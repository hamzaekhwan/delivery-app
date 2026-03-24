#!/usr/bin/env sh
set -eu

: "${DJANGO_SETTINGS_MODULE:=config.django.production}"
: "${DJANGO_BIND:=0.0.0.0:8000}"
: "${GUNICORN_WORKERS:=3}"
: "${GUNICORN_THREADS:=2}"

export DJANGO_SETTINGS_MODULE

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec "$@"