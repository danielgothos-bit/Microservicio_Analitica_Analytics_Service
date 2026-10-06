from django.urls import include, path

from comun.views import health, recibir_evento

urlpatterns = [
    path("health", health),
    path("api/v1/eventos", recibir_evento),
    path("", include("analitica.urls")),
]
