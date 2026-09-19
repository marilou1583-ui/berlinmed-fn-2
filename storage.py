import os
import uuid
from io import BytesIO

import requests
from flask import current_app
from PIL import Image, UnidentifiedImageError


def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def generate_unique_filename():
    return f"{uuid.uuid4().hex}.png"


def save_product_image(file_storage):
    """
    Validates and saves an uploaded product image.
    Returns the stored filename, or None if no file was provided.
    Raises ValueError if the file is invalid.
    """
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("Invalid file type. Allowed: " + ", ".join(sorted(current_app.config["ALLOWED_IMAGE_EXTENSIONS"])))

    try:
        image = Image.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)
        if image.width * image.height > current_app.config["MAX_IMAGE_PIXELS"]:
            raise ValueError("Image dimensions exceed the allowed limit")
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == "Image dimensions exceed the allowed limit":
            raise
        raise ValueError("Invalid image file") from error

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info else "RGB")

    image_data = BytesIO()
    image.save(image_data, format="PNG", optimize=True)
    image_data.seek(0)
    filename = generate_unique_filename()

    if current_app.config.get("SUPABASE_URL") and current_app.config.get("SUPABASE_KEY"):
        return _save_to_supabase(image_data, filename)
    elif current_app.config.get("S3_BUCKET"):
        _save_to_s3(image_data, filename)
        return filename
    else:
        _save_locally(image_data, filename)
        return filename


def _save_locally(image_data, filename):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    with open(os.path.join(upload_folder, filename), "wb") as image_file:
        image_file.write(image_data.getbuffer())


def _save_to_s3(image_data, filename):
    try:
        import boto3
    except ImportError:
        raise RuntimeError("boto3 is required for S3 uploads. Install it with: pip install boto3")

    client = boto3.client(
        "s3",
        region_name=current_app.config["S3_REGION"],
        aws_access_key_id=current_app.config["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["S3_SECRET_ACCESS_KEY"],
    )
    client.upload_fileobj(
        image_data,
        current_app.config["S3_BUCKET"],
        filename,
        ExtraArgs={"ContentType": "image/png"},
    )


def _save_to_supabase(image_data, filename):
    supabase_url = current_app.config["SUPABASE_URL"].rstrip("/")
    supabase_key = current_app.config["SUPABASE_KEY"]
    bucket = current_app.config.get("SUPABASE_BUCKET", "med-images")

    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"

    response = requests.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "image/png",
        },
        data=image_data.getvalue(),
        timeout=30,
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Supabase upload failed: {response.status_code} {response.text}")

    return f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"