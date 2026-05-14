pipeline {
    agent any

    environment {
        APP_NAME = "python-ai-cicd-app"
        IMAGE_TAG = "dev-${BUILD_NUMBER}"
        IMAGE_NAME = "${APP_NAME}:${IMAGE_TAG}"

        GIT_REPO = "https://github.com/Varsith/apex_CI-CD_pipeline.git"
        GIT_CREDENTIALS_ID = "GITHUB_CREDENTIALS"

        OCI_CONFIG_PROFILE = "DEFAULT"
    }

    stages {

        stage('Clean Workspace') {
            steps {
                cleanWs()
            }
        }

        stage('Checkout Dev Branch') {
            steps {
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "*/dev"]],
                    userRemoteConfigs: [[
                        url: "${GIT_REPO}",
                        credentialsId: "${GIT_CREDENTIALS_ID}"
                    ]]
                ])
            }
        }

        stage('Show Build Info') {
            steps {
                sh '''
                    echo "Branch: dev"
                    echo "Build Number: ${BUILD_NUMBER}"
                    echo "Docker Image Name: ${IMAGE_NAME}"
                    echo "Workspace: ${WORKSPACE}"
                '''
            }
        }

        stage('Prepare OCI Config From Jenkins Credentials') {
            steps {
                withCredentials([
                    file(credentialsId: 'OCI_CONFIG_FILE', variable: 'OCI_CONFIG_FILE_PATH'),
                    file(credentialsId: 'OCI_PRIVATE_KEY_FILE', variable: 'OCI_PRIVATE_KEY_PATH')
                ]) {
                    sh '''
                        echo "Preparing OCI config files..."

                        mkdir -p .oci

                        cp "$OCI_CONFIG_FILE_PATH" .oci/config
                        cp "$OCI_PRIVATE_KEY_PATH" .oci/oci_api_key.pem

                        chmod 600 .oci/config
                        chmod 600 .oci/oci_api_key.pem

                        echo "Before key_file correction:"
                        grep key_file .oci/config || true

                        sed -i.bak "s|^key_file=.*|key_file=${WORKSPACE}/.oci/oci_api_key.pem|" .oci/config

                        echo "After key_file correction:"
                        grep key_file .oci/config || true
                    '''
                }
            }
        }

        stage('Set Up Python Environment') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate

                    python --version
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Generate Pytest Test Cases Using OCI GenAI') {
            steps {
                withCredentials([
                    string(credentialsId: 'OCI_COMPARTMENT_ID', variable: 'OCI_COMPARTMENT_ID_VALUE'),
                    string(credentialsId: 'OCI_GENAI_ENDPOINT', variable: 'OCI_GENAI_ENDPOINT_VALUE'),
                    string(credentialsId: 'OCI_CHAT_MODEL_ID', variable: 'OCI_CHAT_MODEL_ID_VALUE')
                ]) {
                    sh '''
                        . venv/bin/activate

                        export OCI_CONFIG_FILE="${WORKSPACE}/.oci/config"
                        export OCI_CONFIG_PROFILE="DEFAULT"

                        export OCI_COMPARTMENT_ID="$OCI_COMPARTMENT_ID_VALUE"
                        export OCI_GENAI_ENDPOINT="$OCI_GENAI_ENDPOINT_VALUE"
                        export OCI_CHAT_MODEL_ID="$OCI_CHAT_MODEL_ID_VALUE"

                        echo "Running AI test generation..."
                        python scripts/generate_tests_ai.py

                        echo "Generated files inside tests folder:"
                        ls -la tests/

                        echo "Generated pytest code:"
                        cat tests/test_ai_generated.py
                    '''
                }
            }
        }

        stage('Run Pytest') {
            steps {
                sh '''
                    . venv/bin/activate

                    mkdir -p reports

                    pytest tests/ \
                        --junitxml=reports/pytest-report.xml \
                        --html=reports/pytest-report.html \
                        --self-contained-html
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/pytest-report.xml'
                    archiveArtifacts artifacts: 'reports/pytest-report.html', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image From Dockerfile') {
            steps {
                sh '''
                    echo "Building Docker image from Dockerfile..."

                    docker build -t ${IMAGE_NAME} .

                    echo "Docker image created successfully:"
                    docker images | grep ${APP_NAME} || true
                '''
            }
        }

        stage('Test Docker Image Locally') {
            steps {
                sh '''
                    echo "Running Docker image locally to verify it starts..."

                    docker run --rm ${IMAGE_NAME}
                '''
            }
        }
    }

    post {
        success {
            echo "Dev branch pipeline completed successfully. Docker image created locally in Jenkins machine."
            echo "Image name: ${IMAGE_NAME}"
        }

        failure {
            echo "Pipeline failed. Check the Jenkins console output."
        }

        always {
            sh '''
                rm -rf .oci || true
            '''
        }
    }
}