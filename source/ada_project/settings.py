# DEV-ONLY, zero .env required

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core (dev only) ---------------------------------------------------------
SECRET_KEY = "django-insecure-dev-key-ok-for-local-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]  # convenient for runserver on LAN / Codespaces

# --- Apps --------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main",
]

# --- Middleware --------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ada_project.urls"

# --- Templates ---------------------------------------------------------------
# APP_DIRS=True will pick up app templates at main/templates/*
# We also allow (optional) project-level templates/ if you add it later.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # safe even if folder doesn't exist
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

WSGI_APPLICATION = "ada_project.wsgi.application"

# --- Database (SQLite for plug-and-play) ------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- Password validation (keep defaults; fine for dev) -----------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ----------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True  
# --- Static & Media (dev convenience) ----------------------------------------
STATIC_URL = "/static/"
# Serve your existing app-level assets from main/static during runserver
STATICFILES_DIRS = [BASE_DIR / "main" / "static"]
# Having STATIC_ROOT set is harmless in dev; ignored by runserver
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Project-specific knobs (kept inline for dev) ----------------------------
PROMETHEUS_URL = "https://host-172-16-100-248.nubes.stfc.ac.uk/"
PROM_DATA_MODE = "prom_on_miss"
# Day by day recommended, the prometheus server tends to time out on larger requests
PROM_CHUNK_DAYS = 1

# --- Logging (simple console) -----------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
