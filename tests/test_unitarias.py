"""Pruebas unitarias: una unidad de lógica de negocio aislada; las dependencias externas se simulan con mocks."""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from analitica.handlers import _periodo, evaluar_fraude
from analitica.models import FraudFlag


class AnaliticaUnitTests(SimpleTestCase):
    def test_periodo_agrupa_por_mes(self):
        self.assertEqual(_periodo("2026-11-17T15:30:00Z"), date(2026, 11, 1))


class FraudeUnitTests(TestCase):
    def test_marca_fraude_por_reglas_de_riesgo(self):
        siniestro = mock.Mock(id_siniestro=uuid.uuid4(), id_asegurado=None, estimated_amount=Decimal("50000000"),
                              reported_at=timezone.now())
        datos = {"incident_date": (timezone.now() - timedelta(days=2)).isoformat(),
                 "policy_effective_date": (date.today() - timedelta(days=10)).isoformat(), "premium": "1000000"}
        evaluar_fraude(datos, siniestro)  # póliza nueva (+0.4) y monto > 10 veces la prima (+0.3)
        flag = FraudFlag.objects.get(id_siniestro=siniestro.id_siniestro)
        self.assertEqual(flag.risk_score, Decimal("0.70"))
