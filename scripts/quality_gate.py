"""Lee el reporte de calidad de un entorno y falla si no está APROBADO.

Es la "aprobación automatizada" que usa Jenkins antes de promocionar al siguiente entorno.
Uso: python scripts/quality_gate.py <entorno> <periodo>
"""
import json
import sys
from pathlib import Path

entorno, periodo = sys.argv[1], sys.argv[2]
ruta = Path("output") / entorno / f"periodo={periodo}" / "reporte_calidad.json"
if not ruta.exists():
    sys.exit(f"[GATE] No existe {ruta}: el pipeline de {entorno} no generó salida")

rep = json.loads(ruta.read_text(encoding="utf-8"))
print(f"[GATE] {entorno.upper()} | filas={rep['filas_salida']} | cruce={rep['ratio_cruce_csv']:.0%} "
      f"| sin_comision={rep['ids_empleado_sin_comision']} | resultado={rep['quality_gate']}")
if rep["quality_gate"] != "APROBADO":
    sys.exit(f"[GATE] Rechazado: {rep['quality_gate_fallos']}")
print(f"[GATE] {entorno.upper()} aprobado automáticamente para promoción")
