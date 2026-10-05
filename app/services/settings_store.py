from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from werkzeug.security import generate_password_hash

from config import SETTINGS_FILE, ensure_settings_file


class SettingsStore:
    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self.path = path

    def read(self) -> dict:
        return ensure_settings_file().copy()

    def public(self) -> dict:
        data = self.read()
        return {
            "admin_username": data.get("admin_username", "admin"),
            "shell_enabled": bool(data.get("shell_enabled", False)),
        }

    def update(self, *, new_password: str | None = None, shell_enabled: bool | None = None) -> dict:
        data = self.read()
        if new_password is not None:
            if len(new_password) < 8:
                raise ValueError("Password must be at least 8 characters long")
            if len(new_password) > 256:
                raise ValueError("Password is too long")
            data["admin_password_hash"] = generate_password_hash(new_password)
        if shell_enabled is not None:
            data["shell_enabled"] = bool(shell_enabled)
        self._atomic_write(data)
        return self.public()

    def _atomic_write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="dz-settings-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
