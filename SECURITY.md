# Security Policy

DZ_Shutdown exposes administrative capabilities and must be treated as privileged software.

- Keep the default bind on loopback unless you have a trusted management network.
- Set a strong administrator password hash and secret key.
- Keep shell functionality disabled unless explicitly required.
- Use HTTPS and secure cookies when traversing a network.
- Never commit `.env`, production hashes, secrets, logs, screenshots, or host-specific data.
