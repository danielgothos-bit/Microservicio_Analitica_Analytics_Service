"""
Espera a que PostgreSQL esté disponible y, si se define DB_NAME,
crea esa base dentro del servidor de DATABASE_URL cuando todavía no existe.
"""
import os
import re
import time

import dj_database_url
import psycopg2

name = os.getenv("DB_NAME")
url = os.getenv("DATABASE_URL")

if url:
    cfg = dj_database_url.parse(url)

    for intento in range(30):
        try:
            conn = psycopg2.connect(
                dbname=cfg["NAME"],
                user=cfg["USER"],
                password=cfg["PASSWORD"],
                host=cfg["HOST"],
                port=cfg["PORT"] or 5432,
            )
            break
        except psycopg2.OperationalError:
            print("Esperando a PostgreSQL...")
            time.sleep(2)
    else:
        raise SystemExit("No fue posible conectarse a PostgreSQL.")

    if name:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
            raise SystemExit(f"DB_NAME inválido: {name}")

        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{name}"')
                print(f"Base de datos {name} creada.")

    conn.close()
