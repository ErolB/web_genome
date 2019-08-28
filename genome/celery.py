from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'genome.settings')
#os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
redis_url = os.environ['REDIS_URL']
app = Celery('genome_app', broker=redis_url, backend=redis_url)

#app.conf.update(BROKER_URL=os.environ['REDIS_URL'],
#                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
