from dotenv import load_dotenv
load_dotenv()

import builtins
import sys

# Silence print statements during server run to keep terminal clean
# but allow them if running tests or interactive shells
if not any(arg in sys.argv for arg in ['test', 'shell']):
    builtins.print = lambda *args, **kwargs: None

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
print("\n\nDEBUG REPORT DIR: ", BASE_DIR)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'stipendieportalen.se',
    'www.stipendieportalen.se',
    'app.stipendieportalen.se',
    'localhost',
    '127.0.0.1',
]
# CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_ALL_ORIGINS = False 

CORS_ALLOWED_ORIGINS = [ 

    'https://stipendieportalen.se', 

    'https://www.stipendieportalen.se', 

    'https://app.stipendieportalen.se', 

] 


CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "ngrok-skip-browser-warning"
)

CSRF_TRUSTED_ORIGINS = [
    'https://stipendieportalen.se',
    'https://www.stipendieportalen.se',
    'https://app.stipendieportalen.se',
]
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'send.one.com').strip()
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587').strip())
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'django_cleanup.apps.CleanupConfig',
    'app',
    'drf_spectacular',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'STEPO_BACKEND.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'STEPO_BACKEND.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

import socket

postgres_host = os.environ.get('POSTGRES_HOST', 'db')
if postgres_host == 'db':
    try:
        socket.gethostbyname('db')
    except socket.gaierror:
        postgres_host = '127.0.0.1'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'stepo_db'),
        'USER': os.environ.get('POSTGRES_USER', 'stepo_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': postgres_host,
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

REST_FRAMEWORK = {
    # YOUR SETTINGS
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'GrantFinder AI',
    'DESCRIPTION': 'Your project description',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATASET_PATH = BASE_DIR/'scholarships.xlsx'
REPORT_DIR = 'reports'

MEDIA_URL = 'media/'
MEDIA_ROOT = 'reports'
WATERMARK_PATH = (BASE_DIR/'watermark.png').__str__()

# Check if the directory exists
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)
    print(f"Directory '{REPORT_DIR}' created.")
else:
    print(f"Directory '{REPORT_DIR}' already exists.")

# ── Local development override ──────────────────────────────────────────────
# Set DJANGO_LOCAL_DEV=1 in your terminal to use SQLite locally
# without needing Docker/PostgreSQL running.
# Example: export DJANGO_LOCAL_DEV=1 && python manage.py runserver
if os.environ.get('DJANGO_LOCAL_DEV'):
    DEBUG = True
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print("🔧 LOCAL DEV MODE — using SQLite")


# ── Production Security Settings ─────────────────────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # nginx already sets this
    SECURE_CONTENT_TYPE_NOSNIFF = True




# docker compose up -d --build && docker exec -it stepo_web python manage.py migrate && docker exec -it stepo_web python manage.py collectstatic --noinput