import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "False") == "True"

    SECRET_KEY = os.getenv("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    UPLOAD_FOLDER = "static/images"
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5")) * 1024 * 1024
    MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "16000000"))

    S3_BUCKET = os.getenv("S3_BUCKET")
    S3_REGION = os.getenv("S3_REGION")
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))

    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per hour")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")

    MAX_ORDER_ITEMS = int(os.getenv("MAX_ORDER_ITEMS", "50"))
    MAX_ITEM_QUANTITY = int(os.getenv("MAX_ITEM_QUANTITY", "100"))

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "med-images")

    @classmethod
    def validate(cls):
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "DATABASE_URL is not set. Refusing to start: without it the app "
                "would silently fall back to a throwaway local SQLite file instead "
                "of the real database. Set DATABASE_URL (see .env.example)."
            )

        if cls.ENV != "production":
            return
        if cls.SQLALCHEMY_DATABASE_URI.lower().startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must use PostgreSQL when FLASK_ENV=production.")
        if not cls.SECRET_KEY or not cls.JWT_SECRET_KEY:
            raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must be set when FLASK_ENV=production.")
