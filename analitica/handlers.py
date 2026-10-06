"""
Eventos que consume el microservicio de Analítica (sección 4.8): actualizan los KPIs
de forma incremental (ETL orientado a eventos).
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import (
    AvgResolutionTime,
    ClaimsByType,
    DimPoliza,
    DimSiniestro,
    FraudFlag,
    LossRatioByProduct,
)

DESCONOCIDO = "desconocido"


def _periodo(valor):
    if isinstance(valor, str):
        valor = parse_datetime(valor) or parse_date(valor)
    valor = valor or timezone.now()
    if isinstance(valor, datetime):
        valor = timezone.localtime(valor) if timezone.is_aware(valor) else valor
        valor = valor.date()
    return date(valor.year, valor.month, 1)


def _decimal(valor):
    return Decimal(str(valor or 0))


def _fecha_hora(valor):
    return parse_datetime(valor) if isinstance(valor, str) else valor


def on_policy(data):
    DimPoliza.objects.update_or_create(
        id_poliza=data["id_poliza"],
        defaults={"product_type": data.get("product_type") or DESCONOCIDO, "id_asegurado": data.get("id_asegurado")},
    )


def evaluar_fraude(data, siniestro):
    """Reglas simples de riesgo de fraude. Si el puntaje es >= 0.5 se marca el siniestro."""
    puntaje, razones = Decimal("0"), []
    incidente = _fecha_hora(data.get("incident_date"))
    inicio_poliza = parse_date(str(data.get("policy_effective_date") or ""))

    if incidente and inicio_poliza and (incidente.date() - inicio_poliza).days <= 30:
        puntaje += Decimal("0.4")
        razones.append("Siniestro dentro de los primeros 30 días de vigencia de la póliza.")

    prima = _decimal(data.get("premium"))
    if prima > 0 and siniestro.estimated_amount > prima * 10:
        puntaje += Decimal("0.3")
        razones.append("Monto estimado mayor a 10 veces la prima.")

    if incidente and (siniestro.reported_at - incidente) > timedelta(days=30):
        puntaje += Decimal("0.2")
        razones.append("Reportado más de 30 días después del incidente.")

    recientes = DimSiniestro.objects.filter(
        id_asegurado=siniestro.id_asegurado, reported_at__gte=siniestro.reported_at - timedelta(days=90)
    ).count()
    if siniestro.id_asegurado and recientes >= 3:
        puntaje += Decimal("0.3")
        razones.append(f"El asegurado tiene {recientes} siniestros en los últimos 90 días.")

    if puntaje >= Decimal("0.5"):
        FraudFlag.objects.update_or_create(
            id_siniestro=siniestro.id_siniestro,
            defaults={"risk_score": min(puntaje, Decimal("1")), "reason": " ".join(razones)},
        )


def on_claim_opened(data):
    siniestro, creado = DimSiniestro.objects.get_or_create(
        id_siniestro=data["id_siniestro"],
        defaults={
            "id_poliza": data.get("id_poliza"),
            "id_asegurado": data.get("id_asegurado"),
            "product_type": data.get("product_type") or DESCONOCIDO,
            "reported_at": _fecha_hora(data.get("reported_at")) or timezone.now(),
            "estimated_amount": _decimal(data.get("estimated_amount")),
        },
    )
    if not creado:
        return

    fila, _ = ClaimsByType.objects.get_or_create(product_type=siniestro.product_type, period=_periodo(siniestro.reported_at))
    fila.claim_count += 1
    fila.total_amount += siniestro.estimated_amount
    fila.save()

    evaluar_fraude(data, siniestro)


def on_claim_resolved(data):
    """claim.approved / claim.rejected: tiempo de resolución desde el reporte."""
    siniestro = DimSiniestro.objects.filter(id_siniestro=data.get("id_siniestro")).first()
    if siniestro is None or siniestro.resuelto:
        return

    dias = Decimal((timezone.now() - siniestro.reported_at).total_seconds() / 86400).quantize(Decimal("0.01"))
    fila, _ = AvgResolutionTime.objects.get_or_create(product_type=siniestro.product_type, period=_periodo(timezone.now()))
    fila.avg_days = (fila.avg_days * fila.resolved_count + dias) / (fila.resolved_count + 1)
    fila.resolved_count += 1
    fila.save()

    siniestro.resuelto = True
    siniestro.save(update_fields=["resuelto"])


def on_payment_completed(data):
    """Primas cobradas e indemnizaciones pagadas por línea de negocio -> loss ratio."""
    monto = _decimal(data.get("amount"))
    if data.get("tipo") == "prima":
        dim = DimPoliza.objects.filter(id_poliza=data.get("id_poliza")).first()
        campo = "premiums_earned"
    else:
        dim = DimSiniestro.objects.filter(id_siniestro=data.get("id_siniestro")).first()
        campo = "claims_paid"

    fila, _ = LossRatioByProduct.objects.get_or_create(
        product_type=dim.product_type if dim else DESCONOCIDO, period=_periodo(data.get("paid_at"))
    )
    setattr(fila, campo, getattr(fila, campo) + monto)
    fila.loss_ratio = (fila.claims_paid / fila.premiums_earned).quantize(Decimal("0.0001")) if fila.premiums_earned else None
    fila.save()


HANDLERS = {
    "policy.issued": on_policy,
    "policy.renewed": on_policy,
    "policy.cancelled": on_policy,
    "claim.opened": on_claim_opened,
    "claim.approved": on_claim_resolved,
    "claim.rejected": on_claim_resolved,
    "payment.completed": on_payment_completed,
}
