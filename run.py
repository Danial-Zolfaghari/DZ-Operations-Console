from app import create_app
from config import (
    _print_first_run_credentials,
    admin_username_is_configured,
    bootstrap_admin_credentials,
    validate_admin_username,
)


def _prompt_first_run_username() -> str:
    print()
    print("=" * 68)
    print(" DZ Operations Console - FIRST RUN ADMIN SETUP")
    print("=" * 68)
    print(" Choose the administrator username for this installation.")
    print(" Allowed: letters, numbers, dot, underscore and hyphen.")
    print(" Nothing is preselected for you.")
    print()

    while True:
        try:
            value = input(" Administrator username: ")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit(
                "\nFirst-run setup cancelled. Run python run.py again, "
                "or set DZ_ADMIN_USERNAME for non-interactive startup."
            )

        try:
            return validate_admin_username(value)
        except ValueError as exc:
            print(f" [!] {exc}")


def main() -> None:
    bootstrap_username = None
    if not admin_username_is_configured():
        bootstrap_username = _prompt_first_run_username()

    credentials = bootstrap_admin_credentials(bootstrap_username)
    if credentials is not None:
        username, password = credentials
        _print_first_run_credentials(username, password)

    app = create_app()
    config = app.extensions["dz_config"]

    print(f"[DZ Operations Console] Starting web UI: http://{config.host}:{config.port}")
    print(f"[DZ Operations Console] Admin user: {config.admin_username}")
    app.run(
        host=config.host,
        port=config.port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
else:
    app = create_app()
