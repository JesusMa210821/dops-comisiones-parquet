"""Pruebas unitarias de las reglas de negocio y calidad."""
import pandas as pd
import pytest

from app.extract import leer_csv_comisiones
from app.transform import ErrorCalidad, aplicar_reglas_calidad, calcular_salario_total

REGLAS = {"min_filas_salida": 1, "min_ratio_cruce": 0.5}


def empleados(**over):
    base = {
        "empleado_id": [1, 2, 3],
        "nom_empleado": ["Juan", "María", "Carlos"],
        "ape_empleado": ["Pérez", "Gómez", "Martínez"],
        "mnt_salario": [5000.0, 4000.0, 3000.0],
        "mnt_tope_comision": [10000.0, 8000.0, 9000.0],
    }
    base.update(over)
    return pd.DataFrame(base)


def comisiones(ids=(1, 2, 3), valores=(9000, 8250, 10500)):
    return pd.DataFrame({"empleado_id": list(ids), "nombre_apellido_csv": ["x"] * len(ids), "comision": list(valores)})


def test_salario_total_es_salario_mas_comision():
    df, _ = calcular_salario_total(empleados(), comisiones(), "202610", "dev")
    assert df.set_index("empleado_id")["salario_total"].to_dict() == {1: 14000.0, 2: 12250.0, 3: 13500.0}


def test_join_interno_y_reporte_de_huerfanos():
    df, rep = calcular_salario_total(empleados(), comisiones(ids=(1, 2, 99), valores=(1, 2, 3)), "202610", "dev")
    assert list(df["empleado_id"]) == [1, 2]
    assert rep["ids_csv_sin_empleado"] == [99]
    assert rep["ids_empleado_sin_comision"] == [3]
    assert rep["ratio_cruce_csv"] == pytest.approx(2 / 3, abs=1e-4)


def test_tope_de_comision_opcional():
    df_sin, rep = calcular_salario_total(empleados(), comisiones(), "202610", "dev", aplicar_tope=False)
    df_con, _ = calcular_salario_total(empleados(), comisiones(), "202610", "dev", aplicar_tope=True)
    assert rep["empleados_exceden_tope"] == 2  # 8250 > 8000 y 10500 > 9000
    assert df_sin.loc[df_sin.empleado_id == 3, "salario_total"].item() == 13500.0
    assert df_con.loc[df_con.empleado_id == 3, "salario_total"].item() == 12000.0


@pytest.mark.parametrize("ids,valores,mensaje", [
    ((1, 1), (100, 200), "duplicados"),
    ((1, 2), (100, -5), "negativas"),
    ((1, 2), (100, None), "vacías"),
])
def test_comisiones_invalidas_detienen_el_pipeline(ids, valores, mensaje):
    with pytest.raises(ErrorCalidad, match=mensaje):
        calcular_salario_total(empleados(), comisiones(ids, valores), "202610", "dev")


def test_columna_faltante_en_bd():
    with pytest.raises(ErrorCalidad, match="faltan columnas"):
        calcular_salario_total(empleados().drop(columns="mnt_salario"), comisiones(), "202610", "dev")


def test_quality_gate_rechaza_bajo_cruce():
    df, rep = calcular_salario_total(empleados(), comisiones(ids=(1, 98, 99), valores=(1, 2, 3)), "202610", "prd")
    with pytest.raises(ErrorCalidad, match="ratio_cruce_csv"):
        aplicar_reglas_calidad(df, rep, {"min_ratio_cruce": 0.95})
    assert rep["quality_gate"] == "RECHAZADO"


def test_quality_gate_aprueba():
    df, rep = calcular_salario_total(empleados(), comisiones(), "202610", "qa")
    assert aplicar_reglas_calidad(df, rep, REGLAS)["quality_gate"] == "APROBADO"


def test_lectura_csv_con_bom_y_punto_y_coma():
    contenido = "﻿empleado_id;Nombre y Apellido;Comisión\r\n1;Juan, Pérez;9000\r\n".encode("utf-8")
    df = leer_csv_comisiones(contenido)
    assert list(df.columns) == ["empleado_id", "nombre_apellido_csv", "comision"]
    assert df.loc[0, "nombre_apellido_csv"] == "Juan, Pérez"
