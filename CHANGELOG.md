# Changelog

All notable changes to **DZ Operations Console** are documented here.

## [Unreleased]

### Added
- Interactive first-run setup with a user-selected administrator username; no username is preselected in the console or login form.
- Automatic first-run administrator password bootstrap in `run.py`; a strong password is generated, its hash is persisted, and the plaintext is printed once before the server starts.
- `.env` loading via `python-dotenv` so documented DZ_* overrides are honored.

### Changed
- Removed the obsolete `admin / admin123` startup message from `start.bat` and `start.ps1`.

### Fixed
- Existing settings no longer generate or print a throwaway first-run administrator password during normal startup.

### Added
- Configuration regression tests.
- Contribution and issue templates.

## [0.1.0] - 2026-10-06

- Initial hardened public release.
- Authentication, CSRF protection, brute-force protection, localhost binding, and shell-disabled defaults.

[Unreleased]: https://github.com/Danial-Zolfaghari/DZ-Operations-Console/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Danial-Zolfaghari/DZ-Operations-Console/releases/tag/v0.1.0
