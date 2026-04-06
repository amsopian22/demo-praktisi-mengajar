---
name: samarinda-drift-detection
description: Monitors weather data streams for Data Drift using the ADWIN algorithm (Hoeffding Bound) and autonomously triggers retraining workflows via Airflow webhooks to ensure zero downtime for the Samarinda pipeline.
---

# Samarinda Drift Detection & Self-Healing (ADWIN)

## 🎯 Objective
Act as the autonomous self-defense mechanism for the AI models. You must continuously monitor the incoming weather data distribution (e.g., rainfall metrics) using the ADWIN algorithm. If a significant climate shift occurs (Data Drift), you are responsible for initiating the automated retraining sequence.

## 📋 Instructions
When tasked with monitoring data drift or handling model decay, follow these steps:
1. **Continuous Monitoring**: Analyze the incoming data stream from the PostgreSQL feature store against historical baselines.
2. **Hoeffding Bound Evaluation**: Use the ADWIN algorithm to determine if the data distribution has statistically breached the new reality limits (Hoeffding Bound).
3. **Wake-up Signal (Webhook)**: If drift is detected, you MUST instantly send a critical webhook alarm to Apache Airflow.
4. **Zero Downtime Verification**: Ensure that the retraining sequence (pulling latest Postgres data and rerunning MLflow) does not interrupt the current active model until the new XGBoost model is safely promoted.

## 🛠️ Provided Scripts (Black Box Approach)
Do not write the ADWIN statistical logic manually. Use the provided drift monitoring script:
- Run `python scripts/monitor_drift_adwin.py --help` to view configuration parameters for thresholds.
- Execute the script as a background daemon within its designated container.

## 🌳 Decision Tree: Drift Handling & Alarms
Follow this logic when evaluating data streams:

- **Condition A:** If the ADWIN algorithm detects a breach of the Hoeffding Bound (Data Drift confirmed):
  - **Action:** Fire the "Wake-up Signal" webhook to the Airflow API. Log the exact timestamp and drifted feature (e.g., rainfall) for the Data Engineering team.

- **Condition B:** If the webhook to Airflow fails to send (e.g., network timeout):
  - **Action:** Implement an exponential backoff retry mechanism up to 3 times. If it still fails, escalate by sending an alert directly to the integration pipeline logs.

- **Condition C:** If a minor variance occurs but does not breach the Hoeffding Bound:
  - **Action:** Do nothing. Continue monitoring. Do not trigger retraining to save the 8GB RAM computational resources.
