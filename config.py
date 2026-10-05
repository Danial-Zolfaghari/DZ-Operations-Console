from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = None


def _default_settings() -> dict:
    initial_password = os.getenv("DZ_INITIAL_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
    print("[DZ_Shutdown] First-run admin password:", initial_password)
    print("[DZ_Shutdown] Change it immediately from Settings or set DZ_ADMIN_PASSWORD_HASH.")
    return {
        "admin_username": DEFAULT_USERNAME,
        "admin_password_hash": generate_password_hash(initial_password),
        "shell_enabled": False,
    }


def ensure_settings_file() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        settings = _default_settings()
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return settings
    try:
        settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = _default_settings()
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    defaults = _default_settings()
    changed = False
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
            changed = True
    if changed:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def _env(name: str, default: str) -> str:
    """Prefer DZ_* variables while keeping VC_* compatibility for older setups."""
    return os.getenv(f"DZ_{name}", os.getenv(f"VC_{name}", default))


class Config:
    def __init__(self) -> None:
        persisted = ensure_settings_file()
        self.host = _env("HOST", "127.0.0.1")
        self.port = int(_env("PORT", "5000"))
        self.secret_key = _env("SECRET_KEY", secrets.token_hex(32))

        self.admin_username = _env("ADMIN_USERNAME", persisted["admin_username"])
        self.admin_password_hash = _env("ADMIN_PASSWORD_HASH", persisted["admin_password_hash"])
        self.shell_enabled = _env("SHELL_ENABLED", "1" if persisted.get("shell_enabled") else "0") == "1"

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
