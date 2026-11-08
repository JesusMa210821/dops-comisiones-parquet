"""Carga de configuración por entorno (dev / qa / prd).

Los valores no sensibles viven en config/<entorno>.json.
Las credenciales se leen SIEMPRE de variables de entorno (inyectadas por
Jenkins Credentials o por un archivo .env local que no se versiona).
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENTORNOS_VALIDOS = ("dev", "qa", "prd")


@dataclass
class Config:
    entorno: str
    periodo: str
    fuente_comisiones: dict
    salida: dict
    calidad: dict
    aplicar_tope_comision: bool = False
    postgres: dict = field(default_factory=dict)
    azure_conn_str: str = ""


def cargar_config(entorno: str) -> Config:
    if entorno not in ENTORNOS_VALIDOS:
        raise ValueError(f"Entorno '{entorno}' no válido. Usa uno de {ENTORNOS_VALIDOS}")

    ruta = RAIZ / "config" / f"{entorno}.json"
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    # El periodo se puede sobreescribir desde Jenkins sin tocar el JSON
    periodo = os.getenv("PERIODO", datos["periodo"])
    datos["fuente_comisiones"]["archivo"] = datos["fuente_comisiones"]["archivo"].format(periodo=periodo)

    return Config(
        entorno=entorno,
        periodo=periodo,
        fuente_comisiones=datos["fuente_comisiones"],
        salida=datos["salida"],
        calidad=datos["calidad"],
        aplicar_tope_comision=datos.get("aplicar_tope_comision", False),
        postgres={
            "host": os.getenv("PG_HOST", ""),
            "port": int(os.getenv("PG_PORT", "5432")),
            "dbname": os.getenv("PG_DB", "dmc"),
            "user": os.getenv("PG_USER", ""),
            "password": os.getenv("PG_PASSWORD", ""),
        },
        azure_conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
    )
