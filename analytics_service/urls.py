from django.urls import include, path

from comun.metricas import metricas
from comun.views import health, recibir_evento

urlpatterns = [
    path("health", health),
    path("metrics", metricas),
    path("api/v1/eventos", recibir_evento),
    path("", include("analitica.urls")),
]
