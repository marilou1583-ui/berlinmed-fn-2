import os

from flask import Blueprint, abort, current_app, make_response, redirect, request

from auth import is_admin_authenticated

page_bp = Blueprint("pages", __name__)


def serve_template_with_api_url(template_path):
    try:
        with open(os.path.join(current_app.root_path, 'templates', template_path), 'r', encoding='utf-8') as f:
            content = f.read()

        api_base_url = request.url_root.rstrip('/')

        meta_tag_template = '<meta name="api-base-url" content="">'
        meta_tag_filled = f'<meta name="api-base-url" content="{api_base_url}">'

        if meta_tag_template in content:
            content = content.replace(meta_tag_template, meta_tag_filled)
        else:
            viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            if viewport_meta in content:
                insert_point = content.find(viewport_meta) + len(viewport_meta)
                content = content[:insert_point] + f'\n    <meta name="api-base-url" content="{api_base_url}">' + content[insert_point:]
            else:
                head_open = '<head>'
                if head_open in content:
                    insert_point = content.find(head_open) + len(head_open)
                    content = content[:insert_point] + f'\n    <meta name="api-base-url" content="{api_base_url}">' + content[insert_point:]

        response = make_response(content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    except FileNotFoundError:
        return abort(404)
    except Exception as e:
        current_app.logger.error(f"Error serving template {template_path}: {e}")
        return abort(500)


@page_bp.route("/")
def serve_index():
    return serve_template_with_api_url("index.html")

@page_bp.route("/products")
def serve_products():
    return serve_template_with_api_url("products.html")

@page_bp.route("/product-details")
def serve_product_details():
    return serve_template_with_api_url("product_details.html")

@page_bp.route("/cart")
def serve_cart():
    return serve_template_with_api_url("cart.html")

@page_bp.route("/about")
def serve_about():
    return serve_template_with_api_url("about.html")

@page_bp.route("/contact")
def serve_contact():
    return serve_template_with_api_url("contact.html")

@page_bp.route("/register")
def serve_register():
    return serve_template_with_api_url("register.html")

@page_bp.route("/login")
def serve_login():
    return serve_template_with_api_url("login.html")

@page_bp.route("/admin")
def serve_admin():
    if not is_admin_authenticated():
        return redirect("/login")
    return serve_template_with_api_url("admin/dashboard.html")

@page_bp.route("/admin/add")
def serve_admin_add():
    if not is_admin_authenticated():
        return redirect("/login")
    return serve_template_with_api_url("admin/add_product.html")

@page_bp.route("/admin/edit")
def serve_admin_edit():
    if not is_admin_authenticated():
        return redirect("/login")
    return serve_template_with_api_url("admin/edit_product.html")

@page_bp.route("/admin/content")
def serve_admin_content():
    if not is_admin_authenticated():
        return redirect("/login")
    return serve_template_with_api_url("admin/edit_content.html")
