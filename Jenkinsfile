pipeline {
    agent any

    environment {
        IMAGE_NAME = 'azure-self-healing-demo'
    }

    stages {
        stage('Python Tests') {
            steps {
                dir('app') {
                    sh 'python3 -m unittest discover -s tests -v'
                }
            }
        }

        stage('Docker Build') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} ./app'
            }
        }

        stage('Terraform Format') {
            steps {
                sh 'terraform -chdir=terraform fmt -check'
            }
        }

        stage('Terraform Validate') {
            steps {
                sh 'terraform -chdir=terraform init -backend=false -input=false'
                sh 'terraform -chdir=terraform validate'
            }
        }

        stage('Kubernetes Manifest Check') {
            steps {
                sh "python3 - <<'PY'\nfrom pathlib import Path\nimport yaml\nfor path in Path('k8s').rglob('*.yaml'):\n    list(yaml.safe_load_all(path.read_text()))\n    print(f'validated {path}')\nfor path in Path('clusters').rglob('*.yaml'):\n    list(yaml.safe_load_all(path.read_text()))\n    print(f'validated {path}')\nPY"
            }
        }
    }

    post {
        always {
            deleteDir()
        }
    }
}
