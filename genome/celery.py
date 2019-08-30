from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'genome.settings')
#os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
broker_url = 'redis://h:pe133a585ca010fe846e05901e80acc9dcd0a7c23a7dc80c4ab22ae8cdaed7c1c@ec2-3-221-165-119.compute-1.amazonaws.com:23889'
os.environ.setdefault('REDIS_URL', broker_url)
print('Redis URL: %s' % os.environ['REDIS_URL'])
app = Celery('genome_app', broker=broker_url, backend=broker_url)

app.conf.update(BROKER_URL=os.environ['REDIS_URL'],
                CELERY_RESULT_BACKEND=os.environ['REDIS_URL'])

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
