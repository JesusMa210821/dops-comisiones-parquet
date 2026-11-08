"""Punto de entrada del pipeline de comisiones.

Uso:
    python -m app.main --env dev              # PostgreSQL + Blob/ADLS según config/dev.json
    python -m app.main --env dev --offline    # sin red: fixture de empleados + CSV local (CI)
"""
import argparse
import logging
import sys

from app.config import RAIZ, cargar_config
from app.extract import extraer_comisiones, extraer_empleados_mock, extraer_empleados_postgres
from app.load import guardar
from app.transform import ErrorCalidad, aplicar_reglas_calidad, calcular_salario_total

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logging.getLogger("azure").setLevel(logging.WARNING)
log = logging.getLogger("pipeline")


def ejecutar(entorno: str, offline: bool = False) -> dict:
    cfg = cargar_config(entorno)
    log.info("=== Pipeline comisiones | entorno=%s | periodo=%s | offline=%s ===", entorno, cfg.periodo, offline)

    if offline:
        empleados = extraer_empleados_mock(RAIZ / "tests" / "fixtures" / "empleados_mock.csv")
        fuente = {**cfg.fuente_comisiones, "tipo": "local"}
        salida = {**cfg.salida, "tipo": "local"}
    else:
        empleados = extraer_empleados_postgres(cfg.postgres)
        fuente, salida = cfg.fuente_comisiones, cfg.salida

    comisiones = extraer_comisiones(fuente, cfg.azure_conn_str, RAIZ)
    df, reporte = calcular_salario_total(empleados, comisiones, cfg.periodo, entorno, cfg.aplicar_tope_comision)
    reporte = aplicar_reglas_calidad(df, reporte, cfg.calidad)
    guardar(df, reporte, salida, entorno, cfg.periodo, cfg.azure_conn_str, RAIZ)

    muestra = df[["empleado_id", "nom_empleado", "mnt_salario", "comision", "salario_total"]].head(5)
    log.info("Muestra de la salida:\n%s", muestra.to_string(index=False))
    log.info("=== Pipeline finalizado OK: %d filas | suma salario_total=%.2f ===",
             reporte["filas_salida"], reporte["suma_salario_total"])
    return reporte


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline DataOps de comisiones de empleados")
    parser.add_argument("--env", required=True, choices=["dev", "qa", "prd"])
    parser.add_argument("--offline", action="store_true", help="Ejecuta sin PostgreSQL ni Azure (pruebas de CI)")
    args = parser.parse_args()
    try:
        ejecutar(args.env, args.offline)
        return 0
    except ErrorCalidad as e:
        log.error("Error de calidad de datos: %s", e)
        return 2
    except Exception:  # noqa: BLE001 - queremos el traceback completo en el log de Jenkins
        log.exception("Fallo en el pipeline")
        return 1


if __name__ == "__main__":
    sys.exit(main())
