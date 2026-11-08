"""Lista el contenido del Data Lake emulado (evidencia de raw y curated por entorno).

Uso: python scripts/azurite_listar.py
"""
from azure.storage.blob import BlobServiceClient

from azurite_setup import CUENTAS, cadena

for entorno, (cuenta, clave) in CUENTAS.items():
    svc = BlobServiceClient.from_connection_string(cadena(cuenta, clave, "127.0.0.1"))
    print(f"=== {entorno.upper()} · storage account {cuenta} ===")
    for contenedor in ("raw", "curated"):
        for b in svc.get_container_client(contenedor).list_blobs():
            print(f"  {contenedor}/{b.name}  ({b.size:,} bytes, {b.last_modified:%Y-%m-%d %H:%M})")
