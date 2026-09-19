import os

from flask import current_app
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from extensions import db
from models import PageContent, Product, User


def add_initial_products():
    products_to_add = [
        {"name": "Digital Thermometer", "description": "Fast and accurate temperature readings.", "price": "150.00", "stock": 0, "image": "thermometer.jpg"},
        {"name": "N95 Face Masks (Box of 50)", "description": "High-filtration masks for protection.", "price": "750.00", "stock": 0, "image": "n95_masks.jpg"},
        {"name": "Hand Sanitizer (500ml)", "description": "Kills 99.9% of germs, with moisturizers.", "price": "80.00", "stock": 0, "image": "sanitizer.jpg"},
        {"name": "Automatic Blood Pressure Monitor", "description": "Easy-to-use upper arm blood pressure monitor.", "price": "1200.00", "stock": 0, "image": "bp_monitor.jpg"},
        {"name": "Pulse Oximeter", "description": "Measures blood oxygen saturation and pulse rate.", "price": "650.00", "stock": 0, "image": "oximeter.jpg"},
        {"name": "First Aid Kit", "description": "Comprehensive kit for home and travel emergencies.", "price": "450.00", "stock": 0, "image": "first_aid_kit.jpg"},
        {"name": "Glucometer Kit", "description": "For monitoring blood glucose levels.", "price": "950.00", "stock": 0, "image": "glucometer.jpg"},
        {"name": "Disposable Gloves (Box of 100)", "description": "Latex-free and powder-free gloves.", "price": "250.00", "stock": 0, "image": "gloves.jpg"},
    ]
    # Flask-SQLAlchemy does not guarantee that ``session.bind`` is populated.
    # ``db.engine`` is the application-bound engine and works for SQLite and
    # PostgreSQL alike.
    dialect_name = db.engine.dialect.name
    if dialect_name == "postgresql":
        statement = postgresql_insert(Product).values(products_to_add).on_conflict_do_nothing(index_elements=["name"])
    elif dialect_name == "sqlite":
        statement = sqlite_insert(Product).values(products_to_add).on_conflict_do_nothing(index_elements=["name"])
    else:
        raise RuntimeError("Initial product seeding requires PostgreSQL or SQLite.")
    db.session.execute(statement)
    db.session.commit()
    current_app.logger.info("Added initial products to the database.")


def add_initial_pages():
    if not PageContent.query.filter_by(slug="about").first():
        db.session.add(PageContent(
            slug="about",
            title="BerlinMed",
            body=(
                "We are specialized in providing the latest medical devices and diagnostic "
                "solutions for hospitals, clinics, and medical centers.\n\n"
                "We offer a wide range of medical equipment such as ultrasound devices, "
                "patient monitors, ECG machines, and emergency devices with the highest quality."
            ),
        ))
        db.session.commit()
        current_app.logger.info("Added initial page content.")


def add_initial_admin():
    """Create the first administrator from environment variables.

    An administrator must never be created with an implicit/default password.  The
    old implementation silently skipped this step when ``ADMIN_PASSWORD`` was
    missing, while the seed command still reported success; consequently no one
    could log in to the admin panel.
    """
    if User.query.filter_by(role="admin").first():
        return False

    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_password:
        raise RuntimeError(
            "ADMIN_PASSWORD must be set before creating the first admin account. "
            "Set ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD in .env, then run flask seed again."
        )
    if len(admin_password) < 8:
        raise RuntimeError("ADMIN_PASSWORD must be at least 8 characters long.")
    if User.query.filter((User.username == admin_username) | (User.email == admin_email)).first():
        raise RuntimeError(
            "ADMIN_USERNAME or ADMIN_EMAIL is already used by another account. "
            "Choose different values before running flask seed."
        )

    admin = User(username=admin_username, email=admin_email, role="admin")
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()
    current_app.logger.info("Added initial admin account.")
    return True
