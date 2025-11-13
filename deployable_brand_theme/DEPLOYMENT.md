# Deployment & CI/CD Guide

## 🚀 Deployment Strategies

### Strategy 1: Docker Compose (Recommended for Quick Start)

**Single Brand Environment:**

```bash
# Set brand via environment variable
export ODOO_BRAND_CODE=greenmotive

# Start services
docker-compose -f docker-compose.brand.yml up -d

# Check logs
docker-compose -f docker-compose.brand.yml logs -f odoo
```

**Multi-Brand Environments (separate containers):**

```bash
# Start all services including multi-brand profile
docker-compose -f docker-compose.brand.yml --profile multi-brand up -d

# This starts:
# - Port 8069: GreenMotive brand
# - Port 8070: TechPro brand
```

---

### Strategy 2: Kubernetes Deployment

**Namespace per Brand:**

```yaml
# k8s/greenmotive-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: greenmotive-prod
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: odoo-greenmotive
  namespace: greenmotive-prod
spec:
  replicas: 2
  selector:
    matchLabels:
      app: odoo
      brand: greenmotive
  template:
    metadata:
      labels:
        app: odoo
        brand: greenmotive
    spec:
      containers:
      - name: odoo
        image: odoo:17.0
        env:
        - name: ODOO_BRAND_CODE
          value: "greenmotive"
        - name: HOST
          value: "postgres-service"
        - name: USER
          value: "odoo"
        - name: PASSWORD
          valueFrom:
            secretKeyRef:
              name: odoo-secrets
              key: db-password
        ports:
        - containerPort: 8069
        volumeMounts:
        - name: addons
          mountPath: /mnt/extra-addons
      volumes:
      - name: addons
        persistentVolumeClaim:
          claimName: odoo-addons-pvc
      initContainers:
      - name: provision-brand
        image: odoo:17.0
        command: ["/bin/bash", "-c"]
        args:
        - |
          cd /mnt/extra-addons/deployable_brand_theme
          python3 provision_brand.py --brand-code $ODOO_BRAND_CODE
        env:
        - name: ODOO_BRAND_CODE
          value: "greenmotive"
---
apiVersion: v1
kind: Service
metadata:
  name: odoo-service
  namespace: greenmotive-prod
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8069
  selector:
    app: odoo
    brand: greenmotive
```

**Apply:**

```bash
kubectl apply -f k8s/greenmotive-namespace.yaml
kubectl get pods -n greenmotive-prod
```

---

### Strategy 3: Ansible Playbook

```yaml
# ansible/deploy-brand.yml
---
- name: Deploy Odoo with Brand
  hosts: odoo_servers
  become: yes
  vars:
    odoo_version: "17.0"
    brand_code: "{{ lookup('env', 'BRAND_CODE') | default('greenmotive') }}"
    db_name: "{{ lookup('env', 'DB_NAME') | default('odoo_prod') }}"
  
  tasks:
    - name: Pull Odoo Docker image
      docker_image:
        name: "odoo:{{ odoo_version }}"
        source: pull
    
    - name: Copy brand theme addon
      synchronize:
        src: ../deployable_brand_theme/
        dest: /opt/odoo/addons/deployable_brand_theme/
        delete: yes
    
    - name: Start Odoo container
      docker_container:
        name: "odoo_{{ brand_code }}"
        image: "odoo:{{ odoo_version }}"
        state: started
        restart_policy: always
        env:
          HOST: "{{ postgres_host }}"
          USER: "{{ postgres_user }}"
          PASSWORD: "{{ postgres_password }}"
          ODOO_BRAND_CODE: "{{ brand_code }}"
        volumes:
          - /opt/odoo/addons:/mnt/extra-addons
        ports:
          - "8069:8069"
    
    - name: Wait for Odoo to start
      wait_for:
        port: 8069
        delay: 10
        timeout: 300
    
    - name: Install brand theme module
      shell: |
        docker exec odoo_{{ brand_code }} \
          odoo -d {{ db_name }} -i deployable_brand_theme --stop-after-init
    
    - name: Provision brand
      shell: |
        docker exec odoo_{{ brand_code }} \
          python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
          --brand-code {{ brand_code }} \
          --db-name {{ db_name }}
    
    - name: Restart Odoo
      docker_container:
        name: "odoo_{{ brand_code }}"
        state: restarted
```

**Run:**

```bash
export BRAND_CODE=techpro
export DB_NAME=techpro_prod
ansible-playbook -i inventory.ini ansible/deploy-brand.yml
```

---

## 🔄 CI/CD Pipelines

### GitHub Actions

```yaml
# .github/workflows/deploy-brand.yml
name: Deploy Brand Environment

on:
  push:
    branches: [main, staging]
  workflow_dispatch:
    inputs:
      brand_code:
        description: 'Brand code to deploy'
        required: true
        default: 'greenmotive'
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || 'staging' }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ secrets.REGISTRY_URL }}
          username: ${{ secrets.REGISTRY_USERNAME }}
          password: ${{ secrets.REGISTRY_PASSWORD }}
      
      - name: Build Odoo with Brand Theme
        run: |
          docker build \
            --build-arg ODOO_VERSION=17.0 \
            --build-arg BRAND_CODE=${{ github.event.inputs.brand_code || 'greenmotive' }} \
            -t ${{ secrets.REGISTRY_URL }}/odoo-branded:${{ github.sha }} \
            -f Dockerfile.brand .
      
      - name: Push image
        run: |
          docker push ${{ secrets.REGISTRY_URL }}/odoo-branded:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        uses: azure/k8s-deploy@v4
        with:
          manifests: |
            k8s/deployment.yaml
            k8s/service.yaml
          images: |
            ${{ secrets.REGISTRY_URL }}/odoo-branded:${{ github.sha }}
          namespace: ${{ github.event.inputs.environment }}
      
      - name: Run brand provisioning
        run: |
          kubectl exec -n ${{ github.event.inputs.environment }} \
            deployment/odoo -- \
            python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
            --brand-code ${{ github.event.inputs.brand_code || 'greenmotive' }}
      
      - name: Health check
        run: |
          curl -f https://${{ github.event.inputs.environment }}.example.com/web/health || exit 1
```

---

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE/odoo-branded
  BRAND_CODE: greenmotive

build:
  stage: build
  image: docker:24.0
  services:
    - docker:24.0-dind
  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $DOCKER_IMAGE:$CI_COMMIT_SHA -f Dockerfile.brand .
    - docker push $DOCKER_IMAGE:$CI_COMMIT_SHA
  only:
    - main
    - staging

test:
  stage: test
  image: $DOCKER_IMAGE:$CI_COMMIT_SHA
  services:
    - postgres:15
  variables:
    POSTGRES_DB: test_db
    POSTGRES_USER: odoo
    POSTGRES_PASSWORD: odoo
  script:
    - odoo -d test_db -i deployable_brand_theme --stop-after-init --test-enable
    - python3 -m pytest tests/
  only:
    - main
    - staging

deploy_staging:
  stage: deploy
  image: bitnami/kubectl:latest
  variables:
    BRAND_CODE: techpro
    ENVIRONMENT: staging
  script:
    - kubectl config use-context $KUBE_CONTEXT_STAGING
    - |
      cat <<EOF | kubectl apply -f -
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: odoo-$BRAND_CODE
        namespace: $ENVIRONMENT
      spec:
        replicas: 1
        template:
          spec:
            containers:
            - name: odoo
              image: $DOCKER_IMAGE:$CI_COMMIT_SHA
              env:
              - name: ODOO_BRAND_CODE
                value: "$BRAND_CODE"
      EOF
    - kubectl rollout status deployment/odoo-$BRAND_CODE -n $ENVIRONMENT
  only:
    - staging
  environment:
    name: staging
    url: https://staging.techpro.example.com

deploy_production:
  stage: deploy
  image: bitnami/kubectl:latest
  variables:
    BRAND_CODE: greenmotive
    ENVIRONMENT: production
  script:
    - kubectl config use-context $KUBE_CONTEXT_PROD
    - kubectl set image deployment/odoo-$BRAND_CODE odoo=$DOCKER_IMAGE:$CI_COMMIT_SHA -n $ENVIRONMENT
    - kubectl rollout status deployment/odoo-$BRAND_CODE -n $ENVIRONMENT
  only:
    - main
  when: manual
  environment:
    name: production
    url: https://greenmotive.example.com
```

---

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    parameters {
        choice(name: 'BRAND_CODE', choices: ['greenmotive', 'techpro', 'luxe'], description: 'Brand to deploy')
        choice(name: 'ENVIRONMENT', choices: ['staging', 'production'], description: 'Target environment')
    }
    
    environment {
        DOCKER_IMAGE = "registry.example.com/odoo-branded"
        ODOO_VERSION = "17.0"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build') {
            steps {
                script {
                    docker.build("${DOCKER_IMAGE}:${BUILD_NUMBER}", 
                                 "--build-arg BRAND_CODE=${params.BRAND_CODE} " +
                                 "-f Dockerfile.brand .")
                }
            }
        }
        
        stage('Test') {
            steps {
                sh '''
                    docker run --rm \
                      -e POSTGRES_HOST=postgres \
                      -e POSTGRES_USER=odoo \
                      -e POSTGRES_PASSWORD=odoo \
                      ${DOCKER_IMAGE}:${BUILD_NUMBER} \
                      odoo -d test_db -i deployable_brand_theme --test-enable --stop-after-init
                '''
            }
        }
        
        stage('Push Image') {
            steps {
                script {
                    docker.withRegistry('https://registry.example.com', 'docker-credentials') {
                        docker.image("${DOCKER_IMAGE}:${BUILD_NUMBER}").push()
                        docker.image("${DOCKER_IMAGE}:${BUILD_NUMBER}").push("${params.ENVIRONMENT}-latest")
                    }
                }
            }
        }
        
        stage('Deploy') {
            steps {
                script {
                    if (params.ENVIRONMENT == 'production') {
                        input message: 'Deploy to production?', ok: 'Deploy'
                    }
                    
                    sh """
                        kubectl set image deployment/odoo-${params.BRAND_CODE} \
                          odoo=${DOCKER_IMAGE}:${BUILD_NUMBER} \
                          -n ${params.ENVIRONMENT}
                        
                        kubectl rollout status deployment/odoo-${params.BRAND_CODE} \
                          -n ${params.ENVIRONMENT}
                    """
                }
            }
        }
        
        stage('Provision Brand') {
            steps {
                sh """
                    kubectl exec -n ${params.ENVIRONMENT} \
                      deployment/odoo-${params.BRAND_CODE} -- \
                      python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
                      --brand-code ${params.BRAND_CODE}
                """
            }
        }
        
        stage('Health Check') {
            steps {
                retry(3) {
                    sh """
                        curl -f https://${params.ENVIRONMENT}.example.com/web/health
                    """
                }
            }
        }
    }
    
    post {
        success {
            slackSend(color: 'good', 
                     message: "Deployed ${params.BRAND_CODE} to ${params.ENVIRONMENT} successfully!")
        }
        failure {
            slackSend(color: 'danger', 
                     message: "Failed to deploy ${params.BRAND_CODE} to ${params.ENVIRONMENT}")
        }
    }
}
```

---

## 🐳 Dockerfile for Branded Builds

```dockerfile
# Dockerfile.brand
FROM odoo:17.0

ARG BRAND_CODE=greenmotive

# Install dependencies
USER root
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*

# Copy brand theme addon
COPY deployable_brand_theme /mnt/extra-addons/deployable_brand_theme/

# Set brand environment variable
ENV ODOO_BRAND_CODE=${BRAND_CODE}

# Run as odoo user
USER odoo

# Custom entrypoint for brand provisioning
COPY docker-entrypoint-brand.sh /
ENTRYPOINT ["/docker-entrypoint-brand.sh"]
CMD ["odoo"]
```

**Custom entrypoint:**

```bash
#!/bin/bash
# docker-entrypoint-brand.sh
set -e

# Wait for database
until psql -h "$HOST" -U "$USER" -d postgres -c '\q'; do
  echo "Postgres is unavailable - sleeping"
  sleep 1
done

# Install module on first run
if [ ! -f /var/lib/odoo/.brand_provisioned ]; then
    echo "Installing brand theme..."
    odoo -d "$POSTGRES_DB" -i deployable_brand_theme --stop-after-init
    
    echo "Provisioning brand: $ODOO_BRAND_CODE"
    python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
        --brand-code "$ODOO_BRAND_CODE" \
        --db-name "$POSTGRES_DB"
    
    touch /var/lib/odoo/.brand_provisioned
fi

# Start Odoo
exec "$@"
```

---

## 🔧 Environment-Specific Configuration

### `.env` files

```bash
# .env.greenmotive
ODOO_BRAND_CODE=greenmotive
POSTGRES_DB=greenmotive_prod
ODOO_URL=https://greenmotive.example.com
```

```bash
# .env.techpro
ODOO_BRAND_CODE=techpro
POSTGRES_DB=techpro_prod
ODOO_URL=https://techpro.example.com
```

**Usage:**

```bash
docker-compose --env-file .env.greenmotive up -d
```

---

## 📊 Monitoring & Observability

### Prometheus Metrics

Add to `provision_brand.py`:

```python
from prometheus_client import Counter, Gauge

brand_deployments = Counter('odoo_brand_deployments_total', 
                           'Total brand deployments', 
                           ['brand_code', 'status'])

active_brands = Gauge('odoo_active_brands', 
                     'Number of active brands')

def assign_brand_to_website(models, uid, db, password, brand_code, website_domain=None):
    try:
        # ... existing code ...
        brand_deployments.labels(brand_code=brand_code, status='success').inc()
        return True
    except Exception as e:
        brand_deployments.labels(brand_code=brand_code, status='failure').inc()
        raise
```

---

## 🎯 Best Practices

1. **Version Control**: Tag brand configurations in git
2. **Secrets Management**: Use vault/secrets manager for credentials
3. **Rollback Strategy**: Keep previous 3 image versions
4. **Health Checks**: Implement `/web/health` endpoint monitoring
5. **Blue-Green Deployments**: Deploy to staging slot first
6. **Database Backups**: Automated daily backups before deployments
7. **Asset CDN**: Use CDN for static assets (logos, CSS)
8. **Cache Warming**: Pre-warm cache after deployment

---

## 🚨 Troubleshooting

**Issue: Brand not applied after deployment**
```bash
# Check brand code in environment
kubectl exec deployment/odoo -- env | grep ODOO_BRAND_CODE

# Manually re-provision
kubectl exec deployment/odoo -- \
  python3 /mnt/extra-addons/deployable_brand_theme/provision_brand.py \
  --brand-code greenmotive
```

**Issue: Assets not loading**
```bash
# Clear Odoo assets cache
kubectl exec deployment/odoo -- \
  odoo -d production_db --stop-after-init --update=deployable_brand_theme
```

**Issue: Database migration failed**
```bash
# Check logs
kubectl logs deployment/odoo --tail=100

# Rollback database
pg_restore -d production_db backup.sql
```

---

**Ready for production! 🚀**
