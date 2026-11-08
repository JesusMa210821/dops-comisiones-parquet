#!/usr/bin/env bash
# Sube el CSV de comisiones al contenedor raw del entorno.
# Uso: ./scripts/upload_comisiones.sh <storage-account> [periodo]
set -euo pipefail
CUENTA=${1:?Indica la storage account}
PERIODO=${2:-202610}
ARCHIVO="ComisionEmpleados_V1_${PERIODO}.csv"

az storage blob upload --auth-mode key --account-name "$CUENTA" \
  --container-name raw --name "comisiones/$ARCHIVO" \
  --file "data/input/$ARCHIVO" --overwrite
echo ">> Subido raw/comisiones/$ARCHIVO a $CUENTA"
