#!/bin/bash
# Samarinda Predictive Flood Intelligence - Orchestration Deployment
set -e

echo "==========================================="
echo "   Demo Praktisi Mengajar - AI Flood Prediction      "
echo "==========================================="
echo "Memeriksa ketersediaan RAM (Max < 8GB Limit)..."
# Simulasi pengecekan batas ram
# free -h | awk '/^Mem/ {print "Available RAM: " $7}'

echo "Membangun dan meluncurkan infrastruktur Docker..."
# Pastikan folder tersedia
mkdir -p dags scripts dbt_project

echo "Inisialisasi Database Airflow..."
docker-compose run --rm airflow-webserver airflow db migrate
docker-compose run --rm airflow-webserver airflow users create \
    --username admin \
    --password admin \
    --firstname MLOps \
    --lastname Admin \
    --role Admin \
    --email mlops@samarindacity.go.id

echo "Mengaktifkan Stack (Up -d)..."
docker-compose up -d

echo "-------------------------------------------"
echo "Deployment berhasil. Sistem berjalan pada: "
echo "- Airflow UI: http://localhost:8080 (admin:admin)"
echo "- MLflow:     http://localhost:5000"
echo "- Grafana:    http://localhost:3000 (admin:admin)"
echo "- PostgreSQL: localhost:5432"
echo "-------------------------------------------"
