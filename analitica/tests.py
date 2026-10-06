import uuid

from django.utils import timezone
from rest_framework.test import APITestCase

from comun.eventos import INTERNAL_TOKEN

ASEGURADO = str(uuid.uuid4())
POLIZA = str(uuid.uuid4())


class AnaliticaTests(APITestCase):
    def evento(self, nombre, data, event_id=None):
        return self.client.post("/api/v1/eventos", {
            "event_id": event_id or str(uuid.uuid4()), "event": nombre, "data": data,
        }, format="json", HTTP_X_INTERNAL_TOKEN=INTERNAL_TOKEN)

    def abrir(self, **extra):
        siniestro = str(uuid.uuid4())
        self.evento("claim.opened", {
            "id_siniestro": siniestro, "id_poliza": POLIZA, "id_asegurado": ASEGURADO, "product_type": "auto",
            "estimated_amount": "4000000.00", "reported_at": timezone.now().isoformat(),
            "incident_date": timezone.now().isoformat(), "premium": "1200000.00",
            "policy_effective_date": "2026-01-01", **extra,
        })
        return siniestro

    def test_siniestralidad_y_evento_duplicado(self):
        id_evento = str(uuid.uuid4())
        data = {"id_siniestro": str(uuid.uuid4()), "product_type": "hogar", "estimated_amount": "100",
                "reported_at": timezone.now().isoformat()}
        self.evento("claim.opened", data, id_evento)
        resp = self.evento("claim.opened", data, id_evento)
        self.assertEqual(resp.data["status"], "duplicate")

        resp = self.client.get("/api/v1/analitica/siniestralidad?product_type=hogar")
        self.assertEqual(resp.data["totales"]["claim_count"], 1)

    def test_resolucion_y_rentabilidad(self):
        self.evento("policy.issued", {"id_poliza": POLIZA, "product_type": "auto", "id_asegurado": ASEGURADO})
        siniestro = self.abrir()
        self.evento("claim.approved", {"id_siniestro": siniestro})
        self.evento("payment.completed", {"tipo": "prima", "id_poliza": POLIZA, "amount": "2000000"})
        self.evento("payment.completed", {"tipo": "indemnizacion", "id_siniestro": siniestro, "amount": "1000000"})

        [fila] = self.client.get("/api/v1/analitica/tiempo-resolucion").data
        self.assertEqual(fila["resolved_count"], 1)

        [fila] = self.client.get("/api/v1/analitica/rentabilidad").data
        self.assertEqual(str(fila["loss_ratio"]), "0.5000")

    def test_fraude(self):
        # Póliza que empezó hace pocos días + monto muy alto respecto a la prima.
        hoy = timezone.localdate().isoformat()
        siniestro = self.abrir(policy_effective_date=hoy, estimated_amount="50000000.00")
        resp = self.client.get("/api/v1/analitica/fraude")
        self.assertEqual(resp.data["siniestros_marcados"], 1)
        self.assertEqual(str(resp.data["alertas"][0]["id_siniestro"]), siniestro)
