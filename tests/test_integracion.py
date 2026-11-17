"""Prueba de integración: endpoint + lógica de negocio + base de datos funcionando juntos."""
import uuid

from rest_framework.test import APITestCase

from comun.eventos import INTERNAL_TOKEN


class AnaliticaIntegracionTests(APITestCase):
    def evento(self, nombre, data):
        return self.client.post("/api/v1/eventos", {"event": nombre, "data": data, "event_id": str(uuid.uuid4())},
                                format="json", HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)

    def test_eventos_alimentan_los_reportes(self):
        poliza, sin = str(uuid.uuid4()), str(uuid.uuid4())
        self.evento("policy.issued", {"id_poliza": poliza, "product_type": "auto", "premium": "1200000"})
        self.evento("claim.opened", {"id_siniestro": sin, "id_poliza": poliza, "product_type": "auto",
                                     "estimated_amount": "2000000", "reported_at": "2026-11-17T10:00:00Z",
                                     "incident_date": "2026-11-16T10:00:00Z"})
        datos = self.client.get("/api/v1/analitica/siniestralidad").data
        self.assertEqual(datos["totales"]["claim_count"], 1)
