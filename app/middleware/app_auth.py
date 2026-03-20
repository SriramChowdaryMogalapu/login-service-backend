from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash

from app.services.auth_service import get_authorized_app
from app.utils.audit import log_audit


def register_app_auth_middleware(auth_blueprint: Blueprint) -> None:
    @auth_blueprint.before_request
    def validate_client_app():
        if request.method == "OPTIONS":
            return None

        app_name = (request.headers.get("X-App-Name") or "").strip()
        client_secret = (request.headers.get("X-Client-Secret") or "").strip()

        missing_fields = []
        if not app_name:
            missing_fields.append("app_name")
        if not client_secret:
            missing_fields.append("client_secret")

        if missing_fields:
            return jsonify({"error": "Missing required app auth headers", "missing": missing_fields}), 400

        authorized_app = get_authorized_app(app_name)
        if not authorized_app or not check_password_hash(authorized_app["client_secret_hash"], client_secret):
            log_audit(None, app_name, "app_auth", False, {"error": "Unauthorized app"})
            return jsonify({"error": "Unauthorized app"}), 403

        g.app_name = app_name
        return None
