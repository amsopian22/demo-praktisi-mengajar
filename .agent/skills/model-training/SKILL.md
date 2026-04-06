---
name: samarinda-model-training
description: Executes predictive model training using XGBoost algorithms with Chronological Splitting, and tracks experiments centrally including hyperparameters, F1-Score, and AUC metrics via MLflow for the Samarinda pipeline.
---

# Samarinda Model Training & Tracking (XGBoost & MLflow)

## 🎯 Objective
Train the predictive machine learning models using the XGBoost algorithm to generate granular geospatial risk scores for Samarinda, and comprehensively track the AI artifacts lifecycle using MLflow.

## 📋 Instructions
When tasked with model training or retraining for the Samarinda Predictive Flood Intelligence project, adhere strictly to the following procedures:
1. **Data Ingestion for Training**: Pull the ML-ready feature data directly from the Gold Layer in PostgreSQL.
2. **Chronological Splitting**: You must apply Chronological Splitting during model training. This prevents temporal data leakage and ensures that real-world simulation predictions remain 100% realistic.
3. **Algorithm Specifics**: Utilize XGBoost (Gradient Boosting Ensembles) to process non-linear feature interactions between extreme weather (e.g., rainfall > 100mm) and geographical complexities.
4. **Automated Experiment Tracking**: Ensure MLflow persistently records all hyperparameter configurations and crucial evaluation metrics, specifically AUC and F1-Score, in a single centralized dashboard.
5. **Model Lifecycle Promotion**: Register the models centrally. Promote algorithms from Staging to Production environments safely; if necessary, be prepared to execute rollbacks in seconds.

## 🛠️ Provided Scripts (Black Box Approach)
Do not read the entire ML source code or write training loops from scratch. Use the provided execution scripts:
- Always run `python scripts/train_xgboost.py --help` first to understand the specific parameters for the Samarinda pipeline.
- Execute the script to initiate the training, evaluation, and MLflow registration process.

## 🌳 Decision Tree: Evaluation & Retraining
If anomalies occur or specific evaluation conditions are met during training, use the following logic:

- **Condition A:** If the new model's evaluation metrics (F1-Score or AUC) are lower than the current model in the Production environment:
  - **Action:** Halt the promotion. Keep the new model in the Staging or Archived state within MLflow. Do NOT deploy to Production.

- **Condition B:** If a retraining is triggered autonomously by the Airflow webhook due to Data Drift detected by ADWIN:
  - **Action:** Execute the training pipeline to pull the latest PostgreSQL data and rerun MLflow to deploy a new XGBoost model, ensuring zero downtime.

- **Condition C:** If the MLflow tracking server is unresponsive or fails to log artifacts:
  - **Action:** Verify the local Docker container running MLflow. Ensure the system is adhering to the Lean Urban Intelligence constraints and has not exceeded the 8GB RAM limit.
