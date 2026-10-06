from django.db import models


class EventoProcesado(models.Model):
    """Eventos ya procesados: evita procesar dos veces un evento reintentado (idempotencia)."""

    event_id = models.UUIDField(primary_key=True)
    event = models.CharField(max_length=100)
    source = models.CharField(max_length=50, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "evento_procesado"
