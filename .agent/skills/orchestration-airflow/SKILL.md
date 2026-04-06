---
name: samarinda-orchestration-airflow
description: Orchestrates the MLOps Infinity Loop for the Samarinda Predictive Flood Intelligence system using Apache Airflow with LocalExecutor, completely isolated within Docker containers to ensure zero dependency issues while keeping memory consumption strictly under 8GB RAM.
---

# Samarinda Pipeline Orchestration (Apache Airflow & Docker)

## 🎯 Objective
Act as the central conductor for the entire Samarinda flood prediction ecosystem. You must orchestrate the flow of data across the MLOps Infinity Loop (Ingest -> Transform -> Train -> Deploy) using Apache Airflow, ensuring the entire infrastructure runs securely within Docker containers (Zero Dependency).

## 📋 Instructions
When configuring, deploying, or troubleshooting the orchestration layer, follow these foundational rules:
1. **Docker Containerization**: All components must run inside a soundproof Docker container ecosystem. This eliminates "It works on my machine" issues and ensures identical environments between development and production.
2. **LocalExecutor Configuration**: You MUST configure Apache Airflow to use `LocalExecutor`. This allows for highly efficient task parallelism without the need for heavy external message brokers (like Celery/RabbitMQ).
3. **Lean Urban Intelligence (RAM Limit)**: Maintain strict adherence to the Micro-Resource Footprint pillar. The entire orchestration and execution environment must operate persistently using less than 8GB of RAM.
4. **End-to-End Orchestration**: Ensure your DAGs (Directed Acyclic Graphs) correctly dictate when and how data flows: pulling API hourly (Open-Meteo), triggering hierarchical dbt runs (PostgreSQL), and running automated inference scripts without human intervention.

## 🛠️ Provided Scripts (Black Box Approach)
Do not attempt to write Dockerfiles or Airflow DAGs from scratch unless explicitly requested. Use the provided infrastructure scripts:
- Always run `bash scripts/deploy_orchestration.sh --help` or `docker-compose config` first to inspect the container environment.
- Use the script flags to start, stop, or restart the Airflow webserver and scheduler safely.

## 🌳 Decision Tree: Infrastructure & Pipeline Handling
If you encounter orchestration bottlenecks or container issues, apply the following logic:

- **Condition A:** If system memory (RAM) usage approaches or exceeds the 8GB limit during parallel DAG executions:
  - **Action:** Dynamically reduce task parallelism (concurrency limits) within Airflow's configuration. Prioritize the ELT transformation tasks over historical model retraining to free up memory.

- **Condition B:** If a task in the pipeline (e.g., dbt ELT or XGBoost training) fails:
  - **Action:** Halt downstream tasks to prevent cascading errors. Send a failure alert to the monitoring system, and rely on PostgreSQL's ACID compliance (Rollback) before allowing manual or automated DAG retries from the point of failure.

- **Condition C:** If there is a "port conflict" or the Docker daemon fails to start the Airflow webserver:
  - **Action:** Inspect local occupied ports and remap the Airflow UI to an available port (e.g., 8081 instead of 8080) without modifying the internal container network structure.
