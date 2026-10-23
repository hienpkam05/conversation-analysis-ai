from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = "dev-only-change-me"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "transcriptions",
    "consultation_quality",
    "conversation_followup",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "recruitment_ai.middleware.SimpleCorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "recruitment_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "recruitment_ai.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
CSRF_TRUSTED_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("127.0.0.1", "localhost")
    for port in (5173, 5174, 5175)
]
CSRF_FAILURE_VIEW = "consultation_quality.review_views.csrf_failure"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 300
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 20

WHISPER_DEFAULT_MODEL = "tiny"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_CPU_THREADS = 8
WHISPER_OUTPUT_DIR = PROJECT_ROOT / "output"
HUGGINGFACE_CACHE_DIR = PROJECT_ROOT / "models" / "huggingface"

QUALITY_MODEL_DIR = os.environ.get("QUALITY_MODEL_DIR", "")
QUALITY_JOB_TIMEOUT = 900
QUALITY_QUEUE_LIMIT = 20
QUALITY_USER_QUEUE_LIMIT = 2
