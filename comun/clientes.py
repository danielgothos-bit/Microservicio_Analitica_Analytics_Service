"""
Cliente REST síncrono entre microservicios (secciones 6.1, 6.5, 6.6 y 6.7 del documento).

- Timeout: SYNC_TIMEOUT segundos (3 por defecto; en Render se sube porque los
  servicios gratis tardan ~1 minuto en despertar).
- Retries: hasta 3 intentos con backoff exponencial (0.5s, 1s, 2s).
- Circuit breaker: tras 3 fallos seguidos el circuito se abre 30 segundos y las
  llamadas se rechazan de inmediato; luego pasa a half-open y deja una de prueba.
"""
import logging
import os
import threading
import time

import requests

logger = logging.getLogger("clientes")


class ServicioNoDisponible(Exception):
    pass


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"

    def __init__(self, umbral=3, espera=30):
        self.umbral = umbral
        self.espera = espera
        self.fallos = 0
        self.estado = self.CLOSED
        self.abierto_en = 0
        self._lock = threading.Lock()

    def permitir(self):
        with self._lock:
            if self.estado == self.OPEN and time.monotonic() - self.abierto_en >= self.espera:
                self.estado = self.HALF_OPEN
            return self.estado != self.OPEN

    def exito(self):
        with self._lock:
            self.fallos = 0
            self.estado = self.CLOSED

    def fallo(self):
        with self._lock:
            self.fallos += 1
            if self.estado == self.HALF_OPEN or self.fallos >= self.umbral:
                self.estado = self.OPEN
                self.abierto_en = time.monotonic()


_circuitos = {}


def _circuito(servicio):
    return _circuitos.setdefault(servicio, CircuitBreaker())


def get_json(servicio, path, params=None):
    """
    GET a otro microservicio. `servicio` es el prefijo de su variable de entorno,
    por ejemplo "POLICY" usa POLICY_SERVICE_URL.
    Retorna el JSON, o None si el recurso no existe (404).
    """
    base = os.getenv(f"{servicio}_SERVICE_URL")
    if not base:
        raise ServicioNoDisponible(f"{servicio}_SERVICE_URL no está configurada.")

    circuito = _circuito(servicio)
    if not circuito.permitir():
        raise ServicioNoDisponible(f"Circuito abierto hacia {servicio}.")

    url = f"{base.rstrip('/')}{path}"
    timeout = float(os.getenv("SYNC_TIMEOUT", "3"))
    ultimo_error = None

    for intento in range(3):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 404:
                circuito.exito()
                return None
            if resp.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            circuito.exito()
            return resp.json()
        except requests.RequestException as exc:
            ultimo_error = exc
            logger.warning("fallo llamando a servicio", extra={"servicio": servicio, "url": url, "intento": intento + 1, "error": str(exc)})
            if intento < 2:
                time.sleep(0.5 * 2 ** intento)

    circuito.fallo()
    raise ServicioNoDisponible(f"{servicio} no respondió: {ultimo_error}")
