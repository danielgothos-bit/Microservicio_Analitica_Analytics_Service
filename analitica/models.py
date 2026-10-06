"""
Esquema de reporte (OLAP) desnormalizado tipo estrella (sección 5.8).

Tablas de hechos/métricas: claims_by_type, avg_resolution_time, fraud_flags, loss_ratio_by_product.
Dimensiones: dim_poliza y dim_siniestro (para ubicar la línea de negocio de cada pago).
Se alimentan por eventos (consistencia eventual), sin llaves foráneas estrictas.
"""
from django.db import models


class ClaimsByType(models.Model):
    product_type = models.CharField(max_length=20)
    period = models.DateField()  # primer día del mes
    claim_count = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        db_table = "claims_by_type"
        constraints = [models.UniqueConstraint(fields=["product_type", "period"], name="uq_claims_by_type")]


class AvgResolutionTime(models.Model):
    product_type = models.CharField(max_length=20)
    period = models.DateField()
    avg_days = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    resolved_count = models.IntegerField(default=0)  # para recalcular el promedio de forma incremental

    class Meta:
        db_table = "avg_resolution_time"
        constraints = [models.UniqueConstraint(fields=["product_type", "period"], name="uq_avg_resolution_time")]


class FraudFlag(models.Model):
    id_siniestro = models.UUIDField(unique=True)  # FK-ext -> Claims Service
    risk_score = models.DecimalField(max_digits=4, decimal_places=2)
    flagged_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()

    class Meta:
        db_table = "fraud_flags"


class LossRatioByProduct(models.Model):
    product_type = models.CharField(max_length=20)
    period = models.DateField()
    premiums_earned = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    claims_paid = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    loss_ratio = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True)

    class Meta:
        db_table = "loss_ratio_by_product"
        constraints = [models.UniqueConstraint(fields=["product_type", "period"], name="uq_loss_ratio_by_product")]


class DimPoliza(models.Model):
    id_poliza = models.UUIDField(primary_key=True)
    id_asegurado = models.UUIDField(blank=True, null=True)
    product_type = models.CharField(max_length=20)

    class Meta:
        db_table = "dim_poliza"


class DimSiniestro(models.Model):
    id_siniestro = models.UUIDField(primary_key=True)
    id_poliza = models.UUIDField(blank=True, null=True)
    id_asegurado = models.UUIDField(blank=True, null=True)
    product_type = models.CharField(max_length=20)
    reported_at = models.DateTimeField()
    estimated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    resuelto = models.BooleanField(default=False)

    class Meta:
        db_table = "dim_siniestro"
        indexes = [models.Index(fields=["id_asegurado"], name="idx_dim_siniestro_asegurado")]
