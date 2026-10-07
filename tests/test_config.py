import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import config
from werkzeug.security import check_password_hash


class SettingsTests(unittest.TestCase):
    def _blank_env(self):
        return mock.patch.dict(
            "os.environ",
            {
                "DZ_ADMIN_USERNAME": "",
                "VC_ADMIN_USERNAME": "",
                "DZ_ADMIN_PASSWORD_HASH": "",
                "VC_ADMIN_PASSWORD_HASH": "",
                "DZ_INITIAL_ADMIN_PASSWORD": "",
                "VC_INITIAL_ADMIN_PASSWORD": "",
            },
            clear=False,
        )

    def test_username_validation(self):
        self.assertEqual(config.validate_admin_username("Danial-Z"), "Danial-Z")
        self.assertEqual(config.validate_admin_username("user.name_1"), "user.name_1")

        for value in ("", "ab", "-admin", "bad username", "a" * 65):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    config.validate_admin_username(value)

    def test_missing_username_requires_first_run_setup(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  self._blank_env():
                self.assertFalse(config.admin_username_is_configured())
                with self.assertRaises(RuntimeError):
                    config.bootstrap_admin_credentials()

    def test_first_run_uses_user_selected_username_and_generates_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  self._blank_env():
                credentials = config.bootstrap_admin_credentials("VoidCipher")

            self.assertIsNotNone(credentials)
            username, password = credentials

            self.assertEqual(username, "VoidCipher")
            self.assertGreaterEqual(len(password), 20)

            saved = json.loads(settings_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["admin_username"], "VoidCipher")
            self.assertTrue(check_password_hash(saved["admin_password_hash"], password))
            self.assertNotIn(password, settings_file.read_text(encoding="utf-8"))

    def test_existing_complete_settings_do_not_generate_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"
            settings_file.write_text(
                json.dumps({
                    "admin_username": "Danial",
                    "admin_password_hash": "already-hashed",
                    "shell_enabled": False,
                }),
                encoding="utf-8",
            )

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  self._blank_env():
                credentials = config.bootstrap_admin_credentials()
                loaded = config.ensure_settings_file()

            self.assertIsNone(credentials)
            self.assertEqual(loaded["admin_username"], "Danial")
            self.assertEqual(loaded["admin_password_hash"], "already-hashed")

    def test_explicit_initial_password_is_used_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict(
                     "os.environ",
                     {
                         "DZ_ADMIN_USERNAME": "",
                         "VC_ADMIN_USERNAME": "",
                         "DZ_ADMIN_PASSWORD_HASH": "",
                         "VC_ADMIN_PASSWORD_HASH": "",
                         "DZ_INITIAL_ADMIN_PASSWORD": "unit-test-password-123",
                     },
                     clear=False,
                 ):
                first = config.bootstrap_admin_credentials("Operator")
                second = config.bootstrap_admin_credentials()

            self.assertEqual(first, ("Operator", "unit-test-password-123"))
            self.assertIsNone(second)

    def test_environment_credentials_skip_interactive_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  mock.patch.dict(
                     "os.environ",
                     {
                         "DZ_ADMIN_USERNAME": "ManagedUser",
                         "VC_ADMIN_USERNAME": "",
                         "DZ_ADMIN_PASSWORD_HASH": "configured-hash",
                         "VC_ADMIN_PASSWORD_HASH": "",
                     },
                     clear=False,
                 ):
                self.assertTrue(config.admin_username_is_configured())
                credentials = config.bootstrap_admin_credentials()
                cfg = config.Config()

            self.assertIsNone(credentials)
            self.assertEqual(cfg.admin_username, "ManagedUser")
            self.assertEqual(cfg.admin_password_hash, "configured-hash")

    def test_noninteractive_start_without_username_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings_file = data_dir / "settings.json"

            with mock.patch.object(config, "DATA_DIR", data_dir),                  mock.patch.object(config, "SETTINGS_FILE", settings_file),                  self._blank_env():
                with self.assertRaises(RuntimeError):
                    config.ensure_settings_file()


if __name__ == "__main__":
    unittest.main()
