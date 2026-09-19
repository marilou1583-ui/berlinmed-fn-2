import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from extensions import db
from models import RevokedToken, User

ACCESS_COOKIE_NAME = "access_token"
CSRF_COOKIE_NAME = "csrf_token"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def generate_token(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "jti": uuid.uuid4().hex,
        "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"])
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm=current_app.config["JWT_ALGORITHM"])


def decode_token(token):
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=[current_app.config["JWT_ALGORITHM"]])
    except jwt.PyJWTError:
        return None


def is_token_revoked(jti):
    return db.session.query(RevokedToken.id).filter_by(jti=jti).first() is not None


def revoke_current_token():
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return
    payload = decode_token(token)
    if not payload or not payload.get("jti"):
        return
    if not is_token_revoked(payload["jti"]):
        db.session.add(RevokedToken(jti=payload["jti"]))
        db.session.commit()


def get_current_user():
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    if is_token_revoked(payload.get("jti", "")):
        return None
    return User.query.get(payload.get("user_id"))


def verify_csrf():
    if request.method in SAFE_METHODS:
        return True
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get("X-CSRF-Token")
    return bool(cookie_token and header_token and cookie_token == header_token)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not verify_csrf():
            return jsonify({"error": "Invalid or missing CSRF token"}), 403
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        g.current_user = user
        return view_func(*args, **kwargs)
    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not verify_csrf():
            return jsonify({"error": "Invalid or missing CSRF token"}), 403
        user = get_current_user()
        if not user or user.role != "admin":
            return jsonify({"error": "Unauthorized"}), 401
        g.current_user = user
        return view_func(*args, **kwargs)
    return wrapped


def is_admin_authenticated():
    user = get_current_user()
    return bool(user and user.role == "admin")


def set_auth_cookie(response, token):
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        token,
        httponly=True,
        samesite="Lax",
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        max_age=current_app.config["JWT_EXPIRES_HOURS"] * 3600
    )
    return response


def clear_auth_cookie(response):
    response.delete_cookie(ACCESS_COOKIE_NAME)
    return response


def ensure_csrf_cookie(response):
    if not request.cookies.get(CSRF_COOKIE_NAME):
        response.set_cookie(
            CSRF_COOKIE_NAME,
            uuid.uuid4().hex,
            httponly=False,
            samesite="Lax",
            secure=current_app.config["SESSION_COOKIE_SECURE"]
        )
    return response
