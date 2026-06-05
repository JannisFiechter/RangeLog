from flask import Flask

from .database import init_db


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="../static",
        template_folder="../templates",
    )
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=app.instance_path + "/rangelog.sqlite",
    )

    init_db(app)

    from .routes import bp

    app.register_blueprint(bp)
    return app
