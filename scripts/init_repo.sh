#!/usr/bin/env bash
# Crea el historial inicial del repositorio con commits por etapa y una rama feature fusionada,
# usando TU identidad de Git. Ejecútalo una sola vez dentro de la carpeta descomprimida.
# Uso: ./scripts/init_repo.sh https://github.com/<tu_usuario>/dops-comisiones-parquet.git
set -euo pipefail
REMOTO=${1:?Indica la URL del repositorio vacío de GitHub}
git config user.name >/dev/null || { echo 'Configura antes: git config --global user.name "Tu Nombre"'; exit 1; }

git init -b main
git add .gitignore .env.example .flake8 requirements.txt requirements-dev.txt README.md
git commit -m "chore: estructura base, dependencias y README"
git add app/ config/ data/
git commit -m "feat: pipeline de comisiones (PostgreSQL + CSV -> Parquet)"
git add tests/
git commit -m "test: pruebas unitarias, integración offline y validación ARM"
git add infra/ scripts/deploy_arm.sh scripts/upload_comisiones.sh
git commit -m "feat(infra): plantillas ARM del Data Lake por entorno"

git checkout -b feat/cicd-jenkins
git add Dockerfile docker-compose.yml Jenkinsfile scripts/quality_gate.py jenkins-local/
git commit -m "ci: imagen Docker y Jenkinsfile con CD DEV -> QA -> PRD y quality gates"
git add docs/ scripts/init_repo.sh
git commit -m "docs: checklist de evidencias"
git checkout main
git merge --no-ff feat/cicd-jenkins -m "merge: feat/cicd-jenkins"

git remote add origin "$REMOTO"
git push -u origin main feat/cicd-jenkins
git log --oneline --graph
