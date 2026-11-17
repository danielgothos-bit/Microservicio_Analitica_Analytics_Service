from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import include, path

from comun.metricas import metricas
from comun.views import health, recibir_evento

urlpatterns = [
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("health", health),
    path("metrics", metricas),
    path("api/v1/eventos", recibir_evento),
    path("", include("analitica.urls")),
]
