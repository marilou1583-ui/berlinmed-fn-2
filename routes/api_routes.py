import re
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, current_app, jsonify, make_response, request
from sqlalchemy.exc import IntegrityError

from auth import (
    admin_required,
    clear_auth_cookie,
    generate_token,
    get_current_user,
    revoke_current_token,
    set_auth_cookie,
    verify_csrf,
)
from extensions import db, limiter
from models import Order, OrderItem, PageContent, Product, ProductImage, User
from storage import save_product_image

api_bp = Blueprint("api", __name__, url_prefix="/api")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MONEY_QUANTUM = Decimal("0.01")


def parse_price(raw_value):
    try:
        price = Decimal(str(raw_value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not price.is_finite() or price < 0:
        return None
    return price


def parse_non_negative_integer(raw_value):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def get_idempotency_key():
    key = (request.headers.get("Idempotency-Key") or "").strip()
    if not key:
        return None
    return key[:128]


@api_bp.route("/products", methods=["GET"])
def api_get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])


@api_bp.route("/products/<int:id>", methods=["GET"])
def api_get_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product.to_dict())


@api_bp.route("/products", methods=["POST"])
@admin_required
def api_add_product():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    price = parse_price(request.form.get("price"))
    stock = parse_non_negative_integer(request.form.get("stock", 0))

    if not name or price is None or stock is None:
        return jsonify({"error": "A valid name, price and stock value are required"}), 400

    image_files = request.files.getlist("images")
    if not image_files:
        legacy_image = request.files.get("image")
        if legacy_image:
            image_files = [legacy_image]

    if not image_files:
        return jsonify({"error": "At least one product image is required"}), 400

    try:
        filenames = []
        for image_file in image_files:
            filename = save_product_image(image_file)
            if filename:
                filenames.append(filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not filenames:
        return jsonify({"error": "At least one product image is required"}), 400

    product = Product(name=name, description=description, price=price, stock=stock, image=filenames[0])
    for index, filename in enumerate(filenames):
        product.images.append(ProductImage(filename=filename, sort_order=index))

    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Product name already exists"}), 409

    return jsonify({"success": True, "product": product.to_dict()}), 201


@api_bp.route("/products/<int:id>", methods=["PUT"])
@admin_required
def api_edit_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if "name" in request.form:
        product.name = request.form.get("name", product.name).strip() or product.name
    if "description" in request.form:
        product.description = request.form.get("description", product.description)
    if "price" in request.form:
        price = parse_price(request.form.get("price"))
        if price is None:
            return jsonify({"error": "Invalid price"}), 400
        product.price = price
    if "stock" in request.form:
        stock = parse_non_negative_integer(request.form.get("stock"))
        if stock is None:
            return jsonify({"error": "Invalid stock value"}), 400
        product.stock = stock

    image_files = request.files.getlist("images")
    if not image_files:
        legacy_image = request.files.get("image")
        if legacy_image:
            image_files = [legacy_image]

    try:
        next_sort_order = max((img.sort_order for img in product.images), default=-1) + 1
        for image_file in image_files:
            filename = save_product_image(image_file)
            if filename:
                product.images.append(ProductImage(filename=filename, sort_order=next_sort_order))
                next_sort_order += 1
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not product.image and product.images:
        product.image = sorted(product.images, key=lambda img: img.sort_order)[0].filename

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Product name already exists"}), 409
    return jsonify({"success": True, "product": product.to_dict()})


@api_bp.route("/products/<int:id>/images/<int:image_id>", methods=["DELETE"])
@admin_required
def api_delete_product_image(id, image_id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    image = next((img for img in product.images if img.id == image_id), None)
    if not image:
        return jsonify({"error": "Image not found"}), 404

    if len(product.images) <= 1:
        return jsonify({"error": "A product must have at least one image"}), 400

    db.session.delete(image)
    db.session.flush()

    remaining = sorted((img for img in product.images if img.id != image_id), key=lambda img: img.sort_order)
    if product.image == image.filename and remaining:
        product.image = remaining[0].filename

    db.session.commit()
    return jsonify({"success": True, "product": product.to_dict()})


@api_bp.route("/products/<int:id>", methods=["DELETE"])
@admin_required
def api_delete_product(id):
    product = db.session.get(Product, id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()
    return jsonify({"success": True, "message": f"Product '{product.name}' deleted successfully!"})


@api_bp.route("/orders", methods=["GET"])
@admin_required
def api_get_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


@api_bp.route("/orders", methods=["POST"])
@limiter.limit("20 per hour")
def api_create_order():
    if not verify_csrf():
        return jsonify({"error": "Invalid or missing CSRF token"}), 403

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    items = data.get("items") if data else None
    if not items or not isinstance(items, list):
        return jsonify({"error": "No items provided"}), 400
    if len(items) > current_app.config["MAX_ORDER_ITEMS"]:
        return jsonify({"error": "Order exceeds the maximum number of items"}), 400

    idempotency_key = get_idempotency_key()
    if idempotency_key:
        existing_order = Order.query.filter_by(idempotency_key=idempotency_key).first()
        if existing_order:
            return jsonify({"success": True, "idempotent": True, "order": existing_order.to_dict()})

    current_user = get_current_user()
    customer_name = (data.get("customer_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    shipping_address = (data.get("shipping_address") or "").strip()
    payment_method = (data.get("payment_method") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None

    if current_user and not customer_name:
        customer_name = current_user.username
    if not customer_name or not phone or not shipping_address:
        return jsonify({"error": "Customer name, phone and shipping address are required"}), 400

    requested_quantities = {}
    max_item_quantity = current_app.config["MAX_ITEM_QUANTITY"]
    for item in items:
        product_id = item.get("id") if isinstance(item, dict) else None
        quantity = item.get("quantity") if isinstance(item, dict) else None
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return jsonify({"error": "Each item must have a valid quantity"}), 400
        if not isinstance(product_id, int) or quantity < 1 or quantity > max_item_quantity:
            return jsonify({"error": "An item exceeds the allowed quantity"}), 400
        requested_quantities[product_id] = requested_quantities.get(product_id, 0) + quantity
        if requested_quantities[product_id] > max_item_quantity:
            return jsonify({"error": "An item exceeds the allowed quantity"}), 400

    try:
        order = Order(
            order_number=uuid.uuid4().hex,
            idempotency_key=idempotency_key,
            customer_name=customer_name,
            phone=phone,
            shipping_address=shipping_address,
            payment_method=payment_method,
            notes=notes,
            user_id=current_user.id if current_user else None,
        )
        total = Decimal("0.00")
        for product_id, quantity in requested_quantities.items():
            product = db.session.query(Product).filter_by(id=product_id).with_for_update().first()
            if not product:
                db.session.rollback()
                return jsonify({"error": f"Product with id {product_id} not found"}), 404
            if quantity > product.stock:
                db.session.rollback()
                return jsonify({"error": f"Insufficient stock for {product.name}"}), 409
            product.stock -= quantity
            total += product.price * quantity
            order.items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_image=product.image,
                unit_price=product.price,
                quantity=quantity,
            ))
        order.total = total.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        db.session.add(order)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if idempotency_key:
            existing_order = Order.query.filter_by(idempotency_key=idempotency_key).first()
            if existing_order:
                return jsonify({"success": True, "idempotent": True, "order": existing_order.to_dict()})
        return jsonify({"error": "Could not create the order"}), 409
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "success": True,
        "message": "Order placed successfully!",
        "order": order.to_dict(),
    }), 201


@api_bp.route("/pages/<slug>", methods=["GET"])
def api_get_page(slug):
    page = PageContent.query.filter_by(slug=slug).first()
    if not page:
        return jsonify({"error": "Page not found"}), 404
    return jsonify(page.to_dict())


@api_bp.route("/pages/<slug>", methods=["PUT"])
@admin_required
def api_update_page(slug):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()

    if not title or not body:
        return jsonify({"error": "Title and body are required"}), 400

    page = PageContent.query.filter_by(slug=slug).first()
    if page:
        page.title = title
        page.body = body
    else:
        page = PageContent(slug=slug, title=title, body=body)
        db.session.add(page)

    db.session.commit()
    return jsonify({"success": True, "page": page.to_dict()})


@api_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def api_register():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    if not EMAIL_PATTERN.match(email):
        return jsonify({"error": "Invalid email address"}), 400

    if len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    user = User(username=username, email=email, role="customer")
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username or email already exists"}), 409

    return jsonify({"success": True, "message": "Account created successfully"})


@api_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def api_login():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    username = data.get("username", "")
    password = data.get("password", "")

    if username is None:
        username = ""
    if password is None:
        password = ""

    username = username.strip()
    password = password.strip()


    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        token = generate_token(user)
        response = make_response(jsonify({"success": True, "message": "Login successful"}))
        set_auth_cookie(response, token)
        return response
    return jsonify({"error": "Invalid credentials"}), 401


@api_bp.route("/logout", methods=["POST"])
def api_logout():
    if not verify_csrf():
        return jsonify({"error": "Invalid or missing CSRF token"}), 403
    revoke_current_token()
    response = make_response(jsonify({"success": True, "message": "Logged out"}))
    clear_auth_cookie(response)
    return response


@api_bp.route("/session", methods=["GET"])
def api_check_session():
    user = get_current_user()
    return jsonify({"authenticated": bool(user), "admin": bool(user and user.role == "admin")})