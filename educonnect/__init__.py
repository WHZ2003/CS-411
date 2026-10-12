"""EduConnect application factory and HTTP security boundary."""

import os
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from werkzeug.exceptions import HTTPException

from .db import close_db, query

ROOT = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    load_dotenv(ROOT / ".env")
    app = Flask(
        __name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static")
    )
    backend = os.getenv("DATABASE_BACKEND", "sqlite")
    if backend not in {"sqlite", "mysql"}:
        raise ValueError("DATABASE_BACKEND must be sqlite or mysql")
    secret = os.getenv("SECRET_KEY")
    if not secret and not test_config:
        if os.getenv("GAE_ENV") or os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true":
            raise RuntimeError("Set SECRET_KEY for production deployment")
        # Persist the local development key so separate CLI/server processes agree.
        key_file = ROOT / "instance" / ".secret_key"
        key_file.parent.mkdir(exist_ok=True)
        try:
            with key_file.open("x", encoding="utf-8") as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        secret = key_file.read_text(encoding="utf-8")
    app.config.from_mapping(
        SECRET_KEY=secret or secrets.token_hex(32),
        DATABASE_BACKEND=backend,
        DATABASE_PATH=str(ROOT / os.getenv("DATABASE_PATH", "instance/educonnect.sqlite3")),
        DB_HOST=os.getenv("DB_HOST", "127.0.0.1"),
        DB_PORT=int(os.getenv("DB_PORT", "3306")),
        DB_USER=os.getenv("DB_USER", "educonnect"),
        DB_PASSWORD=os.getenv("DB_PASSWORD", ""),
        DB_NAME=os.getenv("DB_NAME", "edu_connect"),
        DB_UNIX_SOCKET=os.getenv("DB_UNIX_SOCKET"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=32768,
    )
    if test_config:
        app.config.update(test_config)
    app.teardown_appcontext(close_db)

    @app.context_processor
    def csrf_context():
        return {"csrf_token": csrf_token()}

    @app.before_request
    def authorize():
        if not request.path.startswith("/api/"):
            return None
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            supplied = request.headers.get("X-CSRF-Token", "")
            if not supplied or not secrets.compare_digest(supplied, session.get("csrf", "")):
                return jsonify(error="Invalid CSRF token. Reload the page."), 403
            if request.data and not isinstance(request.get_json(silent=True), dict):
                return jsonify(error="A JSON object is required"), 400
        if request.path in {"/api/login", "/api/session"}:
            return None
        protected = (
            request.path.startswith(
                ("/api/users/", "/api/bookmarks", "/api/comparisons", "/api/admin/")
            )
            or request.method != "GET"
        )
        if not protected:
            return None
        user_id = session.get("user_id")
        if not user_id:
            return jsonify(error="Please log in"), 401
        user = query("SELECT UserID, IsAdmin FROM User WHERE UserID = %s", (user_id,), one=True)
        if not user:
            session.clear()
            return jsonify(error="Please log in"), 401
        admin_required = request.path.startswith("/api/admin/") or (
            request.path.startswith("/api/programs") and request.method != "GET"
        )
        if admin_required and not user["IsAdmin"]:
            return jsonify(error="Administrator access required"), 403
        args = request.view_args or {}
        owner = args.get("user_id")
        data = request.get_json(silent=True) or {}
        if "user_id" in data:
            try:
                owner = int(data["user_id"])
            except (ValueError, TypeError):
                return jsonify(error="Invalid user_id"), 400
        if owner is not None and owner != user_id:
            return jsonify(error="This account belongs to another user"), 403

    @app.after_request
    def response_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ValueError)
    def invalid_input(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(sqlite3.IntegrityError)
    @app.errorhandler(mysql.connector.IntegrityError)
    def integrity_error(error):
        return jsonify(error="Invalid reference, duplicate value, or constrained record"), 409

    @app.errorhandler(sqlite3.DatabaseError)
    @app.errorhandler(mysql.connector.Error)
    def database_error(error):
        app.logger.exception("Database operation failed")
        return jsonify(error="Database unavailable. Check configuration and run init-db."), 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return error

    from . import routes, cli

    routes.register(app)
    cli.register(app)
    return app


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    return session["csrf"]
