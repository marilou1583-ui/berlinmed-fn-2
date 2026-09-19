import json
from pathlib import Path


def get_csrf_token(client):
    client.get("/")
    cookie = client.get_cookie("csrf_token")
    return cookie.value if cookie else None


def create_product(app, name="Test Product", price="10.50", stock=10):
    from extensions import db
    from models import Product

    with app.app_context():
        product = Product(name=name, description="Test", price=price, stock=stock, image="placeholder.jpg")
        db.session.add(product)
        db.session.commit()
        return product.id


def test_product_details_template_uses_shared_image_url_helper():
    template_path = Path(__file__).resolve().parents[1] / "templates" / "product_details.html"
    content = template_path.read_text(encoding="utf-8")

    assert "getImageUrl(data.image)" in content
    assert 'src="/static/images/${escapeHtml(data.image)}"' not in content


def test_get_products_empty(client):
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.get_json() == []


def test_register_and_login(client):
    csrf = get_csrf_token(client)

    response = client.post(
        "/api/register",
        data=json.dumps({"username": "alice", "email": "alice@example.com", "password": "strongpass123"}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    response = client.post(
        "/api/login",
        data=json.dumps({"username": "alice", "password": "strongpass123"}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_login_invalid_username(client):
    csrf = get_csrf_token(client)
    response = client.post(
        "/api/login",
        data=json.dumps({"username": "does_not_exist", "password": "whatever"}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 401
    assert response.get_json()["error"] == "Invalid credentials"


def test_seeded_admin_can_log_in(client, app, monkeypatch):
    from seed import add_initial_admin

    monkeypatch.setenv("ADMIN_USERNAME", "site_admin")
    monkeypatch.setenv("ADMIN_EMAIL", "site-admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")
    with app.app_context():
        assert add_initial_admin() is True
        assert add_initial_admin() is False

    csrf = get_csrf_token(client)
    response = client.post(
        "/api/login",
        data=json.dumps({"username": "site_admin", "password": "adminpass123"}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200

    assert client.get("/api/session").get_json()["admin"] is True


def test_register_weak_password_rejected(client):
    csrf = get_csrf_token(client)
    response = client.post(
        "/api/register",
        data=json.dumps({"username": "bob", "email": "bob@example.com", "password": "123"}),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 400


def test_add_product_requires_admin(client):
    csrf = get_csrf_token(client)
    response = client.post(
        "/api/products",
        data={"name": "Test Product", "price": "10.5", "stock": "1"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 401


def test_add_product_requires_csrf_token(client, app):
    from extensions import db
    from models import User

    with app.app_context():
        admin = User(username="admin_test", email="admin_test@example.com", role="admin")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()

    client.get("/")
    client.post(
        "/api/login",
        data=json.dumps({"username": "admin_test", "password": "adminpass123"}),
        content_type="application/json",
        headers={"X-CSRF-Token": client.get_cookie("csrf_token").value},
    )

    # Missing CSRF header should be rejected even though logged in as admin
    response = client.post("/api/products", data={"name": "No CSRF Product", "price": "10", "stock": "1"})
    assert response.status_code == 403


def test_order_reduces_stock_and_is_idempotent(client, app):
    product_id = create_product(app, stock=3)
    csrf = get_csrf_token(client)
    payload = {
        "items": [{"id": product_id, "quantity": 2}],
        "customer_name": "Guest Customer",
        "phone": "01000000000",
        "shipping_address": "",
    }
    headers = {"X-CSRF-Token": csrf, "Idempotency-Key": "test-order-key"}

    response = client.post("/api/orders", data=json.dumps(payload), content_type="application/json", headers=headers)
    assert response.status_code == 201
    assert response.get_json()["order"]["total"] == 21.0

    response = client.post("/api/orders", data=json.dumps(payload), content_type="application/json", headers=headers)
    assert response.status_code == 200
    assert response.get_json()["idempotent"] is True

    from extensions import db
    from models import Order, Product

    with app.app_context():
        assert Order.query.count() == 1
        assert db.session.get(Product, product_id).stock == 1


def test_order_rejects_insufficient_stock(client, app):
    product_id = create_product(app, stock=1)
    csrf = get_csrf_token(client)
    response = client.post(
        "/api/orders",
        data=json.dumps({
            "items": [{"id": product_id, "quantity": 2}],
            "customer_name": "Guest Customer",
            "phone": "01000000000",
            "shipping_address": "",
        }),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 409
