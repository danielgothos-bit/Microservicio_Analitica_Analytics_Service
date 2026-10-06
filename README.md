# Microservicio de Analítica y Riesgo — Analytics Service

Microservicio de InsureFlow definido en la sección 4.8 del documento de arquitectura.

## Responsabilidad

Calcular KPIs de siniestralidad, tiempo medio de resolución, fraude y rentabilidad técnica por producto.

## Tecnología

Python · Django REST Framework · PostgreSQL (`analytics_db`) · Celery + Redis · Docker

## Modelo de datos (3FN, IDs UUID)

Esquema estrella desnormalizado: `claims_by_type`, `avg_resolution_time`, `fraud_flags`, `loss_ratio_by_product` + dimensiones `dim_poliza` y `dim_siniestro`.

## Endpoints

```
GET /api/v1/analitica/siniestralidad — KPIs de siniestralidad por línea de negocio
GET /api/v1/analitica/tiempo-resolucion — tiempo medio de resolución
GET /api/v1/analitica/fraude — indicadores de fraude
GET /api/v1/analitica/rentabilidad — loss ratio por producto
(filtros opcionales: ?product_type=auto&desde=2026-01-01)
GET  /health — estado del servicio y de su base de datos
POST /api/v1/eventos — endpoint interno donde otros microservicios entregan eventos
```

## Eventos

Publica:
- (ninguno)

Consume:
- policy.issued
- claim.opened
- claim.approved
- claim.rejected
- payment.completed

Los eventos se encolan con Celery/Redis y se entregan por HTTP al endpoint `/api/v1/eventos` de cada
suscriptor, con reintentos y backoff exponencial (módulo `comun/eventos.py`). Cada evento se procesa una
sola vez (idempotencia por `event_id`).

## Variables de entorno

- `DATABASE_URL`, `REDIS_URL`: base de datos y Redis propios
- `INTERNAL_TOKEN`: token compartido por todos los microservicios para los eventos
- `RUN_WORKER_IN_WEB=1`: corre el worker de Celery dentro del mismo contenedor (Render gratis)
- `SYNC_TIMEOUT`: timeout de las llamadas REST síncronas (3 s por defecto)
- (ninguna)

Si una URL no está configurada, el servicio funciona en modo aislado (omite esa validación o ese evento).

## Ejecución local

```bash
docker compose up --build
```

El servicio queda en http://localhost:8007 y las migraciones se aplican solas al arrancar.

Pruebas:

```bash
docker compose exec analytics_service python manage.py test analitica
```

## Despliegue en Render

En Render: **New → Blueprint** → conectar este repositorio → **Deploy Blueprint**.
El `render.yaml` crea el servicio web, su PostgreSQL y su Redis (plan gratis).
