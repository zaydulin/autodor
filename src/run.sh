#!/bin/bash

set -e

# Load base data
python manage.py migrate --noinput

## Load fixtures data
# python manage.py initialize


if [[ $DJANGO_DEBUG -eq 0 ]]; then
  echo "Use production settings"
  # Load static files
  python manage.py collectstatic --noinput
  daphne -b 0.0.0.0 -p 8001 _project.asgi:application --application-close-timeout 1 &
  gunicorn -w 4 --env DJANGO_SETTINGS_MODULE=_project.settings _project.wsgi -b 0.0.0.0:8000
else
  echo "Use development settings"
  python3 manage.py runserver 0.0.0.0:8000
fi