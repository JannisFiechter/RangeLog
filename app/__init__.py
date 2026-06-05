import os

from flask import Flask
from flask_login import LoginManager

from .database import init_db


def create_app():
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="../static",
        template_folder="../templates",
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=app.instance_path + "/rangelog.sqlite",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
    )

    init_db(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    from .auth import auth_bp, get_user

    @login_manager.user_loader
    def load_user(user_id):
        return get_user(user_id)

    from .routes import bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)
    return app


app = create_app()
__all__ = ["create_app", "app"]
