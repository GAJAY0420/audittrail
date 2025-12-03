"""Django settings supporting standalone execution of tiger_audit_trail."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    """Return a boolean value from an environment variable."""

    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> List[str]:
    """Return a sanitized list from a comma separated environment variable."""

    raw_value = os.environ.get(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_database_config(url: str | None) -> Dict[str, Any]:
    """Create a Django DATABASES entry from DATABASE_URL or fall back to SQLite."""

    default = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }
    if not url:
        return default
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme in {"postgres", "postgresql", "psql"}:
        engine = "django.db.backends.postgresql"
    elif scheme in {"mysql"}:
        engine = "django.db.backends.mysql"
    elif scheme in {"sqlite", "sqlite3"}:
        engine = "django.db.backends.sqlite3"
    else:
        raise RuntimeError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")
    config: Dict[str, Any] = {"ENGINE": engine}
    if engine == "django.db.backends.sqlite3":
        config["NAME"] = parsed.path.lstrip("/") or str(BASE_DIR / "db.sqlite3")
    else:
        config.update(
            {
                "NAME": parsed.path.lstrip("/") or "audit_trail",
                "USER": parsed.username or "",
                "PASSWORD": parsed.password or "",
                "HOST": parsed.hostname or "localhost",
                "PORT": str(parsed.port or ""),
            }
        )
    return config


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "tiger_audit_trail")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "corsheaders",
    "rest_framework",
    "audit_trail",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit_trail.middleware.CustomPermissionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "audit_trail" / "ui" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# DATABASES = {"default": build_database_config(os.environ.get("DATABASE_URL"))}
DATABASES = {
    "default": build_database_config(
        os.environ.get(
            "DATABASE_URL", "postgres://insurance:insurance@localhost:5432/audittrail"
        )
    )
}

AUTH_PASSWORD_VALIDATORS: List[Dict[str, str]] = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "audit_trail" / "ui" / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "audit_trail.api.pagination.TimelinePagination",
    "PAGE_SIZE": 50,
}

AUDITTRAIL_USE_CELERY = env_bool("AUDITTRAIL_USE_CELERY", False)
AUDITTRAIL_ACTOR_RESOLVER = "audit_trail.middleware.get_current_user"

LOGIN_URL = "audit-login"
LOGIN_REDIRECT_URL = "audit-trail-timeline"

###############################################################################
# SESSION SETTINGS
###############################################################################

SESSION_SECURITY_ENABLED = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_ENGINE = os.environ.get(
    "DJANGO_SESSION_ENGINE", "django.contrib.sessions.backends.db"
)
SESSION_COOKIE_AGE = int(os.environ.get("DJANGO_SESSION_COOKIE_AGE", 60 * 60 * 24 * 14))
# SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", False)
SESSION_COOKIE_HTTPONLY = env_bool("DJANGO_SESSION_COOKIE_HTTPONLY", True)

###############################################################################
# CELERY SETTINGS
###############################################################################

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_TASK_DEFAULT_QUEUE = os.environ.get(
    "CELERY_TASK_DEFAULT_QUEUE", "audit_trail_outbox"
)
CELERY_TASK_ALWAYS_EAGER = not AUDITTRAIL_USE_CELERY

AUDITTRAIL_STORAGE_BACKEND = os.environ.get(
    "AUDITTRAIL_STORAGE_BACKEND",
    "audit_trail.storage.backends.dynamo.DynamoStorageBackend",
)
AUDITTRAIL_STORAGE_CONFIG = {
    "table": os.environ.get("AUDITTRAIL_DYNAMODB_TABLE", "audit_events"),
    "region": os.environ.get("AUDITTRAIL_AWS_REGION", "eu-central-1"),
}
AUDITTRAIL_STREAMING_ENABLED = env_bool("AUDITTRAIL_STREAMING_ENABLED", False)
AUDITTRAIL_STREAM_PROVIDER = os.environ.get(
    "AUDITTRAIL_STREAM_PROVIDER",
    "audit_trail.streaming.kafka.KafkaPublisher",
)
AUDITTRAIL_STREAM_CONFIG: Dict[str, Any] = {
    "topic": os.environ.get("AUDITTRAIL_KAFKA_TOPIC", "audit-events"),
    "bootstrap_servers": os.environ.get("AUDITTRAIL_KAFKA_SERVERS", "localhost:9092"),
}
AUDITTRAIL_SUMMARIZER = os.environ.get(
    "AUDITTRAIL_SUMMARIZER", "nltk"
)  # "grammar" / "multilang" / "llm" / "nltk"
AUDITTRAIL_SUMMARIZER_LOCALE = os.environ.get("AUDITTRAIL_SUMMARIZER_LOCALE", "en")

###############################################################################
# LLM SETTINGS
###############################################################################

LLM_PROMPT = """
    You are an expert Django audit history summariser.
    You receive audit logs for Django model instances, including:

    Scalar fields (e.g. CharField, IntegerField, DecimalField, BooleanField, DateTimeField, etc.)

    Foreign key (FK) fields (single related objects)

    Many-to-many (M2M) fields (lists of related objects)

    Your job is to convert these raw changes into clear, human-readable summaries for end users (non-technical business users).

    General rules:

    Write in concise, professional English (Indian business tone).

    Group changes by model instance and operation (Created / Updated / Deleted).

    Use bullet points or short paragraphs rather than long prose.

    Do not show internal field names or IDs directly if a label/value is given (e.g. show “Customer: ABC Logistics” instead of customer_id: 123).

    Scalar fields:

    Describe as:

    “<Field label> changed from <old value> to <new value>.”

    For booleans: use friendly language (e.g. “Enabled”/“Disabled”, “Yes”/“No”).

    For dates: format as DD-MMM-YYYY (e.g. 03-Dec-2025).

    Foreign key fields (FK):

    Prefer the related object’s string representation / name (e.g. partner_name, policy_number).

    Describe as:

    “<Field label> changed from <old related label> to <new related label>.”

    Many-to-many fields (M2M):

    Identify added and removed items separately.

    Use patterns like:

    “Added to <Field label>: A, B, C.”

    “Removed from <Field label>: X, Y.”

    If nothing changed in an M2M field, ignore it.

    Operations:

    If action is create: summarise as “Created <Model label> with …”.

    If action is update: summarise only changed fields.

    If action is delete: summarise key identifiers (e.g. number, name) and mention deletion.

    Output format:

    Provide a short title line with model and key identifier.
    Example:
    “Policy #POL12345 – Endorsement Update”

    Then bullet points for each relevant field change.

    Do not invent data that is not present in the input.

    If the input is empty or contains no actual changes, reply with:
    “No significant changes recorded.”
"""

AUDITTRAIL_LLM_ENDPOINT = os.environ.get(
    "AUDITTRAIL_LLM_ENDPOINT", "http://localhost:8000/llm"
)
AUDITTRAIL_LLM_TOKEN = os.environ.get("AUDITTRAIL_LLM_TOKEN", "test-token")
AUDITTRAIL_LLM_PROVIDER = os.environ.get("AUDITTRAIL_LLM_PROVIDER", "bedrock")
AUDITTRAIL_LLM_MODEL = os.environ.get("AUDITTRAIL_LLM_MODEL", "nova-lite")
AUDITTRAIL_LLM_SYSTEM_PROMPT = os.environ.get(
    "AUDITTRAIL_LLM_SYSTEM_PROMPT",
    LLM_PROMPT.strip(),
)
AUDITTRAIL_LLM_ROLE = os.environ.get("AUDITTRAIL_LLM_ROLE", "audit_summarizer")
AUDITTRAIL_LLM_MAX_TOKENS = int(os.environ.get("AUDITTRAIL_LLM_MAX_TOKENS", "256"))
AUDITTRAIL_LLM_TEMPERATURE = float(os.environ.get("AUDITTRAIL_LLM_TEMPERATURE", "0.1"))
AUDITTRAIL_LLM_TOP_P = float(os.environ.get("AUDITTRAIL_LLM_TOP_P", "0.9"))

###############################################################################
# MISC SETTINGS
###############################################################################

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
