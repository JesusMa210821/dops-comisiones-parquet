"""Validación estática de las plantillas ARM (se ejecuta en el CI antes de desplegar)."""
import json

import pytest

from app.config import RAIZ

ARM = RAIZ / "infra" / "arm"


def cargar(nombre):
    return json.loads((ARM / nombre).read_text(encoding="utf-8"))


def test_plantilla_principal_valida():
    t = cargar("azuredeploy.json")
    assert t["$schema"].endswith("deploymentTemplate.json#")
    tipos = {r["type"] for r in t["resources"]}
    assert "Microsoft.Storage/storageAccounts" in tipos
    assert "Microsoft.Storage/storageAccounts/blobServices/containers" in tipos
    cuenta = next(r for r in t["resources"] if r["type"] == "Microsoft.Storage/storageAccounts")
    assert cuenta["properties"]["isHnsEnabled"] is True, "Debe ser ADLS Gen2 (Data Lake)"


@pytest.mark.parametrize("entorno", ["dev", "qa", "prd"])
def test_parametros_por_entorno(entorno):
    t = cargar("azuredeploy.json")
    p = cargar(f"azuredeploy.parameters.{entorno}.json")
    assert set(p["parameters"]) <= set(t["parameters"]), "Parámetro no declarado en la plantilla"
    assert p["parameters"]["entorno"]["value"] == entorno
    assert p["parameters"]["entorno"]["value"] in t["parameters"]["entorno"]["allowedValues"]
