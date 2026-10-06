#!/bin/sh
set -e

python ensure_db.py
python manage.py migrate --noinput

# En Render (plan gratis) el worker de Celery corre dentro del mismo contenedor.
if [ "$RUN_WORKER_IN_WEB" = "1" ]; then
    celery -A comun.celery_app worker -Q analytics --loglevel=info --concurrency=1 &
fi

exec gunicorn analytics_service.wsgi:application --bind 0.0.0.0:${PORT:-8000} \
    --worker-class gthread --threads 4 --timeout 120
