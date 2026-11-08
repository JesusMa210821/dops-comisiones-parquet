"""Prepara el emulador Azurite como si fuera el Data Lake de cada entorno.

- Crea los contenedores raw y curated en las cuentas dopsqa y dopsprd.
- Sube el CSV de comisiones a raw/comisiones/.
- Imprime las cadenas de conexión para Jenkins (host.docker.internal) y para tu PC (127.0.0.1).

Uso: python scripts/azurite_setup.py [periodo]
"""
import sys
from pathlib import Path

from azure.storage.blob import BlobServiceClient

CUENTAS = {
    "qa": ("dopsqa", "Q9s/FGrPEIqPCMcgfOXg4XzhJN8M6jAC41OvmvADqBA="),
    "prd": ("dopsprd", "Pn/BNZ1XIVzxwxUEZrcR1EvptQERfWawUKz6B1baQy0="),
}


def cadena(cuenta: str, clave: str, host: str) -> str:
    return (f"DefaultEndpointsProtocol=http;AccountName={cuenta};AccountKey={clave};"
            f"BlobEndpoint=http://{host}:10000/{cuenta};")


def main() -> None:
    periodo = sys.argv[1] if len(sys.argv) > 1 else "202610"
    archivo = f"ComisionEmpleados_V1_{periodo}.csv"
    csv = Path(__file__).resolve().parent.parent / "data" / "input" / archivo

    for entorno, (cuenta, clave) in CUENTAS.items():
        svc = BlobServiceClient.from_connection_string(cadena(cuenta, clave, "127.0.0.1"))
        for contenedor in ("raw", "curated"):
            if not svc.get_container_client(contenedor).exists():
                svc.create_container(contenedor)
        svc.get_blob_client("raw", f"comisiones/{archivo}").upload_blob(csv.read_bytes(), overwrite=True)
        print(f"[{entorno.upper()}] cuenta {cuenta}: contenedores raw/curated listos, subido raw/comisiones/{archivo}")

    print("\nCredenciales para Jenkins (Secret text):")
    for entorno, (cuenta, clave) in CUENTAS.items():
        print(f"  azure-storage-{entorno}:\n    {cadena(cuenta, clave, 'host.docker.internal')}")
    print("\nPara probar desde tu PC (Git Bash):")
    for entorno, (cuenta, clave) in CUENTAS.items():
        print(f"  {entorno}: export AZURE_STORAGE_CONNECTION_STRING='{cadena(cuenta, clave, '127.0.0.1')}'")


if __name__ == "__main__":
    main()
