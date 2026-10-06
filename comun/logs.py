"""Logs estructurados en JSON (sección 11.1 del documento)."""
import json
import logging
from datetime import datetime, timezone

from .servicio import SERVICE_NAME

_CAMPOS_ESTANDAR = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for clave, valor in vars(record).items():
            if clave not in _CAMPOS_ESTANDAR:
                data[clave] = valor
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str, ensure_ascii=False)
