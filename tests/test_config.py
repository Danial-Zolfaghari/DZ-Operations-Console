import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config


class SettingsTests(unittest.TestCase):
    def test_existing_complete_settings_do_not_generate_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"
            settings_file.write_text(
                json.dumps({
                    "admin_username": "admin",
                    "admin_password_hash": "already-hashed",
                    "shell_enabled": False,
                }),
                encoding="utf-8",
            )
            buf = io.StringIO()
            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  contextlib.redirect_stdout(buf):
                loaded = config.ensure_settings_file()

            self.assertEqual(loaded["admin_password_hash"], "already-hashed")
            self.assertNotIn("First-run admin password", buf.getvalue())

    def test_first_run_creates_hashed_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"
            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {"DZ_INITIAL_ADMIN_PASSWORD": "unit-test-password"}, clear=False):
                loaded = config.ensure_settings_file()

            self.assertTrue(settings_file.exists())
            self.assertNotEqual(loaded["admin_password_hash"], "unit-test-password")
            self.assertFalse(loaded["shell_enabled"])


if __name__ == "__main__":
    unittest.main()
