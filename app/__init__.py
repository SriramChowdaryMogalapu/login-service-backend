import atexit

from flask import Flask, jsonify
from flasgger import Swagger
from pydantic import ValidationError

from app.config.settings import Settings
from app.db import init_db_pool, close_db_pool
from app.extensions import jwt, cors, mail
from app.routes.auth import auth_bp
from app.middleware.app_auth import register_app_auth_middleware
from app.services.auth_service import is_refresh_token_active


def create_app() -> Flask:
    Settings.validate_required_envs()

    app = Flask(__name__)
    app.config.from_object(Settings)

    Swagger(
        app,
        template={
            "swagger": "2.0",
            "info": {
                "title": "Login Backend Service API",
                "version": "1.0.0",
                "description": "Authentication and admin APIs for multi-frontend login service.",
            },
            "basePath": "/",
            "schemes": ["http", "https"],
        },
    )

    init_db_pool(
        database_url=app.config["DATABASE_URL"],
        minconn=app.config["DB_POOL_MIN_CONN"],
        maxconn=app.config["DB_POOL_MAX_CONN"],
    )

    jwt.init_app(app)
    mail.init_app(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_, jwt_payload: dict) -> bool:
        if jwt_payload.get("type") != "refresh":
            return False

        subject = jwt_payload.get("sub")
        if isinstance(subject, dict):
            user_id = str(subject.get("user_id", ""))
        else:
            user_id = str(subject or "")

        app_name = jwt_payload.get("app_name", "")
        jti = jwt_payload.get("jti", "")

        if not user_id or not app_name or not jti:
            return True

        return not is_refresh_token_active(user_id, app_name, jti)

    cors.init_app(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=True,
    )

    register_app_auth_middleware(auth_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return jsonify({"error": "Invalid request payload", "details": exc.errors()}), 400

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    atexit.register(close_db_pool)

    return app
