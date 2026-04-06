---
name: samarinda-elt-postgres-dbt
description: Executes rapid data transformations within PostgreSQL 16 using dbt (Data Build Tool) following the ELT paradigm [1, 4]. Processes raw weather data through Bronze, Silver, and Gold layers to build an ML-ready feature store for the Samarinda predictive flood models [3, 4].
---

# Samarinda ELT & Database Transformation (dbt & PostgreSQL 16)

## 🎯 Objective
Manage the rapid transformation of raw weather data into an ML-ready Feature Store [3, 4]. You must utilize the ELT (Extract, Load, Transform) paradigm, executing transformations directly inside the PostgreSQL 16 database using dbt to drastically reduce time-to-insight [1, 2]. 

## 📋 Instructions
When orchestrating the data transformation pipeline, strictly adhere to the following multi-layered data architecture:
1. **Bronze Layer Verification**: Acknowledge that the raw data extracted from Open-Meteo has been dumped "as-is" (unfiltered) into the Bronze Layer [4]. Do not mutate this layer.
2. **Silver Layer (dbt Macro)**: Execute dbt models designed for the Silver Layer to perform autonomous data cleaning, data type standardization, and the handling of missing/null values [4]. 
3. **Gold Layer (ML-Ready)**: Execute dbt models for the Gold Layer to create ready-to-serve feature tables [4]. This includes calculating rolling-window aggregations that connect directly to the XGBoost prediction algorithms [4, 7].
4. **ACID Compliance Assurance**: Rely on PostgreSQL 16's ACID transaction compliance. Ensure all transformations are atomic; if an error occurs mid-transformation, a full `ROLLBACK` must be executed so no partial data is stored, otherwise execute a `COMMIT` [3].

## 🛠️ Provided Scripts (Black Box Approach)
Do not attempt to write SQL queries or dbt models from scratch [8]. Use the provided automation scripts within the workspace:
- Always run `dbt run --help` or `python scripts/run_elt_pipeline.py --help` first to inspect available execution parameters [8].
- Execute the specific dbt tags for the required layers (e.g., `dbt run --select tag:silver`).

## 🌳 Decision Tree: Error Handling & Integrity Validation
Use the following decision tree to handle anomalies during the ELT process [9]:

- **Condition A:** If the `dbt run` process encounters schema inconsistencies (e.g., unexpected column types from the Bronze Layer):
  - **Action:** Halt the transformation pipeline. Trigger a `ROLLBACK` via PostgreSQL to ensure operational integrity, then log the schema mismatch error for Data Engineer review [3, 10].

- **Condition B:** If null values exceed the acceptable threshold during Silver Layer execution:
  - **Action:** Utilize predefined dbt macros to apply statistical imputation (e.g., mean/median replacement for rainfall metrics) before proceeding to the Gold Layer [4].

- **Condition C:** If the database latency spikes or memory usage nears the 8GB limit of the local infrastructure:
  - **Action:** Pause the transformation batch, allowing the LocalExecutor to clear memory overhead, and retry the transformation of the Gold Layer incrementally [10-12].
