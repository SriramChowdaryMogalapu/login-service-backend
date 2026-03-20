from datetime import datetime, timedelta, timezone
import secrets
import uuid

from flask import Blueprint, current_app, g, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from flask_jwt_extended.utils import get_jti
from psycopg2 import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.models.schemas import (
    AuthRequest,
    CreateAppRequest,
    MpinRequest,
    PasswordResetRequest,
    PromoteSuperUserRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.services.auth_service import (
    create_authorized_app,
    create_password_reset,
    create_user_with_role,
    get_user_by_email,
    get_user_by_id,
    get_valid_password_reset_user_id,
    is_refresh_token_active,
    mark_password_reset_used,
    revoke_refresh_token_jti,
    revoke_refresh_tokens_for_user,
    store_refresh_token,
    update_user_mpin,
    update_user_password,
    update_user_super_user,
)
from app.utils.audit import log_audit
from app.utils.email_service import (
    send_password_changed_email,
    send_password_reset_email,
    send_signup_email,
)


auth_bp = Blueprint("auth", __name__)


def _issue_tokens(user_id: str, app_name: str, fresh: bool = False) -> tuple[str, str]:
    identity = str(user_id)
    additional_claims = {"app_name": app_name}

    access_token = create_access_token(identity=identity, fresh=fresh, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_claims)

    refresh_jti = get_jti(refresh_token)
    store_refresh_token(
        user_id=str(user_id),
        app_name=app_name,
        refresh_jti=refresh_jti,
        expires_delta=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
        ip_address=request.remote_addr or "unknown",
        user_agent=request.headers.get("User-Agent", ""),
    )

    return access_token, refresh_token


def _get_identity_user_id() -> str | None:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        user_id = identity.get("user_id")
    else:
        user_id = identity

    if not user_id:
        return None
    return str(user_id)


def _payload_with_app_name() -> dict:
    payload = request.get_json(silent=True) or {}
    payload["app_name"] = g.app_name
    return payload


@auth_bp.route("/signup", methods=["POST"])
def auth_signup():
    """Create a new user account.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email:
              type: string
            password:
              type: string
            super_user:
              type: boolean
    responses:
      201:
        description: User created
      409:
        description: Email exists
    """
    data = SignupRequest(**_payload_with_app_name())

    app_name = g.app_name
    existing_user = get_user_by_email(data.email)
    if existing_user:
        log_audit(str(existing_user["id"]), app_name, "signup", False, {"error": "Email exists"})
        return jsonify({"error": "Email already registered"}), 409

    user_id = create_user_with_role(
        email=data.email,
        password_hash=generate_password_hash(data.password),
        full_name=data.email.split("@")[0],
        super_user=data.super_user,
    )

    try:
        send_signup_email(data.email)
    except Exception:
        current_app.logger.exception("Failed to send signup email")

    log_audit(user_id, app_name, "signup", True)
    return jsonify({"message": "User created. Verify email."}), 201


@auth_bp.route("/login", methods=["POST"])
def auth_login():
    """Login with email and password.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email, password]
          properties:
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            message:
              type: string
            mpin_set:
              type: boolean
            super_user:
              type: boolean
      401:
        description: Invalid credentials
    """
    data = AuthRequest(**_payload_with_app_name())
    user = get_user_by_email(data.email)

    if not user or not check_password_hash(user["password_hash"], data.password):
        log_audit(str(user["id"]) if user else None, g.app_name, "login", False)
        return jsonify({"error": "Invalid credentials"}), 401

    access_token, refresh_token = _issue_tokens(str(user["id"]), g.app_name, fresh=True)

    log_audit(str(user["id"]), g.app_name, "login", True)
    resp = jsonify(
        {
            "message": "Login successful",
            "mpin_set": bool(user.get("mpin_hash")),
            "super_user": bool(user.get("super_user")),
        }
    )
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp


@auth_bp.route("/set-mpin", methods=["POST"])
@jwt_required(fresh=True)
def auth_set_mpin():
    """Set or update MPIN for the logged-in user.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [mpin]
          properties:
            mpin:
              type: string
    responses:
      200:
        description: MPIN saved successfully
      401:
        description: Invalid token subject or unauthorized
      404:
        description: User not found
    """
    data = MpinRequest(**_payload_with_app_name())
    user_id = _get_identity_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token subject"}), 401

    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    update_user_mpin(user_id, generate_password_hash(data.mpin))
    log_audit(user_id, g.app_name, "set-mpin", True)
    return jsonify({"message": "MPIN saved successfully"}), 200


@auth_bp.route("/create-app", methods=["POST"])
@jwt_required(fresh=True)
def auth_create_app():
    """Create a new authorized client application.
    ---
    tags:
      - Admin
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [app_name]
          properties:
            app_name:
              type: string
            client_secret:
              type: string
    responses:
      201:
        description: App created
      403:
        description: Super user required
      409:
        description: App already exists
    """
    actor_id = _get_identity_user_id()
    if not actor_id:
        return jsonify({"error": "Invalid token subject"}), 401

    actor = get_user_by_id(actor_id)
    if not actor or not actor.get("super_user"):
        return jsonify({"error": "Super user access required"}), 403

    data = CreateAppRequest(**_payload_with_app_name())
    client_secret = data.client_secret or secrets.token_urlsafe(24)

    try:
        create_authorized_app(data.app_name, generate_password_hash(client_secret))
    except IntegrityError:
        return jsonify({"error": "App already exists"}), 409

    log_audit(actor_id, g.app_name, "create-app", True, {"created_app": data.app_name})
    return jsonify({"message": "App created", "app_name": data.app_name, "client_secret": client_secret}), 201


@auth_bp.route("/make-super-user", methods=["POST"])
@jwt_required(fresh=True)
def auth_make_super_user():
    """Grant or revoke super user role for a user.
    ---
    tags:
      - Admin
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email:
              type: string
            super_user:
              type: boolean
    responses:
      200:
        description: Role updated
      403:
        description: Super user required
      404:
        description: User not found
    """
    actor_id = _get_identity_user_id()
    if not actor_id:
        return jsonify({"error": "Invalid token subject"}), 401

    actor = get_user_by_id(actor_id)
    if not actor or not actor.get("super_user"):
        return jsonify({"error": "Super user access required"}), 403

    data = PromoteSuperUserRequest(**_payload_with_app_name())
    target_user = get_user_by_email(data.email)
    if not target_user:
        return jsonify({"error": "User not found"}), 404

    update_user_super_user(str(target_user["id"]), data.super_user)
    log_audit(actor_id, g.app_name, "make-super-user", True, {"email": data.email, "super_user": data.super_user})
    return jsonify({"message": "User role updated", "email": data.email, "super_user": data.super_user}), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def auth_refresh():
    """Refresh access and refresh tokens using a valid refresh token.
    ---
    tags:
      - Auth
    responses:
      200:
        description: Tokens refreshed successfully
      401:
        description: Invalid token subject
      403:
        description: Token app mismatch or invalid refresh token
    """
    claims = get_jwt()

    user_id = _get_identity_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token subject"}), 401

    app_name = g.app_name

    if claims.get("app_name") != app_name:
        return jsonify({"error": "Token app mismatch"}), 403

    refresh_jti = claims.get("jti")
    if not refresh_jti:
        return jsonify({"error": "Invalid refresh token"}), 401

    if not is_refresh_token_active(user_id, app_name, refresh_jti):
        return jsonify({"error": "Invalid refresh token"}), 401

    revoke_refresh_token_jti(user_id, app_name, refresh_jti)
    new_access, new_refresh = _issue_tokens(user_id, app_name)

    resp = jsonify({"message": "Tokens refreshed"})
    set_access_cookies(resp, new_access)
    set_refresh_cookies(resp, new_refresh)
    return resp


@auth_bp.route("/forgot-password", methods=["POST"])
def auth_forgot():
    """Request a password reset email.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email:
              type: string
    responses:
      200:
        description: Reset email sent (if email exists)
    """
    data = PasswordResetRequest(**_payload_with_app_name())
    user = get_user_by_email(data.email)

    if not user:
        return jsonify({"message": "If email exists, reset link sent"}), 200

    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    create_password_reset(str(user["id"]), token, expires_at)

    reset_url = f"{current_app.config['PASSWORD_RESET_BASE_URL']}?token={token}&app={g.app_name}"
    send_password_reset_email(data.email, reset_url)

    log_audit(str(user["id"]), g.app_name, "forgot-password", True)
    return jsonify({"message": "Reset email sent"})


@auth_bp.route("/reset-password", methods=["POST"])
def auth_reset():
    """Reset password using a valid reset token.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [token, password]
          properties:
            token:
              type: string
            password:
              type: string
    responses:
      200:
        description: Password reset successful
      400:
        description: Invalid or expired token
    """
    data = ResetPasswordRequest(**_payload_with_app_name())

    user_id = get_valid_password_reset_user_id(data.token)
    if not user_id:
        return jsonify({"error": "Invalid or expired token"}), 400

    update_user_password(user_id, generate_password_hash(data.password))
    mark_password_reset_used(data.token)
    revoke_refresh_tokens_for_user(user_id, g.app_name)

    user = get_user_by_id(user_id)
    if user and user.get("email"):
        try:
            send_password_changed_email(str(user["email"]))
        except Exception:
            current_app.logger.exception("Failed to send password changed email")

    log_audit(user_id, g.app_name, "reset-password", True)
    return jsonify({"message": "Password reset successful"})


@auth_bp.route("/mpin-verify", methods=["POST"])
@jwt_required()
def auth_mpin_verify():
    """Verify MPIN and issue fresh access token.
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [mpin]
          properties:
            mpin:
              type: string
    responses:
      200:
        description: MPIN verified, fresh token issued
      401:
        description: Invalid token subject or invalid MPIN
    """
    data = MpinRequest(**_payload_with_app_name())
    user_id = _get_identity_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token subject"}), 401

    user = get_user_by_id(user_id)
    if not user or not user.get("mpin_hash") or not check_password_hash(user["mpin_hash"], data.mpin):
        return jsonify({"error": "Invalid MPIN"}), 401

    new_access = create_access_token(
        identity=str(user["id"]),
        fresh=True,
        additional_claims={"app_name": g.app_name},
    )
    resp = jsonify({"message": "MPIN verified"})
    set_access_cookies(resp, new_access)
    return resp


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def auth_logout():
    """Logout user and revoke refresh tokens.
    ---
    tags:
      - Auth
    responses:
      200:
        description: Logged out successfully
      401:
        description: Invalid token subject
    """
    user_id = _get_identity_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token subject"}), 401

    revoke_refresh_tokens_for_user(user_id, g.app_name)
    resp = jsonify({"message": "Logged out"})
    unset_jwt_cookies(resp)
    log_audit(user_id, g.app_name, "logout", True)
    return resp


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def auth_profile():
    """Get current user profile information.
    ---
    tags:
      - Auth
    responses:
      200:
        description: User profile retrieved
        schema:
          type: object
          properties:
            user:
              type: object
              properties:
                id:
                  type: string
                email:
                  type: string
                name:
                  type: string
                super_user:
                  type: boolean
      401:
        description: Invalid token subject
      404:
        description: User not found
    """
    user_id = _get_identity_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token subject"}), 401

    user = get_user_by_id(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "name": user.get("full_name"),
                "super_user": bool(user.get("super_user")),
            }
        }
    )
