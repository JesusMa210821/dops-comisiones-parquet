# DataOps · Cálculo de comisiones de empleados

Pipeline automatizado que calcula el **salario total** de cada empleado combinando la tabla
`dmc.rrhh.empleado` (PostgreSQL) con el archivo `ComisionEmpleados_V1_<periodo>.csv`
(Azure Blob Storage), genera una tabla consolidada en **Parquet** dentro de un Data Lake
(ADLS Gen2) y se despliega en **DEV → QA → PRD** mediante CI/CD con **GitHub + Jenkins**.

```
salario_total = mnt_salario + comision
```

> Proyecto del módulo DE – DataOps (DMC). Camino elegido del enunciado: *Python + GitHub + Jenkins*,
> con plantillas ARM para la infraestructura del Data Lake.

---

## Arquitectura

```
                    ┌──────────── GitHub (main) ────────────┐
   git push ───────▶│  código · tests · Jenkinsfile · ARM   │
                    └───────────────┬───────────────────────┘
                                    │ webhook
                                    ▼
┌──────────────────────── Jenkins (local en Docker o VM) ─────────────────────┐
│ CI: build imagen → flake8 + pytest (JUnit) → smoke test offline             │
│ Infra (opcional): plantillas ARM → ADLS Gen2 por entorno                     │
│ CD: DEV ─gate─▶ QA ─gate─▶ aprobación PRD (automática) ─▶ PRD ─gate          │
└──────────────────────────────────────────────────────────────────────────────┘
          │                                   │
          ▼                                   ▼
 PostgreSQL dmc.rrhh.empleado      Storage del entorno (ADLS Gen2)
 (+ cargo, departamento)           raw/comisiones/ComisionEmpleados_V1_<periodo>.csv
                                   curated/rrhh/salario_total_empleados/periodo=<periodo>/*.parquet
```

| Entorno | Fuente CSV | Salida Parquet | Quality gate (cruce mínimo CSV↔BD) |
|---|---|---|---|
| dev | `data/input/` (local) | `output/dev/` (artefacto Jenkins) | 80 % |
| qa  | Blob `raw` | ADLS `curated` | 90 % |
| prd | Blob `raw` | ADLS `curated` | 95 % |

## Contenido del repositorio

```
app/
  config.py        Configuración por entorno + credenciales desde variables de entorno
  extract.py       Lectura de PostgreSQL (empleado + cargo + departamento) y del CSV (Blob/local)
  transform.py     Validaciones, join por empleado_id, salario_total y quality gate
  load.py          Escritura Parquet local y en ADLS Gen2 + reporte_calidad.json
  main.py          Punto de entrada: python -m app.main --env <dev|qa|prd> [--offline]
config/            dev.json · qa.json · prd.json (sin secretos)
data/input/        ComisionEmpleados_V1_202610.csv
infra/arm/         azuredeploy.json + parámetros por entorno (ADLS Gen2, contenedores raw/curated)
scripts/           deploy_arm.sh · upload_comisiones.sh · quality_gate.py · azurite_setup.py · azurite_listar.py
tests/             Pruebas unitarias, de integración offline y de validación ARM (19 tests)
Dockerfile         Imagen del pipeline
docker-compose.yml Ejecución local
Jenkinsfile        Pipeline CI/CD declarativo
jenkins-local/     Jenkins en Docker para ejecutar el CI/CD en tu PC
local-azure/       Azurite (emulador de Blob Storage) si no hay suscripción de Azure
```

## Reglas de negocio y calidad

- **Join interno** por `empleado_id`. Los IDs que no cruzan se registran en el log y en
  `reporte_calidad.json` (`ids_csv_sin_empleado`, `ids_empleado_sin_comision`).
- `salario_total = mnt_salario + comision`, tal como pide el enunciado.
- Se marca `excede_tope_comision` cuando la comisión supera `mnt_tope_comision`. Si se pone
  `"aplicar_tope_comision": true` en la configuración, la comisión se limita al tope (como en el
  ejercicio de clase de Jenkins).
- El pipeline **se detiene** si: faltan columnas, hay `empleado_id` vacíos o duplicados, hay
  comisiones vacías o negativas, o el porcentaje de cruce queda por debajo del umbral del entorno.
- El Parquet incluye: periodo, datos del empleado, cargo, departamento, salario, comisión, tope,
  comisión aplicada, salario_total, entorno y fecha de proceso.

---

## Despliegue paso a paso

### 1. Requisitos
- Cuenta de GitHub, Jenkins con un agente con Docker (la VM `vm_docker` de clase) y Azure CLI
  instalado en ese agente si vas a desplegar la infraestructura desde Jenkins.
- Suscripción de Azure para los entornos QA/PRD.

### 2. Clonar y probar en local
```bash
git clone https://github.com/<tu_usuario>/dops-comisiones-parquet.git
cd dops-comisiones-parquet
pip install -r requirements-dev.txt
flake8 && pytest -v                      # 19 pruebas
python -m app.main --env dev --offline   # sin red: genera output/dev/periodo=202610/*.parquet
```
Con acceso a la base de datos de clase:
```bash
cp .env.example .env    # completa PG_* (material del curso)
python -m app.main --env dev
# o con Docker
ENTORNO=dev docker compose up --build
```

### 3. Infraestructura (plantillas ARM)
```bash
az login
./scripts/deploy_arm.sh qa  rg-dops-comisiones-qa  eastus2
./scripts/deploy_arm.sh prd rg-dops-comisiones-prd eastus2
# Sube el CSV al contenedor raw de cada storage (nombre en el output del despliegue)
./scripts/upload_comisiones.sh <storage_qa>  202610
./scripts/upload_comisiones.sh <storage_prd> 202610
```
Copia la *connection string* de cada storage (Portal → Storage account → Access keys).

### 3-B. Sin suscripción de Azure: Data Lake emulado (Azurite)
Si tu cuenta no tiene suscripción activa, QA y PRD pueden usar **Azurite**, el emulador oficial
de Azure Blob Storage. El código no cambia: solo la cadena de conexión.
```bash
cd local-azure && docker compose up -d && cd ..
python scripts/azurite_setup.py      # crea raw/curated en dopsqa y dopsprd, sube el CSV e imprime las credenciales
python scripts/azurite_listar.py     # evidencia: contenido de raw y curated por entorno
```
En Jenkins usa como `azure-storage-qa` / `azure-storage-prd` las cadenas con `host.docker.internal`
que imprime `azurite_setup.py`. Las plantillas ARM siguen versionadas y se validan en el CI; se
despliegan con el paso 3 cuando haya una suscripción disponible.

### 4. Configurar Jenkins
Si no tienes un Jenkins en una VM, levántalo en tu PC con Docker Desktop:
```bash
cd jenkins-local
docker compose up -d --build
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```
Abre http://localhost:8080, pega la contraseña, elige *Install suggested plugins* y crea tu usuario.
El job corre en el nodo `built-in` (parámetro `AGENTE`). Si usas la VM de clase, pon `AGENTE=vm_docker`.

1. **Credentials** (Manage Jenkins → Credentials → Global):

   | ID | Tipo | Valor |
   |---|---|---|
   | `pg-rrhh-readonly` | Username with password | usuario / contraseña PostgreSQL |
   | `pg-host` | Secret text | host PostgreSQL |
   | `azure-storage-qa` | Secret text | connection string QA |
   | `azure-storage-prd` | Secret text | connection string PRD |
   | `azure-sp` *(opcional)* | Username with password | appId / secret del service principal |

2. **Nuevo item → Pipeline** → *Pipeline script from SCM* → Git → URL del repo → rama `main`
   → Script path `Jenkinsfile`. Marca *GitHub hook trigger for GITScm polling*.
3. Disparo automático: con Jenkins local, GitHub no puede llamar a `localhost`, así que el Jenkinsfile
   revisa el repositorio cada 5 minutos (`pollSCM`). Si Jenkins es accesible desde internet, añade en
   GitHub **Settings → Webhooks** → `http://<IP_JENKINS>:8080/github-webhook/` (content type `application/json`).
4. Ejecuta **Build with Parameters** la primera vez (Jenkins carga los parámetros del Jenkinsfile).

### 5. Flujo de trabajo con Git
```bash
git checkout -b feat/<cambio>
# ... cambios ...
git add . && git commit -m "feat: <descripción>"
git push -u origin feat/<cambio>
# Pull Request a main → al hacer merge, el webhook dispara CI/CD
```

## Etapas del Jenkinsfile

| Etapa | Qué hace | Falla si… |
|---|---|---|
| CI · Build imagen | `docker build` | el Dockerfile o las dependencias fallan |
| CI · Lint y pruebas | `flake8` + `pytest` (publica JUnit) | hay errores de estilo o tests rojos |
| CI · Smoke test offline | ejecuta el pipeline completo sin red | el flujo E2E no genera el Parquet |
| Infra · ARM *(opcional)* | `az deployment group validate/create` por entorno | la plantilla es inválida |
| CD · DEV / QA / PRD | ejecuta el pipeline con las credenciales del entorno | la extracción, la carga o la calidad fallan |
| Quality gate (en cada CD) | lee `reporte_calidad.json` | el gate no está `APROBADO` |
| Aprobación PRD | automática si DEV y QA aprobaron (`APROBACION_MANUAL_PRD=true` para pedir confirmación) | se rechaza o vence el plazo |

Artefactos archivados por build: los Parquet y el `reporte_calidad.json` de cada entorno.

## Evidencias
Ver [`docs/evidencias/README.md`](docs/evidencias/README.md) para la lista de capturas del informe.
