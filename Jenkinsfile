// Pipeline CI/CD del flujo de comisiones: CI (lint, tests, validación ARM, smoke test)
// y CD con promoción automática DEV -> QA -> PRD controlada por quality gates.
//
// Funciona igual en un Jenkins local en Docker (jenkins-local/) o en un agente VM con Docker:
// no usa bind mounts, los resultados se copian del contenedor con `docker cp`.
//
// Credenciales necesarias en Jenkins (Manage Jenkins > Credentials):
//   pg-rrhh-readonly        Username with password  -> usuario/contraseña PostgreSQL
//   pg-host                 Secret text             -> host PostgreSQL
//   azure-storage-qa        Secret text             -> connection string storage QA
//   azure-storage-prd       Secret text             -> connection string storage PRD
//   azure-sp (opcional)     Username with password  -> appId / secret del service principal (despliegue ARM)

pipeline {
    agent { label params.AGENTE ?: 'built-in' }

    triggers {
        githubPush()            // webhook de GitHub (si Jenkins es accesible desde internet)
        pollSCM('H/5 * * * *')  // Jenkins local: revisa GitHub cada 5 minutos
    }

    parameters {
        string(name: 'AGENTE', defaultValue: 'built-in', description: 'Label del nodo con Docker (built-in = Jenkins local)')
        string(name: 'PERIODO', defaultValue: '202610', description: 'Periodo del CSV ComisionEmpleados_V1_<PERIODO>.csv')
        booleanParam(name: 'DESPLEGAR_INFRA', defaultValue: false, description: 'Aplicar plantillas ARM antes del CD (requiere az CLI en el nodo)')
        booleanParam(name: 'APROBACION_MANUAL_PRD', defaultValue: false,
                     description: 'false = PRD se aprueba automáticamente si QA pasa el quality gate')
        string(name: 'AZURE_TENANT', defaultValue: '', description: 'Tenant ID (solo si DESPLEGAR_INFRA)')
        string(name: 'AZURE_RG_PREFIX', defaultValue: 'rg-dops-comisiones', description: 'Prefijo de resource groups')
    }

    environment {
        IMAGEN  = "dops-comisiones:${env.BUILD_NUMBER}"
        PERIODO = "${params.PERIODO ?: '202610'}"
    }

    options {
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'rm -rf output reports && git log -1 --pretty="format:Commit %h | %an | %s"'
            }
        }

        stage('CI · Build imagen') {
            steps {
                sh 'docker build -t $IMAGEN .'
            }
        }

        stage('CI · Lint y pruebas') {
            steps {
                script {
                    enContenedor('tests', '--entrypoint sh', '-c "flake8 && pytest -v --junitxml=reports/junit.xml"')
                }
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'reports/junit.xml' }
            }
        }

        stage('CI · Smoke test offline') {
            steps {
                script { enContenedor('smoke', '-e PERIODO', '--env dev --offline') }
            }
        }

        stage('Infra · ARM') {
            when { expression { params.DESPLEGAR_INFRA } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'azure-sp',
                                 usernameVariable: 'AZ_APP_ID', passwordVariable: 'AZ_SECRET')]) {
                    sh '''
                        az login --service-principal -u "$AZ_APP_ID" -p "$AZ_SECRET" --tenant "$AZURE_TENANT" -o none
                        for ENTORNO in dev qa prd; do
                          ./scripts/deploy_arm.sh $ENTORNO "${AZURE_RG_PREFIX}-$ENTORNO"
                        done
                    '''
                }
            }
        }

        stage('CD · DEV') {
            steps {
                script { desplegar('dev', '') }
            }
        }

        stage('CD · QA') {
            steps {
                script { desplegar('qa', 'azure-storage-qa') }
            }
        }

        stage('Aprobación PRD') {
            steps {
                script {
                    if (params.APROBACION_MANUAL_PRD) {
                        timeout(time: 30, unit: 'MINUTES') {
                            input message: "¿Desplegar periodo ${env.PERIODO} en PRODUCCIÓN?", ok: 'Desplegar'
                        }
                    } else {
                        echo 'Aprobación automática: DEV y QA superaron sus quality gates.'
                    }
                }
            }
        }

        stage('CD · PRD') {
            steps {
                script { desplegar('prd', 'azure-storage-prd') }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'output/**/*.parquet, output/**/*.json', allowEmptyArchive: true
        }
        success { echo "Despliegue completo DEV -> QA -> PRD del periodo ${env.PERIODO}" }
        failure { echo 'El pipeline falló: revisa la etapa en rojo y el reporte_calidad.json archivado.' }
        cleanup { sh 'docker image rm -f $IMAGEN || true' }
    }
}

// Ejecuta el pipeline de un entorno con sus credenciales y aplica el quality gate
// (aprobación automatizada) dentro del mismo contenedor.
def desplegar(String entorno, String credStorage) {
    def creds = [
        usernamePassword(credentialsId: 'pg-rrhh-readonly', usernameVariable: 'PG_USER', passwordVariable: 'PG_PASSWORD'),
        string(credentialsId: 'pg-host', variable: 'PG_HOST'),
    ]
    if (credStorage) {
        creds << string(credentialsId: credStorage, variable: 'AZURE_STORAGE_CONNECTION_STRING')
    }
    withCredentials(creds) {
        enContenedor(entorno,
            '--entrypoint sh -e PG_HOST -e PG_USER -e PG_PASSWORD -e PG_DB=dmc -e PG_PORT=5432 -e AZURE_STORAGE_CONNECTION_STRING -e PERIODO',
            "-c \"python -m app.main --env ${entorno} && python scripts/quality_gate.py ${entorno} \$PERIODO\"")
    }
}

// docker create + start + docker cp: los resultados (output/, reports/) vuelven al workspace
// sin depender de bind mounts (necesario cuando Jenkins corre dentro de un contenedor).
def enContenedor(String nombre, String opciones, String argumentos) {
    def c = "dops-${env.BUILD_NUMBER}-${nombre}"
    sh """
        mkdir -p output reports
        docker rm -f ${c} >/dev/null 2>&1 || true
        docker create --name ${c} ${opciones} \$IMAGEN ${argumentos}
        set +e
        docker start -a ${c}
        RC=\$?
        set -e
        docker cp ${c}:/app/output/. output/ 2>/dev/null || true
        docker cp ${c}:/app/reports/. reports/ 2>/dev/null || true
        docker rm -f ${c} >/dev/null
        exit \$RC
    """
}
