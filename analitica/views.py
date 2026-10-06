from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AvgResolutionTime, ClaimsByType, FraudFlag, LossRatioByProduct


def filtrar(request, qs):
    """Filtros opcionales: ?product_type=auto&desde=2026-01-01"""
    if request.query_params.get("product_type"):
        qs = qs.filter(product_type=request.query_params["product_type"])
    if request.query_params.get("desde"):
        qs = qs.filter(period__gte=request.query_params["desde"])
    return qs.order_by("-period", "product_type")


@api_view(["GET"])
def siniestralidad(request):
    qs = filtrar(request, ClaimsByType.objects.all())
    totales = qs.aggregate(claim_count=Sum("claim_count"), total_amount=Sum("total_amount"))
    return Response({
        "totales": {k: v or 0 for k, v in totales.items()},
        "por_linea_y_periodo": list(qs.values("product_type", "period", "claim_count", "total_amount")),
    })


@api_view(["GET"])
def tiempo_resolucion(request):
    qs = filtrar(request, AvgResolutionTime.objects.all())
    return Response(list(qs.values("product_type", "period", "avg_days", "resolved_count")))


@api_view(["GET"])
def fraude(request):
    qs = FraudFlag.objects.order_by("-risk_score", "-flagged_at")
    return Response({
        "siniestros_marcados": qs.count(),
        "alertas": list(qs.values("id_siniestro", "risk_score", "flagged_at", "reason")),
    })


@api_view(["GET"])
def rentabilidad(request):
    qs = filtrar(request, LossRatioByProduct.objects.all())
    return Response(list(qs.values("product_type", "period", "premiums_earned", "claims_paid", "loss_ratio")))
