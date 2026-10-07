from app import create_app
from config import _print_first_run_credentials, bootstrap_admin_credentials


def main() -> None:
    credentials = bootstrap_admin_credentials()
    if credentials is not None:
        username, password = credentials
        _print_first_run_credentials(username, password)

    app = create_app()
    config = app.extensions["dz_config"]

    print(f"[DZ_Shutdown] Starting web UI: http://{config.host}:{config.port}")
    print(f"[DZ_Shutdown] Admin user: {config.admin_username}")
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
    # Keep run.py importable by WSGI/test tooling.
    app = create_app()
