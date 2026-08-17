release: python manage.py migrate && python manage.py seed_demo_data
web: gunicorn pitchpal.wsgi --log-file -
