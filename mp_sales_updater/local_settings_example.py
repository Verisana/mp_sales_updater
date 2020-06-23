import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = ''

DEBUG = False

ALLOWED_HOSTS = ['', '']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

EMAIL_HOST = ''
EMAIL_PORT = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

CELERY_BROKER_URL = 'amqp://localhost'

ADMINS = []

INTERNAL_IPS = ['127.0.0.1']
