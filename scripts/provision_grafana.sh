#!/bin/bash
# Skrip Penyediaan (Provisioning) Dasbor Grafana Samarinda
set -e

echo "[GRAFANA] Menyiapkan Datasource PostgreSQL ke dalam Grafana..."
# Dalam arsitektur asli, JSON config biasanya di map via docker volume ke 
# /etc/grafana/provisioning/datasources/postgres.yml

cat <<EOF > postgres_datasource.yml
apiVersion: 1
datasources:
  - name: PostgreSQL-MLOps
    type: postgres
    url: postgres:5432
    database: airflow
    user: airflow
    secureJsonData:
      password: airflow
    jsonData:
      sslmode: disable
      postgresVersion: 16
EOF

echo "[GRAFANA] Menyiapkan Interactive Risk Map (Dashboard JSON)..."
# Menghasilkan struktur dasar JSON dashboard.
cat <<EOF > flood_risk_dashboard.json
{
  "title": "Demo Praktisi Mengajar - Flood Risk",
  "panels": [
    {
      "type": "geomap",
      "title": "Interactive Risk Map (Berdasarkan Gold Layer)",
      "gridPos": {"h": 12, "w": 18, "x": 0, "y": 0},
      "targets": [
        {
          "refId": "A",
          "rawSql": "SELECT latitude, longitude, proxy_target_flood AS risk_score FROM gold_features_ml WHERE proxy_target_flood = 1",
          "format": "table"
        }
      ]
    },
    {
      "type": "gauge",
      "title": "Hardware Memory Utilization (< 8GB)",
      "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
    }
  ]
}
EOF

echo "[GRAFANA] Persiapan Grafana Selesai. Masukkan file ke folder provisioning untuk auto-load."
