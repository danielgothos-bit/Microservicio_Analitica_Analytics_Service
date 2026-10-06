import os

from celery import Celery

from .servicio import SERVICE_NAME, SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", SETTINGS_MODULE)

app = Celery(SERVICE_NAME, broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Cola propia del microservicio, para no mezclar tareas si varios comparten Redis.
app.conf.task_default_queue = SERVICE_NAME
app.conf.broker_connection_retry_on_startup = True

# CELERY_EAGER=1 ejecuta las tareas en el mismo proceso (útil sin Redis y en pruebas).
app.conf.task_always_eager = os.getenv("CELERY_EAGER") == "1"

app.autodiscover_tasks(["comun"], related_name="eventos")
