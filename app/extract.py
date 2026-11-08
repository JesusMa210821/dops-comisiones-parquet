"""Extracción: tabla dmc.rrhh.empleado (PostgreSQL) y CSV de comisiones (Blob Storage o local)."""
import io
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

QUERY_EMPLEADOS = """
SELECT e.empleado_id,
       e.tip_documento,
       e.num_documento,
       e.nom_empleado,
       e.ape_empleado,
       e.cod_cargo,
       c.des_cargo,
       e.cod_departamento,
       d.des_departamento,
       e.mnt_salario,
       e.mnt_tope_comision
FROM rrhh.empleado e
LEFT JOIN rrhh.cargo c        ON c.cod_cargo = e.cod_cargo
LEFT JOIN rrhh.departamento d ON d.cod_departamento = e.cod_departamento
"""


def extraer_empleados_postgres(pg: dict) -> pd.DataFrame:
    """Lee los empleados desde PostgreSQL con un usuario de solo lectura."""
    import psycopg2  # import diferido: el modo offline no lo necesita

    faltan = [k for k in ("host", "user", "password") if not pg.get(k)]
    if faltan:
        raise RuntimeError(f"Faltan variables de entorno de PostgreSQL: {faltan}")

    log.info("Conectando a PostgreSQL %s:%s/%s", pg["host"], pg["port"], pg["dbname"])
    with psycopg2.connect(connect_timeout=15, **pg) as conn, conn.cursor() as cur:
        cur.execute(QUERY_EMPLEADOS)
        columnas = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=columnas)

    for col in ("mnt_salario", "mnt_tope_comision"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    log.info("Empleados extraídos de BD: %d", len(df))
    return df


def extraer_empleados_mock(ruta: Path) -> pd.DataFrame:
    """Modo offline (CI): empleados sintéticos con el mismo esquema que la tabla."""
    df = pd.read_csv(ruta, sep=";", encoding="utf-8")
    log.info("Empleados extraídos de fixture offline: %d", len(df))
    return df


def leer_csv_comisiones(contenido: bytes) -> pd.DataFrame:
    """Normaliza el CSV de comisiones: separador ';', UTF-8 con o sin BOM."""
    df = pd.read_csv(io.BytesIO(contenido), sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Nombre y Apellido": "nombre_apellido_csv", "Comisión": "comision"})
    return df


def extraer_comisiones(fuente: dict, azure_conn_str: str, raiz: Path) -> pd.DataFrame:
    """Lee el CSV desde Azure Blob Storage (tipo=blob) o desde disco (tipo=local)."""
    archivo = fuente["archivo"]
    if fuente["tipo"] == "blob":
        from azure.storage.blob import BlobServiceClient

        if not azure_conn_str:
            raise RuntimeError("Falta AZURE_STORAGE_CONNECTION_STRING para leer desde Blob Storage")
        blob = f'{fuente["carpeta"].rstrip("/")}/{archivo}'
        log.info("Descargando blob %s/%s", fuente["contenedor"], blob)
        cliente = BlobServiceClient.from_connection_string(azure_conn_str)
        contenido = cliente.get_blob_client(fuente["contenedor"], blob).download_blob().readall()
    else:
        ruta = raiz / fuente["carpeta_local"] / archivo
        log.info("Leyendo CSV local %s", ruta)
        contenido = ruta.read_bytes()

    df = leer_csv_comisiones(contenido)
    log.info("Filas de comisiones leídas: %d", len(df))
    return df
