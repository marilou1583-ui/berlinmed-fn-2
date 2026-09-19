import os

import click

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory

from auth import ensure_csrf_cookie
from config import Config
from extensions import db, limiter, migrate
from logging_config import configure_logging
from routes.api_routes import api_bp
from routes.page_routes import page_bp
from seed import add_initial_admin, add_initial_pages, add_initial_products

load_dotenv()


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    Config.validate()

    configure_logging(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp)

    @app.get("/script.js")
    def serve_site_script():
        return send_from_directory(app.root_path, "script.js")

    @app.after_request
    def apply_csrf_cookie(response):
        return ensure_csrf_cookie(response)

    @app.errorhandler(413)
    def handle_file_too_large(e):
        return jsonify({"error": "File too large"}), 413

    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(429)
    def handle_rate_limit(e):
        return jsonify({"error": "Too many requests, please try again later"}), 429

    @app.errorhandler(500)
    def handle_server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    with app.app_context():
        pass

    @app.cli.command("seed")
    def seed_database():
        """Seed initial data and create the configured first administrator."""
        add_initial_products()
        created_admin = add_initial_admin()
        add_initial_pages()
        click.echo("Initial data seeded. Admin account created." if created_admin else "Initial data seeded. An admin account already exists.")

    return app


app = create_app()

# أضف هذا السطر لضمان أن يقرأ Vercel المتغير باسم 'app' مباشرة
application = app 

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], port=3000)
