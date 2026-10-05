# Security Policy

## Supported deployment model

DZ_Shutdown is designed to bind to `127.0.0.1` by default. Remote exposure should only be performed through an explicitly secured deployment with authentication, TLS and network access controls.

## Security defaults

- Login required for dashboard/control routes
- Passwords stored as hashes, not plaintext
- CSRF protection for state-changing requests
- HTTP-only, SameSite=Strict sessions
- Login throttling and progressive lockout
- Custom shell disabled by default
- CSP, X-Frame-Options, no-sniff and other response headers

## Reporting a vulnerability

Do not include passwords, session cookies, real host details, private IP architecture, or sensitive screenshots in public issues.
