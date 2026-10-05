from __future__ import annotations

from datetime import timedelta
from flask import Flask

from config import Config
from .security import get_csrf_token
from .services.diagnostics import DiagnosticsService
from .services.input_control import InputControlService
from .services.power import PowerScheduler
from .services.screen import ScreenStreamer
from .services.settings_store import SettingsStore
from .services.system_monitor import SystemMonitor

monitor = SystemMonitor()
power_scheduler = PowerScheduler()
diagnostics = DiagnosticsService()
screen_streamer = ScreenStreamer()
settings_store = SettingsStore()
input_control = InputControlService()


def create_app() -> Flask:
    config = Config()
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.update(
        SECRET_KEY=config.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=config.session_cookie_secure,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=config.session_lifetime_minutes),
        MAX_CONTENT_LENGTH=128 * 1024,
    )
    app.extensions["dz_config"] = config

    global diagnostics, screen_streamer
    diagnostics = DiagnosticsService(config.command_timeout, config.shell_enabled)
    screen_streamer = ScreenStreamer(config.screen_fps, config.screen_scale)

    from .routes import auth_bp, main_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_security():
        return {"csrf_token": get_csrf_token()}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        if response.mimetype == "application/json":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
