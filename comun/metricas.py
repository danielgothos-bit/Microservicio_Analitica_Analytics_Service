"""
Métricas para Prometheus (sección 11.2 del documento).

- insureflow_http_requests_total{service, method, route, status}: solicitudes atendidas
- insureflow_http_request_duration_seconds{service, route}: latencia por ruta
- insureflow_sync_call_duration_seconds{service, target}: latencia de llamadas REST entre servicios
- insureflow_events_published_total{service, event} / insureflow_events_received_total{service, event, result}

Se exponen en GET /metrics (formato de texto de Prometheus).
"""
import time

from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .servicio import SERVICE_NAME

HTTP_REQUESTS = Counter("insureflow_http_requests_total", "Solicitudes HTTP atendidas",
                        ["service", "method", "route", "status"])
HTTP_LATENCY = Histogram("insureflow_http_request_duration_seconds", "Latencia de las solicitudes HTTP",
                         ["service", "route"], buckets=(.01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60))
SYNC_LATENCY = Histogram("insureflow_sync_call_duration_seconds", "Latencia de llamadas REST síncronas a otros servicios",
                         ["service", "target"], buckets=(.05, .1, .25, .5, 1, 2, 3, 5, 10, 30, 60))
EVENTS_PUBLISHED = Counter("insureflow_events_published_total", "Eventos publicados", ["service", "event"])
EVENTS_RECEIVED = Counter("insureflow_events_received_total", "Eventos recibidos", ["service", "event", "result"])


class MetricasMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        inicio = time.monotonic()
        response = self.get_response(request)
        match = getattr(request, "resolver_match", None)
        ruta = "/" + match.route if match and match.route else "otra"
        if ruta != "/metrics":
            HTTP_REQUESTS.labels(SERVICE_NAME, request.method, ruta, str(response.status_code)).inc()
            HTTP_LATENCY.labels(SERVICE_NAME, ruta).observe(time.monotonic() - inicio)
        return response


def metricas(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
