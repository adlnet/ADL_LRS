import os
import sys
import linecache
from fabric.api import local

def setup_env():
    INSTALL_STEPS = ['virtualenv ../env;. ../env/bin/activate;pip install -r requirements.txt;deactivate']
    for step in INSTALL_STEPS:
        local(step)

    # Bug fix for django 1.4 package (not patched in d/l for some reason now)
    try:
        line_140 = linecache.getline('../env/local/lib/python2.7/site-packages/django/utils/translation/trans_real.py', 140)
    except Exception, e:
        line_140 = ""

    if not line_140 or line_140 == '\n':
        with open('../env/local/lib/python2.7/site-packages/django/utils/translation/trans_real.py', 'r') as f:
            data = f.readlines()
    
        data[139] = "        if res is None:\n"
        data[140] = "            return gettext_module.NullTranslations()\n"
    
        with open('../env/local/lib/python2.7/site-packages/django/utils/translation/trans_real.py', 'w') as f:
            data = f.writelines(data)


def setup_lrs():
    # Media folder names
    agent_profile = 'agent_profile'
    activity_profile = 'activity_profile'
    activity_state = 'activity_state'
    statement_attachments = 'attachment_payloads'
    
    # Add env packages and project to the path
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    if not cwd in sys.path:
        sys.path.append(cwd)
    
    env_dir = os.path.join(cwd, '../env/lib/python2.7/site-packages')
    if not env_dir in sys.path:
        sys.path.append(env_dir)

    log_dir = os.path.join(cwd, '../logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Add settings module so fab file can see it
    os.environ['DJANGO_SETTINGS_MODULE'] = "adl_lrs.settings"
    from django.conf import settings
    adldir = settings.MEDIA_ROOT

    # Create media directories
    if not os.path.exists(os.path.join(adldir,activity_profile)):
        os.makedirs(os.path.join(adldir,activity_profile))

    if not os.path.exists(os.path.join(adldir,activity_state)):
        os.makedirs(os.path.join(adldir,activity_state))

    if not os.path.exists(os.path.join(adldir,agent_profile)):
        os.makedirs(os.path.join(adldir,agent_profile))

    if not os.path.exists(os.path.join(adldir,statement_attachments)):
        os.makedirs(os.path.join(adldir,statement_attachments))

    # Create cache tables and sync the db
    local('./manage.py createcachetable cache_statement_list')
    local('./manage.py createcachetable attachment_cache')
    local('./manage.py syncdb')

    print "If you see an error code 23 while running rync it's only because there were no files to sync in the django_extensions directory. \
    That occurs when the files are where they are supposed to be in the first place."
    # Fixes admin templates for django
    local('rsync -av ../env/django_extensions/ ../env/local/lib/python2.7/site-packages/django_extensions/')
    local('rm -rf ../env/django_extensions/')

    local('rsync -av ../env/django/ ../env/local/lib/python2.7/site-packages/django/')
    local('rm -rf ../env/django/')


def test_lrs():
    local('./manage.py test lrs')