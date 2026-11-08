# Evidencias para el informe

Guarda aquí las capturas con el número de la lista (p. ej. `03_jenkins_stage_view.png`).

| # | Evidencia | Dónde se obtiene | Criterio de la rúbrica |
|---|---|---|---|
| 01 | `pytest -v` con 19 pruebas en verde | terminal local o consola de Jenkins | Pipeline / CI |
| 02 | Ejecución `python -m app.main --env dev` con el log "Pipeline finalizado OK" | terminal | Pipeline (6 pts) |
| 03 | Stage View de Jenkins con todas las etapas en verde | Jenkins → job | CI/CD (4 pts) |
| 04 | Pestaña *Test Result* (JUnit) del build | Jenkins → build | CI/CD |
| 05 | Log de las etapas CD · DEV, QA y PRD con el mensaje `[GATE] … aprobado` | Jenkins → Console Output | CI/CD |
| 06 | Artefactos archivados (Parquet + reporte_calidad.json) | Jenkins → build | Pipeline |
| 07 | Contenedor `raw/comisiones/` con el CSV | Portal Azure → Storage → Containers | Pipeline |
| 08 | Contenedor `curated/rrhh/salario_total_empleados/periodo=202610/` con el Parquet | Portal Azure | Pipeline |
| 09 | Despliegue ARM correcto (Resource group → Deployments) | Portal Azure | Git / ARM |
| 10 | Repositorio en GitHub: estructura, historial de commits y un Pull Request fusionado | GitHub | Git (4 pts) |
| 11 | Disparo automático: build iniciado por "Started by an SCM change" tras un push (o webhook ✔ 200) | Jenkins → build → Console Output | CI/CD |
| 12 | Prueba negativa: build en rojo al subir un CSV con una comisión negativa o un ID duplicado | Jenkins | Informe (registro de pruebas) |
| 13 | Contenido del Parquet (p. ej. `pd.read_parquet(...).head()`) | notebook o terminal | Pipeline |
