"""Carga: escribe la tabla consolidada en Parquet (local y/o Data Lake ADLS Gen2)."""
import io
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def nombre_parquet(periodo: str) -> str:
    return f"salario_total_empleados_{periodo}.parquet"


def a_parquet_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", index=False, compression="snappy")
    return buffer.getvalue()


def guardar(df: pd.DataFrame, reporte: dict, salida: dict, entorno: str, periodo: str,
            azure_conn_str: str, raiz: Path) -> dict:
    """Siempre deja una copia local (artefacto de Jenkins); si tipo=adls, la sube al Data Lake."""
    datos = a_parquet_bytes(df)
    archivo = nombre_parquet(periodo)

    carpeta_local = raiz / "output" / entorno / f"periodo={periodo}"
    carpeta_local.mkdir(parents=True, exist_ok=True)
    (carpeta_local / archivo).write_bytes(datos)
    rutas = {"local": str(carpeta_local / archivo)}
    log.info("Parquet local: %s (%d filas, %d bytes)", rutas["local"], len(df), len(datos))

    if salida["tipo"] == "adls":
        from azure.storage.blob import BlobServiceClient, ContentSettings

        if not azure_conn_str:
            raise RuntimeError("Falta AZURE_STORAGE_CONNECTION_STRING para escribir en el Data Lake")
        destino = f'{salida["carpeta"].rstrip("/")}/periodo={periodo}/{archivo}'
        cliente = BlobServiceClient.from_connection_string(azure_conn_str)
        cliente.get_blob_client(salida["contenedor"], destino).upload_blob(
            datos, overwrite=True,
            content_settings=ContentSettings(content_type="application/vnd.apache.parquet"),
        )
        rutas["adls"] = f'{salida["contenedor"]}/{destino}'
        log.info("Parquet en Data Lake: %s", rutas["adls"])

    reporte["rutas_salida"] = rutas
    (carpeta_local / "reporte_calidad.json").write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return rutas
