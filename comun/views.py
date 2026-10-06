import importlib
import logging

from django.conf import settings
from django.db import connection, transaction
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .eventos import INTERNAL_TOKEN
from .models import EventoProcesado
from .servicio import SERVICE_NAME

logger = logging.getLogger("eventos")


@api_view(["GET"])
def health(request):
    try:
        connection.ensure_connection()
        db = "ok"
    except Exception:
        db = "error"

    codigo = status.HTTP_200_OK if db == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response({"service": SERVICE_NAME, "status": db, "database": db}, status=codigo)


@api_view(["POST"])
def recibir_evento(request):
    """Endpoint interno donde otros microservicios entregan sus eventos."""
    if request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
        return Response(
            {"code": "UNAUTHORIZED", "message": "Token interno inválido."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    evento = request.data.get("event")
    event_id = request.data.get("event_id")
    handlers = importlib.import_module(settings.EVENT_HANDLERS_MODULE).HANDLERS
    handler = handlers.get(evento)

    if handler is None:
        return Response({"status": "ignored", "event": evento})

    if event_id and EventoProcesado.objects.filter(event_id=event_id).exists():
        return Response({"status": "duplicate", "event": evento})

    logger.info("evento recibido", extra={"evento": evento, "origen": request.data.get("source")})
    with transaction.atomic():
        handler(request.data.get("data") or {})
        if event_id:
            EventoProcesado.objects.create(event_id=event_id, event=evento, source=request.data.get("source") or "")

    return Response({"status": "processed", "event": evento})
