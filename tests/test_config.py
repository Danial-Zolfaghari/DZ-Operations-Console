import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from werkzeug.security import check_password_hash


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

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {
                     "DZ_ADMIN_PASSWORD_HASH": "",
                     "VC_ADMIN_PASSWORD_HASH": "",
                 }, clear=False):
                credentials = config.bootstrap_admin_credentials()
                loaded = config.ensure_settings_file()

            self.assertIsNone(credentials)
            self.assertEqual(loaded["admin_password_hash"], "already-hashed")

    def test_first_run_generates_printable_password_and_persists_only_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {
                     "DZ_ADMIN_PASSWORD_HASH": "",
                     "VC_ADMIN_PASSWORD_HASH": "",
                     "DZ_INITIAL_ADMIN_PASSWORD": "",
                     "VC_INITIAL_ADMIN_PASSWORD": "",
                 }, clear=False):
                credentials = config.bootstrap_admin_credentials()

            self.assertIsNotNone(credentials)
            username, password = credentials
            self.assertEqual(username, "admin")
            self.assertGreaterEqual(len(password), 20)
            self.assertTrue(settings_file.exists())

            saved = json.loads(settings_file.read_text(encoding="utf-8"))
            self.assertNotEqual(saved["admin_password_hash"], password)
            self.assertTrue(check_password_hash(saved["admin_password_hash"], password))
            self.assertNotIn(password, settings_file.read_text(encoding="utf-8"))

    def test_explicit_initial_password_is_used_once_then_not_regenerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {
                     "DZ_ADMIN_PASSWORD_HASH": "",
                     "VC_ADMIN_PASSWORD_HASH": "",
                     "DZ_INITIAL_ADMIN_PASSWORD": "unit-test-password-123",
                 }, clear=False):
                first = config.bootstrap_admin_credentials()
                second = config.bootstrap_admin_credentials()

            self.assertEqual(first, ("admin", "unit-test-password-123"))
            self.assertIsNone(second)

    def test_environment_password_hash_prevents_bootstrap_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {
                     "DZ_ADMIN_PASSWORD_HASH": "configured-hash",
                     "VC_ADMIN_PASSWORD_HASH": "",
                 }, clear=False):
                credentials = config.bootstrap_admin_credentials()
                loaded = config.ensure_settings_file()
                cfg = config.Config()

            self.assertIsNone(credentials)
            self.assertEqual(cfg.admin_password_hash, "configured-hash")
            self.assertNotIn("admin_password_hash", loaded)

    def test_direct_ensure_prints_generated_password_for_non_runpy_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"
            output = io.StringIO()

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict("os.environ", {
                     "DZ_ADMIN_PASSWORD_HASH": "",
                     "VC_ADMIN_PASSWORD_HASH": "",
                     "DZ_INITIAL_ADMIN_PASSWORD": "direct-start-password",
                 }, clear=False),                  contextlib.redirect_stdout(output):
                config.ensure_settings_file()

            text = output.getvalue()
            self.assertIn("FIRST RUN ADMIN CREDENTIALS", text)
            self.assertIn("direct-start-password", text)


if __name__ == "__main__":
    unittest.main()
