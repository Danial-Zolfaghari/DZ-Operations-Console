from __future__ import annotations

import json
import os
import re
import secrets
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_USERNAME = None
DEFAULT_PASSWORD = None

load_dotenv(BASE_DIR / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    """Prefer DZ_* variables while keeping VC_* compatibility for older setups."""
    return os.getenv(f"DZ_{name}", os.getenv(f"VC_{name}", default))


def _configured_admin_username() -> str | None:
    value = _env("ADMIN_USERNAME", "").strip()
    return value or None


def _configured_admin_password_hash() -> str | None:
    value = _env("ADMIN_PASSWORD_HASH", "").strip()
    return value or None


def validate_admin_username(value: str) -> str:
    """Validate and normalize a user-selected administrator username."""
    username = (value or "").strip()
    if not username:
        raise ValueError("Administrator username is required.")
    if len(username) < 3:
        raise ValueError("Administrator username must be at least 3 characters.")
    if len(username) > 64:
        raise ValueError("Administrator username must be at most 64 characters.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", username):
        raise ValueError(
            "Use letters, numbers, dot, underscore or hyphen; "
            "the username must start with a letter or number."
        )
    return username


def _new_admin_password() -> str:
    """Return an explicit bootstrap password or generate a strong random one."""
    configured = _env("INITIAL_ADMIN_PASSWORD", "").strip()
    return configured or secrets.token_urlsafe(18)


def _read_settings() -> tuple[dict, bool]:
    if not SETTINGS_FILE.exists():
        return {}, True

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings root must be an object")
        return data, False
    except (OSError, json.JSONDecodeError, ValueError):
        return {}, True


def _ensure_settings_file(
    bootstrap_username: str | None = None,
) -> tuple[dict, str | None]:
    """Return persisted settings and plaintext password only when bootstrapped now."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    settings, must_write = _read_settings()
    changed = must_write

    env_username = _configured_admin_username()
    persisted_username = str(settings.get("admin_username") or "").strip()

    if env_username:
        username = validate_admin_username(env_username)
    elif persisted_username:
        username = validate_admin_username(persisted_username)
    elif bootstrap_username:
        username = validate_admin_username(bootstrap_username)
        settings["admin_username"] = username
        changed = True
    else:
        raise RuntimeError(
            "Administrator username is not configured. "
            "Run python run.py once to complete first-run setup, "
            "or set DZ_ADMIN_USERNAME."
        )

    if "shell_enabled" not in settings:
        settings["shell_enabled"] = False
        changed = True

    generated_password: str | None = None
    persisted_hash = str(settings.get("admin_password_hash") or "").strip()
    env_hash = _configured_admin_password_hash()

    if not env_hash and not persisted_hash:
        generated_password = _new_admin_password()
        settings["admin_password_hash"] = generate_password_hash(generated_password)
        changed = True

    if changed:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    return settings, generated_password


def _print_first_run_credentials(username: str, password: str) -> None:
    line = "=" * 68
    print()
    print(line)
    print(" DZ_Shutdown - FIRST RUN ADMIN CREDENTIALS")
    print(line)
    print(f" Username : {username}")
    print(f" Password : {password}")
    print("-" * 68)
    print(" Save this password now. The plaintext password is NOT stored")
    print(" and will NOT be printed again after this first bootstrap.")
    print(f" Password hash saved to: {SETTINGS_FILE}")
    print(line)
    print()


def admin_username_is_configured() -> bool:
    """Return True when an administrator username exists in env or settings."""
    if _configured_admin_username():
        return True
    settings, _ = _read_settings()
    return bool(str(settings.get("admin_username") or "").strip())


def bootstrap_admin_credentials(username: str | None = None) -> tuple[str, str] | None:
    """
    Ensure administrator credentials exist before the web application starts.

    The first CLI start supplies a user-selected username. A plaintext password
    is returned only when a password was generated during this call.
    """
    settings, generated_password = _ensure_settings_file(bootstrap_username=username)
    if generated_password is None:
        return None

    effective_username = _configured_admin_username() or str(settings.get("admin_username") or "")
    return validate_admin_username(effective_username), generated_password


def ensure_settings_file() -> dict:
    """
    Load/create persisted settings.

    Non-interactive starts must already have a username configured in settings
    or through DZ_ADMIN_USERNAME. Normal first-run setup happens in run.py.
    """
    settings, generated_password = _ensure_settings_file()
    if generated_password is not None:
        username = _configured_admin_username() or str(settings.get("admin_username") or "")
        _print_first_run_credentials(validate_admin_username(username), generated_password)
    return settings


class Config:
    def __init__(self) -> None:
        persisted = ensure_settings_file()

        self.host = _env("HOST", "127.0.0.1")
        self.port = int(_env("PORT", "5000"))
        self.secret_key = _env("SECRET_KEY", secrets.token_hex(32))

        raw_username = _configured_admin_username() or str(persisted.get("admin_username") or "")
        self.admin_username = validate_admin_username(raw_username)

        persisted_hash = str(persisted.get("admin_password_hash") or "")
        self.admin_password_hash = _configured_admin_password_hash() or persisted_hash
        if not self.admin_password_hash:
            raise RuntimeError("Administrator password bootstrap failed.")

        self.shell_enabled = _env(
            "SHELL_ENABLED",
            "1" if persisted.get("shell_enabled") else "0",
        ) == "1"

        self.session_cookie_secure = _env("COOKIE_SECURE", "0") == "1"
        self.screen_fps = max(1, min(20, int(_env("SCREEN_FPS", "8"))))
        self.screen_scale = max(0.25, min(1.0, float(_env("SCREEN_SCALE", "0.65"))))
        self.command_timeout = max(2, min(60, int(_env("COMMAND_TIMEOUT", "15"))))
        self.session_lifetime_minutes = max(5, int(_env("SESSION_MINUTES", "120")))

        self.login_request_limit = max(10, int(_env("LOGIN_REQUEST_LIMIT", "30")))
        self.login_request_window_seconds = max(60, int(_env("LOGIN_REQUEST_WINDOW", "300")))
        self.login_max_failures = max(3, int(_env("LOGIN_MAX_FAILURES", "5")))
        self.login_failure_window_seconds = max(60, int(_env("LOGIN_FAILURE_WINDOW", "600")))
        self.login_base_lock_seconds = max(10, int(_env("LOGIN_BASE_LOCK", "30")))
        self.login_max_lock_seconds = max(60, int(_env("LOGIN_MAX_LOCK", "900")))
