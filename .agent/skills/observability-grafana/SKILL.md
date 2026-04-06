---
name: samarinda-observability-grafana
description: Manages near real-time observability in Grafana for Command Center 112, visualizing geospatial flood risks from PostgreSQL's Gold Layer, tracking pipeline logs, and monitoring 8GB RAM server health.
---

# Samarinda System Observability (Grafana)

## 🎯 Objective
Serve as the "Eyes of the System." You must ensure that the Grafana dashboards correctly and continuously consume the final probability outputs from the PostgreSQL Gold Layer, presenting instant visual intelligence for 112 emergency operators.

## 📋 Instructions
When managing the observability layer, strictly ensure the following components are functioning:
1. **Interactive Risk Map**: Verify that Grafana is securely connected to the Gold Layer database to pull granular risk scores (0-100%) and display them spatially per Kecamatan.
2. **Infrastructure Health**: Continuously monitor the server's hardware utilization. Since the system follows the Lean Urban Intelligence pillar, you must track memory usage (ensuring it stays below the 8GB Max RAM limit) and live latency.
3. **Integration Pipeline Logs**: Ensure data flow anomalies from Airflow and dbt are visible in the centralized log panel for Data Engineer visibility.

## 🛠️ Provided Scripts (Black Box Approach)
Use the provided provisioning scripts to manage Grafana dashboards:
- Run `bash scripts/provision_grafana.sh --help` to inspect dashboard deployment options.
- Use the script to reload data sources or reset dashboard panels without manually editing JSON models.

## 🌳 Decision Tree: Dashboard Troubleshooting
If the Command Center 112 reports dashboard issues, use this logic:

- **Condition A:** If the Interactive Risk Map fails to display the latest probabilities:
  - **Action:** Verify the connection to the PostgreSQL 16 Gold Layer. If the database is locked due to an active dbt ELT transaction, wait for the `COMMIT` to finish before refreshing Grafana.

- **Condition B:** If the Server Health monitor shows Memory Utilization exceeding 85% of the 8GB limit:
  - **Action:** Log a critical infrastructure warning. Advise operators that the Airflow LocalExecutor might be processing a heavy ML training batch.

- **Condition C:** If Integration Pipeline Logs are empty:
  - **Action:** Check the Docker volume mappings for Airflow logs. Ensure Grafana has the correct read permissions for the containerized log directories.
