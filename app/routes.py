from __future__ import annotations

import hmac
import secrets
import subprocess
from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from . import diagnostics, input_control, monitor, power_scheduler, screen_streamer, settings_store
from .security import (
    api_login_required,
    client_ip,
    control_request_limiter,
    login_bruteforce_guard,
    login_request_limiter,
    login_required,
    validate_csrf,
)

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")


def _safe_next(value: str | None) -> str:
    if not value:
        return url_for("main.dashboard")
    parsed = urlparse(value)
    return value if not parsed.netloc and value.startswith("/") else url_for("main.dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("main.dashboard"))

    config = current_app.extensions["dz_config"]
    error = None
    retry_after = 0
    if request.method == "POST":
        validate_csrf()
        ip = client_ip()
        username = request.form.get("username", "")[:128].strip()
        supplied = request.form.get("password", "")[:512]
        normalized_username = username.casefold()
        keys = (f"ip:{ip}", f"account:{ip}:{normalized_username}")

        if not login_request_limiter.allow(f"login-request:{ip}", config.login_request_limit, config.login_request_window_seconds):
            retry_after = config.login_request_window_seconds
            return render_template("login.html", error="Too many sign-in requests. Please wait before trying again.", retry_after=retry_after), 429, {"Retry-After": str(retry_after)}

        retry_after = login_bruteforce_guard.retry_after(keys, config.login_failure_window_seconds)
        if retry_after:
            return render_template("login.html", error=f"Sign-in is temporarily locked. Try again in {retry_after} seconds.", retry_after=retry_after), 429, {"Retry-After": str(retry_after)}

        valid_username = hmac.compare_digest(normalized_username, config.admin_username.casefold())
        valid_password = check_password_hash(config.admin_password_hash, supplied)
        if valid_username and valid_password:
            login_bruteforce_guard.reset(keys)
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            session["username"] = config.admin_username
            session["csrf_token"] = secrets.token_urlsafe(32)
            session["login_at"] = datetime.now().isoformat()
            return redirect(_safe_next(request.args.get("next")))

        retry_after = login_bruteforce_guard.record_failure(
            keys,
            max_failures=config.login_max_failures,
            window_seconds=config.login_failure_window_seconds,
            base_lock_seconds=config.login_base_lock_seconds,
            max_lock_seconds=config.login_max_lock_seconds,
        )
        error = f"Invalid username or password.{f' Sign-in has been locked for {retry_after} seconds.' if retry_after else ''}"

    return render_template("login.html", error=error, retry_after=retry_after)


@auth_bp.post("/logout")
@login_required
def logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("auth.login"))


@main_bp.route("/")
def root():
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", page="dashboard")


@main_bp.route("/screen")
@login_required
def screen():
    return render_template("screen.html", page="screen")


@main_bp.route("/diagnostics")
@login_required
def diagnostics_page():
    return render_template("diagnostics.html", page="diagnostics", catalog=diagnostics.catalog())


@main_bp.route("/settings")
@login_required
def settings_page():
    config = current_app.extensions["dz_config"]
    persisted = settings_store.public()
    return render_template(
        "settings.html",
        page="settings",
        active_shell=config.shell_enabled,
        persisted_shell=persisted["shell_enabled"],
        username=config.admin_username,
        restart_pending=(config.shell_enabled != persisted["shell_enabled"]),
    )


@main_bp.route("/video-feed")
@login_required
def video_feed():
    return Response(screen_streamer.frames(), mimetype="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store"})


@api_bp.get("/system")
@api_login_required
def system_info():
    return jsonify(monitor.snapshot())


@api_bp.get("/power/tasks")
@api_login_required
def power_tasks():
    return jsonify({"tasks": power_scheduler.list_tasks()})


@api_bp.post("/power/schedule")
@api_login_required
def power_schedule():
    validate_csrf()
    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action", "")).lower()
    mode = str(payload.get("mode", "countdown"))
    try:
        if mode == "scheduled":
            task = power_scheduler.schedule(action, at_time=str(payload.get("time", "")))
        else:
            task = power_scheduler.schedule(action, delay_seconds=int(payload.get("seconds", 0)))
        return jsonify({"ok": True, "task": task.as_dict()}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@api_bp.delete("/power/tasks/<task_id>")
@api_login_required
def power_cancel(task_id: str):
    validate_csrf()
    if power_scheduler.cancel(task_id):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Task is not cancellable"}), 404


@api_bp.get("/diagnostics/catalog")
@api_login_required
def diagnostic_catalog():
    return jsonify(diagnostics.catalog())


@api_bp.post("/diagnostics/helper")
@api_login_required
def diagnostic_helper():
    validate_csrf()
    payload = request.get_json(silent=True) or {}
    try:
        result = diagnostics.execute_helper(str(payload.get("id", "")))
        return jsonify({"ok": True, **result})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Command timed out"}), 408
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Helper command failed")
        return jsonify({"ok": False, "error": "Command failed"}), 500


@api_bp.post("/diagnostics/custom")
@api_login_required
def diagnostic_custom():
    validate_csrf()
    payload = request.get_json(silent=True) or {}
    try:
        result = diagnostics.execute_custom(str(payload.get("command", "")))
        return jsonify({"ok": True, **result})
    except PermissionError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Command timed out"}), 408
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Custom command failed")
        return jsonify({"ok": False, "error": "Command failed"}), 500


@api_bp.get("/settings")
@api_login_required
def settings_get():
    config = current_app.extensions["dz_config"]
    persisted = settings_store.public()
    return jsonify({
        "username": config.admin_username,
        "active_shell_enabled": config.shell_enabled,
        "pending_shell_enabled": persisted["shell_enabled"],
        "restart_pending": config.shell_enabled != persisted["shell_enabled"],
    })


@api_bp.post("/settings")
@api_login_required
def settings_update():
    validate_csrf()
    config = current_app.extensions["dz_config"]
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("current_password", ""))
    if not check_password_hash(config.admin_password_hash, current_password):
        return jsonify({"ok": False, "error": "The current administrator password is incorrect."}), 403

    new_password = payload.get("new_password")
    if new_password == "":
        new_password = None
    shell_enabled = payload.get("shell_enabled") if "shell_enabled" in payload else None
    try:
        settings_store.update(new_password=new_password, shell_enabled=shell_enabled)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({
        "ok": True,
        "restart_required": True,
        "message": "Settings saved. Restart the application once to apply the pending changes.",
    })


@api_bp.get("/control/probe")
@api_login_required
def control_probe():
    result = input_control.probe()
    return jsonify(result)


def _control_rate(kind: str, limit: int, window_seconds: int = 1) -> bool:
    key = f"control:{client_ip()}:{session.get('username', 'session')}:{kind}"
    return control_request_limiter.allow(key, limit, window_seconds)


@api_bp.post("/control/mouse/move")
@api_login_required
def control_mouse_move():
    validate_csrf()
    if not _control_rate("move", 24):
        return jsonify({"ok": False, "error": "Mouse input rate limit exceeded."}), 429
    payload = request.get_json(silent=True) or {}
    try:
        input_control.mouse_move(float(payload.get("x", -1)), float(payload.get("y", -1)))
        return jsonify({"ok": True})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Remote mouse move failed")
        return jsonify({"ok": False, "error": "Mouse movement could not be applied to the active desktop session."}), 503


@api_bp.post("/control/mouse/click")
@api_login_required
def control_mouse_click():
    validate_csrf()
    if not _control_rate("click", 12):
        return jsonify({"ok": False, "error": "Mouse click rate limit exceeded."}), 429
    payload = request.get_json(silent=True) or {}
    try:
        input_control.mouse_click(
            float(payload.get("x", -1)),
            float(payload.get("y", -1)),
            int(payload.get("button", 0)),
        )
        return jsonify({"ok": True})
    except (TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Remote mouse click failed")
        return jsonify({"ok": False, "error": "Mouse click could not be applied to the active desktop session."}), 503


@api_bp.post("/control/key")
@api_login_required
def control_key_press():
    validate_csrf()
    if not _control_rate("key", 25):
        return jsonify({"ok": False, "error": "Keyboard input rate limit exceeded."}), 429
    payload = request.get_json(silent=True) or {}
    try:
        input_control.key_press(
            str(payload.get("key", "")),
            ctrl=bool(payload.get("ctrl")),
            shift=bool(payload.get("shift")),
            alt=bool(payload.get("alt")),
        )
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        current_app.logger.exception("Remote keyboard input failed")
        return jsonify({"ok": False, "error": "Keyboard input could not be applied to the active desktop session."}), 503
