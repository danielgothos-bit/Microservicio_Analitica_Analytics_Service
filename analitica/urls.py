from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/analitica/siniestralidad", views.siniestralidad),
    path("api/v1/analitica/tiempo-resolucion", views.tiempo_resolucion),
    path("api/v1/analitica/fraude", views.fraude),
    path("api/v1/analitica/rentabilidad", views.rentabilidad),
]
