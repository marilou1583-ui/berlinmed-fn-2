import os
import tempfile

import pytest

db_fd, db_path = tempfile.mkstemp()

os.environ["FLASK_ENV"] = "testing"
os.environ["SECRET_KEY"] = "test_secret_key"
os.environ["JWT_SECRET_KEY"] = "test_jwt_secret_key"
os.environ["LOG_FILE"] = "logs/test.log"
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


@pytest.fixture
def app():
    test_app = create_app()
    test_app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
    with test_app.app_context():
        db.drop_all()
        db.create_all()
    yield test_app
    with test_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True, scope="session")
def cleanup():
    yield
    os.close(db_fd)
    os.unlink(db_path)
