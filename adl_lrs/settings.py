# Django settings for adl_lrs project.
from os import path
from os.path import dirname, abspath

# Root of LRS
SETTINGS_DIR = dirname(abspath(__file__))
PROJECT_ROOT = dirname(dirname(SETTINGS_DIR))

# If you want to debug
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'lrs',
        'USER': 'root',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '',
    }    
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

# The ID, as an integer, of the current site in the django_site database table.
# This is used so that application data can hook into specific sites and a single database can manage
# content for multiple sites.
SITE_ID = 1
SITE_SCHEME = 'http'
SITE_DOMAIN = 'localhost:8000'
# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = path.join(PROJECT_ROOT, 'media')

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
XAPI_VERSION = '1.0.2'

XAPI_VERSIONS = ['1.0.1', '1.0.2']

# Where to be redirected after logging in
LOGIN_REDIRECT_URL = '/XAPI/me'

# Me view has a tab of user's statements
STMTS_PER_PAGE = 10

# Whether HTTP auth or OAuth is enabled
ALLOW_EMPTY_HTTP_AUTH = False
OAUTH_ENABLED = True

# OAuth1 callback views
OAUTH_AUTHORIZE_VIEW = 'oauth_provider.views.authorize_client'
OAUTH_CALLBACK_VIEW = 'oauth_provider.views.callback_view'
OAUTH_SIGNATURE_METHODS = ['plaintext','hmac-sha1','rsa-sha1']
OAUTH_REALM_KEY_NAME = '%s://%s/xAPI' % (SITE_SCHEME, SITE_DOMAIN)

# THIS IS OAUTH2 STUFF
STATE = 1
PROFILE = 1 << 1
DEFINE = 1 << 2
STATEMENTS_READ_MINE = 1 << 3
STATEMENTS_READ = 1 << 4
STATEMENTS_WRITE = 1 << 5
ALL_READ = 1 << 6
ALL = 1 << 7

# List STATEMENTS_WRITE and STATEMENTS_READ_MINE first so they get defaulted in oauth2/forms.py
OAUTH_SCOPES = (
        (STATEMENTS_WRITE,'statements/write'),
        (STATEMENTS_READ_MINE,'statements/read/mine'),
        (STATEMENTS_READ,'statements/read'),
        (STATE,'state'),
        (DEFINE,'define'),
        (PROFILE,'profile'),
        (ALL_READ,'all/read'),
        (ALL,'all')
    )
SESSION_KEY = 'oauth2'

# Limit on number of statements the server will return
SERVER_STMT_LIMIT = 100

# Enable celery for activityID metadata retrieval
CELERY_ENABLED = True
# One minute timeout to all celery tasks
CELERYD_TASK_SOFT_TIME_LIMIT = 60
# ActivityID resolve timeout (seconds)
ACTIVITY_ID_RESOLVE_TIMEOUT = .2
# Caches for /more endpoint and attachments
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_statement_list',
        'TIMEOUT': 86400,
    },
    'attachment_cache':{
        'BACKEND':'django.core.cache.backends.db.DatabaseCache',
        'LOCATION':'attachment_cache',
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
SECRET_KEY = 'v+m%^r0x)$_x8i3trn*duc6vd-yju0kx2b#9lk0sn2k^7cgyp5'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages"
)


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lrs.util.AllowOriginMiddleware.AllowOriginMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

# Main url router
ROOT_URLCONF = 'adl_lrs.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'adl_lrs.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'lrs',
    'oauth_provider',
    'oauth2_provider.provider',
    'oauth2_provider.provider.oauth2',
    'django.contrib.admin',
    'django_extensions',
    'jsonify',
    'south',
    'endless_pagination',
)

REQUEST_HANDLER_LOG_DIR = path.join(PROJECT_ROOT, 'logs/django_request.log')
DEFAULT_LOG_DIR = path.join(PROJECT_ROOT, 'logs/lrs.log')
CELERY_TASKS_LOG_DIR =  path.join(PROJECT_ROOT, 'logs/celery_tasks.log')

CELERYD_HIJACK_ROOT_LOGGER = False

# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
# lrs logger is used in views.py for LRS specific logging
# django.request logger logs warning and error server requests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': u'%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'standard': {
            'format': u'%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'simple': {
            'format': u'%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': DEFAULT_LOG_DIR,
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        },  
        'request_handler': {
                'level':'DEBUG',
                'class':'logging.handlers.RotatingFileHandler',
                'filename': REQUEST_HANDLER_LOG_DIR,
                'maxBytes': 1024*1024*5, # 5 MB
                'backupCount': 5,
                'formatter':'standard',
        },
        'celery_handler': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': CELERY_TASKS_LOG_DIR,
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
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
            'propagate': False
        },
        'celery-act-task': {
            'handlers': ['celery_handler'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}
