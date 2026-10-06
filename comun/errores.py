"""Respuestas de error JSON con formato consistente: code + message (sección 6.4)."""
from rest_framework.views import exception_handler

CODIGOS = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
}


def manejar_error(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detalle = response.data
    if isinstance(detalle, dict) and set(detalle) == {"detail"}:
        mensaje, detalle = str(detalle["detail"]), None
    else:
        mensaje = "Datos inválidos." if response.status_code == 400 else "Error en la solicitud."

    response.data = {"code": CODIGOS.get(response.status_code, "ERROR"), "message": mensaje}
    if detalle:
        response.data["details"] = detalle
    return response
