import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = ''

DEBUG = False

ALLOWED_HOSTS = ['', '']

INTERNAL_IPS = ['127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

JSON_LOG_FILE = 'logs/main.json.log'
DJANGO_DEBUG_LOG_FILE = 'logs/django.json.log'
TELEGRAM_TOKEN = ''
TELEGRAM_LOG_CHAT_ID = ''

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
            'filename': JSON_LOG_FILE,
            'level': 'INFO',
            'formatter': 'FullJsonFormatter'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose'
        },
        'telegram_error': {
            'class': 'core.utils.logging_helpers.TelegramHandler',
            'token': TELEGRAM_TOKEN,
            'chat_id': TELEGRAM_LOG_CHAT_ID,
            'level': 'WARNING',
            'formatter': 'FullJsonFormatter',
        },
    },
    'loggers': {
        'main': {
            'handlers': ['console', 'file', 'telegram_error'],
            'level': 'DEBUG',
        },
    }
}
