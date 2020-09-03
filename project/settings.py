"""
Django settings for project.
Generated by 'django-admin startproject' using Django 3.0.7.
"""

import os
import ast

from django_query_profiler.settings import *
from dotenv import load_dotenv

from core.utils.logging_helpers import get_logger

load_dotenv()

logger = get_logger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = True if os.getenv('DEBUG') == 'True' else False
ALLOWED_HOSTS = ast.literal_eval(os.getenv('ALLOWED_HOSTS'))
INTERNAL_IPS = ast.literal_eval(os.getenv('INTERNAL_IPS'))
CSRF_COOKIE_SECURE = True if os.getenv('CSRF_COOKIE_SECURE') == 'True' else False
SESSION_COOKIE_SECURE = True if os.getenv('SESSION_COOKIE_SECURE') == 'True' else False
SECURE_SSL_REDIRECT = True if os.getenv('SECURE_SSL_REDIRECT') == 'True' else False
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 0))

INSTALLED_APPS = [
    'django_extensions',
    'rest_framework',
    'mptt',
    'core.apps.CoreConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
]

MIDDLEWARE = [
    'pyinstrument.middleware.ProfilerMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_BACKEND', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', 'default_database'),
        'USER': os.getenv('DB_USERNAME', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv('TIME_ZONE')

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s: %(levelname)s %(module)s (%(process)d): %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'FullJsonFormatter': {
            '()': 'core.utils.logging_helpers.FullJsonFormatter'
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.getenv('JSON_LOG_FILE'),
            'level': 'INFO',
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
        },
        'telegram': {
            'class': 'core.utils.logging_helpers.TelegramHandler',
            'level': 'ERROR',
            'formatter': 'FullJsonFormatter',
            'token': os.getenv('TELEGRAM_TOKEN'),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID'),
        }
    },
    'loggers': {
        'main': {
            'handlers': ['console', 'file', 'telegram'],
            'level': 'DEBUG',
        },
    }
}

WEBSHARE_PROXY_API = os.getenv('WEBSHARE_PROXY_API')
