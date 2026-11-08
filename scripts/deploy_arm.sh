#!/usr/bin/env bash
# Despliega el Data Lake de un entorno con la plantilla ARM.
# Uso: ./scripts/deploy_arm.sh <dev|qa|prd> <resource-group> [location]
set -euo pipefail
ENTORNO=${1:?Indica el entorno: dev | qa | prd}
RG=${2:?Indica el resource group}
LOCATION=${3:-eastus2}

az group create --name "$RG" --location "$LOCATION" --tags proyecto=dataops-comisiones entorno="$ENTORNO" -o none

az deployment group validate -g "$RG" \
  --template-file infra/arm/azuredeploy.json \
  --parameters @infra/arm/azuredeploy.parameters.$ENTORNO.json -o none
echo ">> Plantilla ARM validada para $ENTORNO"

az deployment group create -g "$RG" --name "dops-comisiones-$ENTORNO-$(date +%Y%m%d%H%M%S)" \
  --template-file infra/arm/azuredeploy.json \
  --parameters @infra/arm/azuredeploy.parameters.$ENTORNO.json \
  --query "properties.outputs" -o json
