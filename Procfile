web: gunicorn genome.wsgi --log-file -
main_worker: celery worker --app=tasks.app --loglevel=info