from app import create_app

app = create_app()

if __name__ == "__main__":
    config = app.extensions["dz_config"]
    app.run(host=config.host, port=config.port, debug=False, use_reloader=False, threaded=True)
