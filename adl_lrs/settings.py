# Django settings for adl_lrs project.
from os import path
from os.path import dirname, abspath
from configparser import RawConfigParser

ALLOWED_HOSTS = ['*']

# Root of LRS
SETTINGS_DIR = dirname(abspath(__file__))
PROJECT_ROOT = dirname(dirname(SETTINGS_DIR))

config = RawConfigParser()
config.read(SETTINGS_DIR+'/settings.ini')

# If you want to debug
DEBUG = config.getboolean('debug', 'DEBUG')

# Support proxy https (Ex: Amazon ALB)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Set these email values to send the reset password link
# If you do not want this functionality just comment out the
# Forgot Password? link in templates/registration/login.html
EMAIL_BACKEND = config.get('email', 'EMAIL_BACKEND')
EMAIL_HOST = config.get('email', 'EMAIL_HOST')
EMAIL_PORT = config.getint('email', 'EMAIL_PORT')
EMAIL_HOST_USER = config.get('email', 'EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config.get('email', 'EMAIL_HOST_PASSWORD')
EMAIL_USE_SSL = config.getboolean('email', 'EMAIL_USE_SSL')
EMAIL_USE_TLS = config.getboolean('email', 'EMAIL_USE_TLS')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# Google reCAPTCHA Config
# 
# Using reCAPTCHA currently requires a Google API key, which is free.  
USE_GOOGLE_RECAPTCHA = config.getboolean('recaptcha', 'USE_GOOGLE_RECAPTCHA')
RECAPTCHA_PUBLIC_KEY = config.get('recaptcha', 'RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = config.get('recaptcha', 'RECAPTCHA_PRIVATE_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config.get('database', 'NAME'),
        'USER': config.get('database', 'USER'),
        'PASSWORD': config.get('database', 'PASSWORD'),
        'HOST': config.get('database', 'HOST'),
        'PORT': config.getint('database', 'PORT'),
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = config.get('preferences', 'TIME_ZONE')

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = config.get('preferences', 'LANGUAGE_CODE')

# The ID, as an integer, of the current site in the django_site database table.
# This is used so that application data can hook into specific sites and a single database can manage
# content for multiple sites.
SITE_ID = config.getint('site', 'SITE_ID', fallback=1)

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Set this to True if you would like to utilize the webhooks functionality
USE_HOOKS = config.getboolean('hooks', 'USE_HOOKS')

# Newer versions of Django recommend specifying a default auto field here
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = path.join(PROJECT_ROOT, 'media')
# Paths for xapi media
AGENT_PROFILE_UPLOAD_TO = "agent_profile"
ACTIVITY_STATE_UPLOAD_TO = "activity_state"
ACTIVITY_PROFILE_UPLOAD_TO = "activity_profile"
STATEMENT_ATTACHMENT_UPLOAD_TO = "attachment_payloads"

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# Current xAPI version
XAPI_VERSION = '2.0.0'

XAPI_VERSIONS = ['1.0.0', '1.0.1', '1.0.2', '1.0.3', XAPI_VERSION]

# Where to be redirected after logging in
LOGIN_REDIRECT_URL = '/me'

# Me view has a tab of user's statements
STMTS_PER_PAGE = config.getint('preferences', 'STMTS_PER_PAGE')

# Whether HTTP auth or OAuth is enabled
ALLOW_EMPTY_HTTP_AUTH = config.getboolean('auth', 'ALLOW_EMPTY_HTTP_AUTH')
OAUTH_ENABLED = config.getboolean('auth', 'OAUTH_ENABLED')

# OAuth1 callback views
OAUTH_AUTHORIZE_VIEW = 'oauth_provider.views.authorize_client'
OAUTH_CALLBACK_VIEW = 'oauth_provider.views.callback_view'
OAUTH_SIGNATURE_METHODS = ['plaintext', 'hmac-sha1', 'rsa-sha1']

AUTH_USER_MODEL = "auth.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        # Blocks passwords that are common words
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        # Blocks passwords that are entirely numeric
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        # Blocks passwords that are too similar to the username
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    }
]

# List STATEMENTS_WRITE and STATEMENTS_READ_MINE first so they get
# defaulted in oauth2/forms.py
STATE = 1
PROFILE = 1 << 1
DEFINE = 1 << 2
STATEMENTS_READ_MINE = 1 << 3
STATEMENTS_READ = 1 << 4
STATEMENTS_WRITE = 1 << 5
ALL_READ = 1 << 6
ALL = 1 << 7

OAUTH_SCOPES = (
    (STATEMENTS_WRITE, 'statements/write'),
    (STATEMENTS_READ_MINE, 'statements/read/mine'),
    (STATEMENTS_READ, 'statements/read'),
    (STATE, 'state'),
    (DEFINE, 'define'),
    (PROFILE, 'profile'),
    (ALL_READ, 'all/read'),
    (ALL, 'all')
)

AMPQ_USERNAME = config.get('ampq', 'USERNAME')
AMPQ_PASSWORD = config.get('ampq', 'PASSWORD')
AMPQ_HOST = config.get('ampq', 'HOST')
AMPQ_PORT = config.getint('ampq', 'PORT')
AMPQ_VHOST = config.get('ampq', 'VHOST')

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_IGNORE_RESULT = True

# Limit on number of statements the server will return
SERVER_STMT_LIMIT = config.getint('preferences', 'SERVER_STMT_LIMIT')
# Fifteen second timeout to all celery tasks
CELERYD_TASK_SOFT_TIME_LIMIT = 15
# ActivityID resolve timeout (seconds)
ACTIVITY_ID_RESOLVE_TIMEOUT = .2
# Caches for /more endpoint and attachments
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_statement_list',
        'TIMEOUT': 86400,
    },
    'attachment_cache': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'attachment_cache',
        'TIMEOUT': 86400,
    },
}

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = config.get('secrets', 'SECRET_KEY')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # insert your TEMPLATE_DIRS here
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                "adl_lrs.context_processors.recaptcha_config"
            ],
        },
    },
]

USE_ETAGS = False
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = (
    'HEAD',
    'POST',
    'GET',
    'OPTIONS',
    'DELETE',
    'PUT'
)
CORS_ALLOW_HEADERS = (
    'Content-Type',
    'Content-Length',
    'Authorization',
    'If-Match',
    'If-None-Match',
    'X-Experience-API-Version',
    'Accept-Language'
)
CORS_EXPOSE_HEADERS = (
    'ETag',
    'Last-Modified',
    'Cache-Control',
    'Content-Type',
    'Content-Length',
    'WWW-Authenticate',
    'X-Experience-API-Version',
    'Accept-Language'
)
CORS_URLS_REGEX = r"^/(xapi|xAPI)/.*$"

DEFENDER_REDIS_URL = "redis://redis:6379/0"

MIDDLEWARE = (
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'defender.middleware.FailedLoginMiddleware',
)

# Main url router
ROOT_URLCONF = 'adl_lrs.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'adl_lrs.wsgi.application'

ADMIN_REGISTER_APPS = ['adl_lrs', 'lrs', 'oauth_provider']

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'adl_lrs',
    'captcha',
    'lrs',
    'oauth_provider',
    'django.contrib.admin',
    'jsonify',
    'corsheaders',
    'defender'
]

REQUEST_HANDLER_LOG_DIR = path.join(PROJECT_ROOT, 'logs/django_request.log')
DEFAULT_LOG_DIR = path.join(PROJECT_ROOT, 'logs/lrs.log')
CELERY_TASKS_LOG_DIR = path.join(PROJECT_ROOT, 'logs/celery/celery_tasks.log')

CELERYD_HIJACK_ROOT_LOGGER = False

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
# lrs logger is used in views.py for LRS specific logging
# django.request logger logs warning and error server requests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': DEFAULT_LOG_DIR,
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
        'request_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': REQUEST_HANDLER_LOG_DIR,
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
        'celery_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': CELERY_TASKS_LOG_DIR,
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'lrs': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.request': {
            'handlers': ['request_handler'],
            'level': 'WARNING',
            'propagate': True
        },
        'celery-task': {
            'handlers': ['celery_handler'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}
