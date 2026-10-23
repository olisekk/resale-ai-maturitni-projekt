from pathlib import Path

from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config("DEBUG", default=True, cast=bool)
SECRET_KEY = config("SECRET_KEY", default="django-insecure-local-development-only")
if not DEBUG and SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured("Set a strong SECRET_KEY when DEBUG is disabled.")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config(
    "SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0, cast=int
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG, cast=bool
)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=not DEBUG, cast=bool)
TRUST_PROXY_SSL_HEADER = config("TRUST_PROXY_SSL_HEADER", default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https") if TRUST_PROXY_SSL_HEADER else None
)
SECURE_CONTENT_TYPE_NOSNIFF = True
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in config("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

ALLOWED_HOSTS = [
    host.strip()
    for host in config("ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]

STORAGE_BACKEND = config("STORAGE_BACKEND", default="local").strip().lower()
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="")
AWS_S3_FILE_OVERWRITE = False

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "products",
]
if STORAGE_BACKEND == "s3":
    if not AWS_STORAGE_BUCKET_NAME:
        raise ImproperlyConfigured("Set AWS_STORAGE_BUCKET_NAME when STORAGE_BACKEND=s3.")
    INSTALLED_APPS.append("storages")
elif STORAGE_BACKEND != "local":
    raise ImproperlyConfigured("STORAGE_BACKEND must be 'local' or 's3'.")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "resale_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "resale_ai.wsgi.application"

DB_ENGINE = config("DB_ENGINE", default="sqlite").strip().lower()
if DB_ENGINE in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="resale_ai"),
            "USER": config("DB_USER", default="resale_ai"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
            "OPTIONS": {"sslmode": config("DB_SSLMODE", default="prefer")},
        }
    }
elif DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    raise ImproperlyConfigured("DB_ENGINE must be 'sqlite' or 'postgresql'.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "cs-cz"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── ResaleAI App Config ──────────────────────────────────────────────────────
APP_NAME = "ResaleAI"
APP_VERSION = "1.0.0"

# ─── eBay / RapidAPI ──────────────────────────────────────────────────────────
RAPIDAPI_KEY = config("RAPIDAPI_KEY", default="")
EBAY_CLIENT_ID = config("EBAY_CLIENT_ID", default="")
EBAY_CLIENT_SECRET = config("EBAY_CLIENT_SECRET", default="")
EBAY_ENVIRONMENT = config("EBAY_ENVIRONMENT", default="production")
EBAY_MARKETPLACE_ID = config("EBAY_MARKETPLACE_ID", default="EBAY_DE").strip().upper()

# ─── Auth redirects ───────────────────────────────────────────────────────────
LOGIN_URL          = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL= "/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {
        "handlers": ["console"],
        "level": config("LOG_LEVEL", default="INFO").upper(),
    },
}
