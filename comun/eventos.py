"""
Bus de eventos de InsureFlow (secciones 5.10, 6.2 y 6.6 del documento).

Cada microservicio publica sus eventos con `publicar()`. Celery (con Redis como broker)
encola una tarea por cada microservicio suscrito y la entrega por HTTP a su endpoint
/api/v1/eventos, con reintentos y backoff exponencial. Así los microservicios se
comunican aunque estén desplegados en cuentas distintas de Render.

La URL de cada suscriptor se configura con la variable <SERVICIO>_SERVICE_URL,
por ejemplo PAYMENT_SERVICE_URL=https://payment-service-xxxx.onrender.com
"""
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import requests
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from .celery_app import app
from .servicio import SERVICE_NAME

logger = logging.getLogger("eventos")

# Evento -> microservicios que lo consumen.
SUSCRIPTORES = {
    "policyholder.created": [],
    "policyholder.kyc_updated": [],
    "policy.issued": ["NOTIFICATION", "ANALYTICS"],
    "policy.renewed": ["NOTIFICATION", "ANALYTICS"],
    "policy.cancelled": ["NOTIFICATION", "ANALYTICS"],
    "claim.opened": ["ADJUSTER", "NOTIFICATION", "ANALYTICS"],
    "claim.documentation_requested": ["NOTIFICATION"],
    "claim.approved": ["PAYMENT", "ANALYTICS"],
    "claim.rejected": ["NOTIFICATION", "ANALYTICS"],
    "inspection.scheduled": ["CLAIMS"],
    "inspection.completed": ["CLAIMS", "DOCUMENT"],
    "payment.completed": ["CLAIMS", "DOCUMENT", "NOTIFICATION", "ANALYTICS"],
    "payment.failed": ["CLAIMS", "NOTIFICATION"],
    "document.uploaded": ["CLAIMS"],
}

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "insureflow-dev-token")


def publicar(evento, data):
    """Publica un evento para todos sus suscriptores (después del commit en la BD)."""
    payload = json.loads(json.dumps({
        "event_id": str(uuid.uuid4()),
        "event": evento,
        "source": SERVICE_NAME,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }, cls=DjangoJSONEncoder))

    logger.info("evento publicado", extra={"evento": evento, "data": payload["data"]})

    for destino in SUSCRIPTORES.get(evento, []):
        url = os.getenv(f"{destino}_SERVICE_URL")
        if not url:
            logger.warning("suscriptor sin URL configurada", extra={"evento": evento, "destino": destino})
            continue
        transaction.on_commit(lambda u=url: entregar_evento.delay(u, payload))

    return payload


@app.task(bind=True, max_retries=5)
def entregar_evento(self, url, payload):
    """Entrega el evento por HTTP. Reintenta con backoff exponencial (5s, 10s, 20s...)."""
    destino = f"{url.rstrip('/')}/api/v1/eventos"
    try:
        resp = requests.post(
            destino,
            json=payload,
            headers={"X-Internal-Token": INTERNAL_TOKEN},
            timeout=(10, 90),  # Render despierta un servicio dormido en ~1 minuto
        )
        if resp.status_code >= 500:
            raise requests.HTTPError(f"HTTP {resp.status_code}")
    except requests.RequestException as exc:
        logger.warning("fallo entregando evento", extra={"evento": payload["event"], "destino": destino, "error": str(exc)})
        if app.conf.task_always_eager:
            return None
        raise self.retry(exc=exc, countdown=5 * 2 ** self.request.retries)

    if resp.status_code >= 400:
        logger.error("evento rechazado", extra={"evento": payload["event"], "destino": destino, "status": resp.status_code})
    return resp.status_code
