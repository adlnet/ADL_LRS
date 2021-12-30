

import os

from celery import Celery

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adl_lrs.settings')

from django.conf import settings

app = Celery('lrs',
             broker='amqp://%s:%s@%s:%s/%s' % (
             	settings.AMPQ_USERNAME, settings.AMPQ_PASSWORD,
             	settings.AMPQ_HOST, settings.AMPQ_PORT, 
             	settings.AMPQ_VHOST),
             include=['lrs.tasks'])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))