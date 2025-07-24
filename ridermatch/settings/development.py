"""
Settings per ambiente di sviluppo
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database SQLite per sviluppo
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email backend per sviluppo (stampa nella console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disabilita cache in sviluppo
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Configurazioni aggiuntive per sviluppo
INTERNAL_IPS = ['127.0.0.1']

# Telegram Bot Token (da file .env)
try:
    from decouple import config
    TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
except ImportError:
    TELEGRAM_BOT_TOKEN = ''

# Debug toolbar se disponibile
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
except ImportError:
    pass