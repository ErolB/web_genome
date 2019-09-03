web: gunicorn genome.wsgi --log-file -
main_worker: celery worker --loglevel=info --app=genome.genome.celery.app