"""Transformación: validación, join por empleado_id y cálculo de salario_total."""
import logging
from datetime import datetime, timezone

import pandas as pd

log = logging.getLogger(__name__)

COLUMNAS_EMPLEADO = {"empleado_id", "nom_empleado", "ape_empleado", "mnt_salario", "mnt_tope_comision"}
COLUMNAS_COMISION = {"empleado_id", "comision"}


class ErrorCalidad(Exception):
    """Se lanza cuando los datos no superan las reglas de calidad (detiene el pipeline)."""


def validar_entrada(df: pd.DataFrame, requeridas: set, nombre: str) -> pd.DataFrame:
    faltan = requeridas - set(df.columns)
    if faltan:
        raise ErrorCalidad(f"[{nombre}] faltan columnas: {sorted(faltan)}")

    df = df.copy()
    df["empleado_id"] = pd.to_numeric(df["empleado_id"], errors="coerce")
    if df["empleado_id"].isna().any():
        raise ErrorCalidad(f"[{nombre}] hay empleado_id vacíos o no numéricos")
    df["empleado_id"] = df["empleado_id"].astype("int64")

    duplicados = df.loc[df["empleado_id"].duplicated(), "empleado_id"].tolist()
    if duplicados:
        raise ErrorCalidad(f"[{nombre}] empleado_id duplicados: {duplicados}")
    return df


def validar_comisiones(df: pd.DataFrame) -> pd.DataFrame:
    df = validar_entrada(df, COLUMNAS_COMISION, "comisiones")
    df["comision"] = pd.to_numeric(df["comision"], errors="coerce")
    if df["comision"].isna().any():
        raise ErrorCalidad("[comisiones] hay comisiones vacías o no numéricas")
    if (df["comision"] < 0).any():
        raise ErrorCalidad("[comisiones] hay comisiones negativas")
    return df


def calcular_salario_total(
    empleados: pd.DataFrame,
    comisiones: pd.DataFrame,
    periodo: str,
    entorno: str,
    aplicar_tope: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Join interno por empleado_id y salario_total = salario + comisión.

    Devuelve la tabla consolidada y un reporte de calidad con los registros
    que no cruzaron, para que queden trazados en los logs y en el artefacto.
    """
    empleados = validar_entrada(empleados, COLUMNAS_EMPLEADO, "empleados")
    comisiones = validar_comisiones(comisiones)

    df = empleados.merge(comisiones, on="empleado_id", how="inner", validate="one_to_one")

    df["excede_tope_comision"] = df["comision"] > df["mnt_tope_comision"]
    if aplicar_tope:
        df["comision_aplicada"] = df[["comision", "mnt_tope_comision"]].min(axis=1)
    else:
        df["comision_aplicada"] = df["comision"]

    df["salario_total"] = (df["mnt_salario"] + df["comision_aplicada"]).round(2)
    df["periodo"] = periodo
    df["entorno"] = entorno
    df["fecha_proceso"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    columnas = [
        "periodo", "empleado_id", "tip_documento", "num_documento", "nom_empleado", "ape_empleado",
        "cod_cargo", "des_cargo", "cod_departamento", "des_departamento",
        "mnt_salario", "comision", "mnt_tope_comision", "excede_tope_comision",
        "comision_aplicada", "salario_total", "entorno", "fecha_proceso",
    ]
    df = df[[c for c in columnas if c in df.columns]].sort_values("empleado_id").reset_index(drop=True)

    ids_bd = set(empleados["empleado_id"])
    ids_csv = set(comisiones["empleado_id"])
    reporte = {
        "periodo": periodo,
        "entorno": entorno,
        "filas_empleados_bd": len(empleados),
        "filas_comisiones_csv": len(comisiones),
        "filas_salida": len(df),
        "ratio_cruce_csv": round(len(df) / len(comisiones), 4) if len(comisiones) else 0.0,
        "ids_csv_sin_empleado": sorted(int(i) for i in ids_csv - ids_bd),
        "ids_empleado_sin_comision": sorted(int(i) for i in ids_bd - ids_csv),
        "empleados_exceden_tope": int(df["excede_tope_comision"].sum()),
        "aplicar_tope_comision": aplicar_tope,
        "suma_salario_total": float(df["salario_total"].sum()),
    }
    log.info("Cruce: %d de %d filas del CSV (%.1f%%)", len(df), len(comisiones), reporte["ratio_cruce_csv"] * 100)
    if reporte["ids_csv_sin_empleado"]:
        log.warning("IDs del CSV sin empleado en BD: %s", reporte["ids_csv_sin_empleado"])
    return df, reporte


def aplicar_reglas_calidad(df: pd.DataFrame, reporte: dict, reglas: dict) -> dict:
    """Quality gate: decide si el entorno puede promocionarse al siguiente."""
    fallos = []
    if reporte["filas_salida"] < reglas.get("min_filas_salida", 1):
        fallos.append(f"filas_salida={reporte['filas_salida']} < {reglas.get('min_filas_salida', 1)}")
    if reporte["ratio_cruce_csv"] < reglas.get("min_ratio_cruce", 0.0):
        fallos.append(f"ratio_cruce_csv={reporte['ratio_cruce_csv']} < {reglas['min_ratio_cruce']}")
    if df["salario_total"].isna().any():
        fallos.append("salario_total con nulos")
    if (df["salario_total"] < df["mnt_salario"]).any():
        fallos.append("salario_total menor que el salario base")

    reporte["quality_gate"] = "APROBADO" if not fallos else "RECHAZADO"
    reporte["quality_gate_fallos"] = fallos
    if fallos:
        raise ErrorCalidad("Quality gate rechazado: " + "; ".join(fallos))
    log.info("Quality gate APROBADO")
    return reporte
