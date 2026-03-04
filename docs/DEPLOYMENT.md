# Deployment Guide

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.0+ | latest |
| Docker Compose | 2.20+ | latest |
| CPU | 8 cores | 16+ cores |
| RAM | 16 GB | 32 GB |
| SSD Storage | 200 GB | 500 GB |
| OS | Ubuntu 22.04 / Debian 12 | Ubuntu 24.04 |
| GPU (optional) | NVIDIA GTX 1080 | NVIDIA RTX 3090+ |

---

## Quick Start (Docker Compose)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/video-cloud-platform.git
cd video-cloud-platform

# Copy environment template
cp .env.example .env

# Edit credentials and URLs
nano .env
```

### 2. Key environment variables

```bash
# Ingest
SRS_HTTP_PORT=8080
SRS_RTMP_PORT=1935
SRS_SRT_PORT=8890

# AI Analysis
YOLO_MODEL=yolov8n.pt
GPU_ENABLED=false

# Database
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=platform

# Ad Server
AD_DECISION_TIMEOUT_MS=200

# Grafana
GF_SECURITY_ADMIN_PASSWORD=your-grafana-password
```

### 3. Start the platform

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f srs
docker compose logs -f yolo-analyzer
```

### 4. Verify services are healthy

```bash
# SRS API
curl http://localhost:1985/api/v1/versions

# YOLO Analyzer
curl http://localhost:8000/health

# SCTE-35 Processor
curl http://localhost:8001/health

# FFmpeg Transcoder
curl http://localhost:8002/health

# Ad Server
curl http://localhost:3000/health

# Dashboard
curl http://localhost:3002/health
```

### 5. Start a test stream

```bash
# Using FFmpeg
ffmpeg -re -i /path/to/test.mp4 \
  -c:v libx264 -preset fast -b:v 2000k \
  -c:a aac -b:a 128k \
  -f flv rtmp://localhost:1935/live/test

# Watch HLS output
open http://localhost:8080/live/test.m3u8
```

---

## Development Mode

```bash
# Start with hot-reload and debug ports
docker compose -f docker-compose.dev.yml up -d

# Dashboard dev server (with Vite HMR)
cd services/dashboard
npm install
npm run dev
```

---

## Production Deployment (Kubernetes)

### Prerequisites

- Kubernetes 1.28+
- kubectl configured
- Helm 3.14+
- NGINX Ingress Controller installed
- cert-manager installed (for TLS)

### 1. Create namespace and secrets

```bash
kubectl apply -f kubernetes/namespace.yaml

# Create platform secrets
kubectl create secret generic platform-secrets \
  --namespace=video-platform \
  --from-literal=postgres-password='your-secure-password' \
  --from-literal=database-url='postgresql://postgres:your-secure-password@timescaledb:5432/platform' \
  --from-literal=grafana-admin-password='your-grafana-password'
```

### 2. Build and push images

```bash
# Set your registry
REGISTRY=your-registry.io

# Build all images
docker build -t ${REGISTRY}/srs:latest services/ingest/
docker build -t ${REGISTRY}/yolo-analyzer:latest services/ai-analysis/
docker build -t ${REGISTRY}/scte35-processor:latest services/scte35-processor/
docker build -t ${REGISTRY}/ffmpeg-transcoder:latest services/transcoding/
docker build -t ${REGISTRY}/shaka-packager:latest services/packaging/
docker build -t ${REGISTRY}/ad-server:latest services/ad-insertion/
docker build -t ${REGISTRY}/dashboard:latest services/dashboard/

# Push all images
for svc in srs yolo-analyzer scte35-processor ffmpeg-transcoder shaka-packager ad-server dashboard; do
  docker push ${REGISTRY}/${svc}:latest
done
```

### 3. Update image references

```bash
# Update image tags in deployment files
find kubernetes/ -name '*.yaml' -exec \
  sed -i "s|video-platform/|${REGISTRY}/|g" {} \;
```

### 4. Deploy storage and database

```bash
kubectl apply -f kubernetes/analytics/timescaledb-statefulset.yaml
kubectl apply -f kubernetes/ai-analysis/yolo-pvc.yaml

# Wait for database to be ready
kubectl wait --namespace=video-platform \
  --for=condition=ready pod \
  --selector=app=timescaledb \
  --timeout=120s

# Initialize schema
kubectl exec -n video-platform statefulset/timescaledb -- \
  psql -U postgres -d platform -f /docker-entrypoint-initdb.d/init.sql
```

### 5. Deploy all services

```bash
kubectl apply -f kubernetes/ingest/
kubectl apply -f kubernetes/ai-analysis/
kubectl apply -f kubernetes/scte35-processor/
kubectl apply -f kubernetes/transcoding/
kubectl apply -f kubernetes/packaging/
kubectl apply -f kubernetes/ad-insertion/
kubectl apply -f kubernetes/analytics/
kubectl apply -f kubernetes/dashboard/
kubectl apply -f kubernetes/ingress.yaml
```

### 6. Verify deployment

```bash
kubectl get pods -n video-platform
kubectl get services -n video-platform
kubectl get ingress -n video-platform
```

---

## Cloud Deployment

### AWS EKS

```bash
# Create EKS cluster
eksctl create cluster \
  --name video-platform \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type c5.2xlarge \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10

# For GPU nodes (YOLO + FFmpeg)
eksctl create nodegroup \
  --cluster=video-platform \
  --name=gpu-workers \
  --node-type=g4dn.xlarge \
  --nodes=1

# Install NVIDIA device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.16.0/deployments/static/nvidia-device-plugin.yml

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system --set clusterName=video-platform

# Use EBS CSI driver for persistent volumes
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.25"
```

### GCP GKE

```bash
# Create GKE cluster
gcloud container clusters create video-platform \
  --zone=us-central1-a \
  --machine-type=e2-standard-8 \
  --num-nodes=3 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10

# GPU node pool
gcloud container node-pools create gpu-pool \
  --cluster=video-platform \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --num-nodes=1

# Install NVIDIA drivers
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml
```

### Azure AKS

```bash
# Create AKS cluster
az aks create \
  --resource-group video-platform-rg \
  --name video-platform-aks \
  --node-count 3 \
  --node-vm-size Standard_D8s_v3 \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10

# GPU node pool
az aks nodepool add \
  --resource-group video-platform-rg \
  --cluster-name video-platform-aks \
  --name gpunodepool \
  --node-count 1 \
  --node-vm-size Standard_NC6
```

---

## Configuration Management

### Environment-Specific Overrides

```bash
# Development
cp .env.example .env.development
# Production
cp .env.example .env.production

# Use with docker compose
docker compose --env-file .env.production up -d
```

### Kubernetes ConfigMaps

```bash
# Update SRS config
kubectl create configmap srs-config \
  --namespace=video-platform \
  --from-file=srs.conf=services/ingest/srs.conf \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## Monitoring Setup

### Access Grafana

```bash
# Port-forward Grafana
kubectl port-forward -n video-platform svc/grafana 3001:3000

# Open browser
open http://localhost:3001
# Default credentials: admin / (grafana-admin-password from secret)
```

### Import Dashboards

Dashboards are provisioned automatically from `services/analytics/grafana/dashboards/`. To manually import:

```bash
for dashboard in services/analytics/grafana/dashboards/*.json; do
  curl -s -X POST http://admin:${GF_SECURITY_ADMIN_PASSWORD}@localhost:3001/api/dashboards/import \
    -H 'Content-Type: application/json' \
    -d "{\"dashboard\": $(cat $dashboard), \"overwrite\": true}"
done
```

### Prometheus Alerting

```bash
kubectl apply -f configs/prometheus.yml

# Access Prometheus UI
kubectl port-forward -n video-platform svc/prometheus 9090:9090
open http://localhost:9090
```

---

## Backup and Disaster Recovery

### TimescaleDB Backup

```bash
# Continuous WAL archiving with pg_basebackup
kubectl exec -n video-platform statefulset/timescaledb -- \
  pg_dump -U postgres platform | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Upload to S3
aws s3 cp backup_*.sql.gz s3://your-bucket/timescaledb-backups/
```

### Restore from Backup

```bash
# Restore
zcat backup_20241201_120000.sql.gz | \
  kubectl exec -i -n video-platform statefulset/timescaledb -- \
  psql -U postgres platform
```

### Automated Backup CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: timescaledb-backup
  namespace: video-platform
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: postgres:14
              command:
                - /bin/sh
                - -c
                - |
                  pg_dump -h timescaledb -U postgres platform | \
                  gzip > /backup/db_$(date +%Y%m%d).sql.gz
          restartPolicy: OnFailure
```

### HLS Segment Archiving

For DVR/VOD functionality, configure SRS to archive segments to S3:
```bash
# Mount S3 bucket as FUSE filesystem
s3fs your-hls-bucket /var/www/streams \
  -o allow_other \
  -o iam_role=auto
```
