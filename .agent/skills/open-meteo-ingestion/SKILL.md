---
name: samarinda-weather-ingestion
description: Executes asynchronous batch ingestion of high-precision weather data from Open-Meteo API for 59 Kelurahan in Samarinda, pulling historical and forecast data without overloading local network bandwidth.
---

# Samarinda Weather Data Ingestion (Open-Meteo)

## 🎯 Objective
Handle the extraction of high-precision weather data from the Open-Meteo API for 59 Kelurahan (sub-districts) in Samarinda. The extraction must be executed asynchronously to prevent overloading the local government's network bandwidth.

## 📋 Instructions
When tasked with ingesting weather data for the Samarinda Predictive Flood Intelligence project, follow these guidelines:
1. **Target Verification**: Ensure the data request covers the specified 59 Kelurahan.
2. **Asynchronous Batching**: Execute API calls asynchronously. Do not use synchronous loops that block the network.
3. **Data Scope**: Extract both historical data and future weather forecasts.
4. **Bronze Layer Destination**: Dump the extracted raw data "as-is" (unfiltered and pure) directly into the Bronze Layer of the PostgreSQL 16 database. 

## 🛠️ Provided Scripts (Black Box Approach)
Do not attempt to write the ingestion logic from scratch or read the entire Python source code. Use the provided automation script:
- Always run `python scripts/ingest_open_meteo.py --help` first to understand the available parameters.
- Execute the script using the appropriate flags to initiate the asynchronous batching process.

## 🌳 Decision Tree: Error Handling & Optimization
If you encounter issues during the ingestion process, follow this decision tree to resolve them:

- **Condition A:** If the Open-Meteo API returns a `429 Too Many Requests` (Rate Limit) error:
  - **Action:** Apply an exponential backoff strategy and reduce the asynchronous batch size by 50% before retrying.
  
- **Condition B:** If a network timeout occurs during extraction:
  - **Action:** The local network bandwidth might be overloaded. Pause the execution for 60 seconds, then resume the batch from the last failed Kelurahan.

- **Condition C:** If the extracted data fails to load into the database:
  - **Action:** Verify that the PostgreSQL 16 database is actively running within its Docker container and ensure the credentials are correct. Do not attempt to transform the data; it must remain in its pure "as-is" state for the Bronze Layer.
