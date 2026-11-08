"""Prueba de integración end-to-end sin red (CSV real del curso + fixture de empleados)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from app.config import RAIZ, cargar_config
from app.main import ejecutar


@pytest.mark.parametrize("entorno", ["dev", "qa", "prd"])
def test_config_por_entorno(entorno):
    cfg = cargar_config(entorno)
    assert cfg.fuente_comisiones["archivo"] == f"ComisionEmpleados_V1_{cfg.periodo}.csv"
    assert 0 < cfg.calidad["min_ratio_cruce"] <= 1


def test_periodo_sobrescribible(monkeypatch):
    monkeypatch.setenv("PERIODO", "202611")
    assert cargar_config("dev").fuente_comisiones["archivo"] == "ComisionEmpleados_V1_202611.csv"


def test_pipeline_offline_genera_parquet():
    rep = ejecutar("dev", offline=True)
    ruta = Path(rep["rutas_salida"]["local"])
    assert ruta.exists()

    df = pd.read_parquet(ruta)
    csv = pd.read_csv(RAIZ / "data/input/ComisionEmpleados_V1_202610.csv", sep=";")
    assert len(df) == len(csv) == 34
    assert (df["salario_total"] == df["mnt_salario"] + df["comision"]).all()
    assert rep["quality_gate"] == "APROBADO"

    reporte = json.loads((ruta.parent / "reporte_calidad.json").read_text(encoding="utf-8"))
    assert reporte["ids_empleado_sin_comision"] == [6, 7, 8]
