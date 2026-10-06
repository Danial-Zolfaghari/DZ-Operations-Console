# Contributing to DZ_Shutdown

DZ_Shutdown includes privileged Windows administration features, so changes must preserve secure defaults.

## Rules

- Keep the default bind address loopback-only unless the user explicitly configures otherwise.
- Keep the shell disabled by default.
- Do not weaken authentication, CSRF protection, brute-force controls, cookie settings, or security headers.
- Never commit passwords, password hashes from real deployments, tokens, private host details, screenshots containing sensitive information, or runtime data.
- Add or update tests for authentication/configuration changes.

## Validation

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app config.py run.py make_password.py tests
```

Explain any privilege, Windows-version, or network-exposure impact in the pull request.
