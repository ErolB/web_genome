web: gunicorn genome.wsgi --log-file -
main_worker: celery worker --loglevel=info --app=genome.celery.app