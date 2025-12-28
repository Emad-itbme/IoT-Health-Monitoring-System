#  Deployment Guide

Complete instructions for deploying the IoT Health Monitoring System to production.

## Table of Contents
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [AWS Deployment](#aws-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
```bash
# Python 3.8+
python --version

# Docker & Docker Compose
docker --version
docker-compose --version

# Arduino IDE (for firmware)
# Download: https://arduino.cc/
```

### Setup

```bash
# 1. Clone repository
git clone https://github.com/yourusername/iot-health-monitoring.git
cd iot-health-monitoring

# 2. Create Python environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Docker services
docker-compose up -d

# 5. Verify services
docker-compose ps
```

### Running Services

```bash
# Terminal 1: Live Validator
cd Python_Scripts
python live_sensor_validator.py

# Terminal 2: Data Writer
python grafana_data_writer.py

# Terminal 3: Monitor
python system_mqtt_stream.py

# Browser: Grafana
http://localhost:3000
```

---

## Docker Deployment

### Production Docker Compose

```yaml
version: '3.8'

services:
  mosquitto:
    image: eclipse-mosquitto:latest
    container_name: mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    networks:
      - iot-network

  influxdb:
    image: influxdb:2.6-alpine
    container_name: influxdb
    ports:
      - "8086:8086"
    environment:
      INFLUXDB_DB: telegraf
      INFLUXDB_ADMIN_USER: admin
      INFLUXDB_ADMIN_PASSWORD: ${INFLUXDB_PASSWORD:-admin}
      INFLUXDB_HTTP_AUTH_ENABLED: "true"
    volumes:
      - ./influxdb/data:/var/lib/influxdb2
    networks:
      - iot-network

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_INSTALL_PLUGINS: grafana-mqtt-datasource
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/data:/var/lib/grafana
    depends_on:
      - influxdb
    networks:
      - iot-network

  validator:
    build:
      context: .
      dockerfile: Dockerfile.validator
    container_name: validator
    environment:
      MQTT_HOST: mosquitto
      MQTT_PORT: 1883
      LOG_LEVEL: INFO
    depends_on:
      - mosquitto
    networks:
      - iot-network

  data-writer:
    build:
      context: .
      dockerfile: Dockerfile.writer
    container_name: data-writer
    environment:
      MQTT_HOST: mosquitto
      INFLUXDB_HOST: influxdb
      INFLUXDB_TOKEN: ${INFLUXDB_TOKEN}
    depends_on:
      - mosquitto
      - influxdb
    networks:
      - iot-network

networks:
  iot-network:
    driver: bridge
```

### Build Custom Images

```dockerfile
# Dockerfile.validator
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY Python_Scripts/live_sensor_validator.py .
COPY Python_Scripts/models ./models

CMD ["python", "live_sensor_validator.py"]
```

### Deploy

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## AWS Deployment

### EC2 Setup

```bash
# 1. Launch EC2 Instance
# AMI: Ubuntu 22.04 LTS
# Instance Type: t3.medium
# Security Group: Allow 1883, 8086, 3000

# 2. Connect to instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose

# 4. Clone repository
git clone https://github.com/yourusername/iot-health-monitoring.git
cd iot-health-monitoring

# 5. Set environment variables
cat > .env << EOF
MQTT_HOST=your-ec2-ip
INFLUXDB_PASSWORD=your-password
GRAFANA_PASSWORD=your-password
EOF

# 6. Deploy
docker-compose up -d
```

### RDS for InfluxDB

```bash
# Option: Use AWS Timestream instead of InfluxDB
# Faster, serverless, auto-scaling

# Update Python scripts to use Timestream
# from boto3 import client as boto3_client
# timestream = boto3_client('timestream-write')
```

### Load Balancer

```bash
# Use AWS Application Load Balancer
# Target Group: Grafana (port 3000)
# Listener: HTTP 80 → HTTPS 443
```

---

## Kubernetes Deployment

### Install Tools
```bash
# kubectl
curl -LO "https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl"

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Deploy on Kubernetes

```bash
# 1. Create namespace
kubectl create namespace iot-monitoring

# 2. Create secrets
kubectl create secret generic mqtt-credentials \
  --from-literal=password='your-password' \
  -n iot-monitoring

# 3. Deploy Helm chart
helm install iot-monitoring ./helm-chart -n iot-monitoring

# 4. Verify
kubectl get pods -n iot-monitoring
kubectl get svc -n iot-monitoring
```

### Helm Chart Structure

```
helm-chart/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── statefulset.yaml
```

---

## CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -r requirements.txt
      - run: pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker images
        run: docker-compose build
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker tag iot-validator:latest ${{ secrets.DOCKER_USERNAME }}/iot-validator:latest
          docker push ${{ secrets.DOCKER_USERNAME }}/iot-validator:latest
```

---

## Monitoring & Maintenance

### Health Checks

```bash
# MQTT Broker
docker exec mosquitto mosquitto_pub -t test -m "health"

# InfluxDB
curl -X GET "http://localhost:8086/api/v2/health"

# Grafana
curl -X GET "http://localhost:3000/api/health"
```

### Backup

```bash
# Backup InfluxDB
docker exec influxdb influxd backup /backups

# Backup Grafana
docker cp grafana:/var/lib/grafana ./grafana-backup

# Upload to S3
aws s3 cp grafana-backup s3://your-bucket/backups/
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose build --no-cache

# Deploy with zero-downtime
docker-compose up -d --no-deps --build validator data-writer
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Containers won't start | Check logs: `docker-compose logs` |
| MQTT connection refused | Verify `MQTT_HOST` in `.env` |
| Data not in Grafana | Check validator: `docker logs validator` |
| High memory usage | Increase InfluxDB retention |

---

## Security Checklist

- [ ] Change default passwords
- [ ] Enable MQTT authentication
- [ ] Use TLS for MQTT (port 8883)
- [ ] Enable InfluxDB authentication
- [ ] Setup Grafana RBAC
- [ ] Configure firewall rules
- [ ] Enable Docker container security
- [ ] Regular security updates

---

**Need help?** Check [README.md](README.md) or open an issue on GitHub.
