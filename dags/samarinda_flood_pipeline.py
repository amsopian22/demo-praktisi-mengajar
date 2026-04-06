from airflow import DAG
from airflow.models.baseoperator import chain
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago
import datetime

# Konfigurasi DAG dengan prinsip LocalExecutor dan Zero Dependency issues (Docker)
default_args = {
    'owner': 'samarinda_city',
    'start_date': days_ago(1),
    'retries': 3,
    'retry_delay': datetime.timedelta(minutes=5),
    'depends_on_past': False,
}

# The MLOps Infinity Loop DAG (Ingest -> ELT Transform -> Train/Infer)
with DAG(
    'samarinda_flood_pipeline',
    default_args=default_args,
    description='Automated orchestration of weather ingestion, DBT transformation, and XGBoost tuning',
    schedule_interval='@hourly',
    catchup=False,
    max_active_runs=1,
) as dag:

    # ==============================
    # 1. Ingestion Phase (Open-Meteo)
    # ==============================
    # Asynchronous ingestion with 10-30s throttling.
    # Default: Incremental (Daily). Use --initial via manual run for 5-year data.
    task_ingest_open_meteo = BashOperator(
        task_id='ingest_weather_data',
        bash_command='python /opt/airflow/scripts/ingest_open_meteo.py --start-date {{ ds }} --end-date {{ (execution_date + macros.timedelta(days=1)).strftime("%Y-%m-%d") }} --throttle 15'
    )

    # ==============================
    # 2. ELT Transformation (dbt & PostgreSQL)
    # ==============================
    # Relying on dbt for PostgreSQL 16 ACID compliance and aggregations
    task_elt_silver = BashOperator(
        task_id='dbt_transform_silver',
        bash_command='python /opt/airflow/scripts/run_elt_pipeline.py --layer silver'
    )
    
    task_elt_gold = BashOperator(
        task_id='dbt_transform_gold',
        bash_command='python /opt/airflow/scripts/run_elt_pipeline.py --layer gold'
    )

    # ==============================
    # 3. Model Training / Retraining (XGBoost)
    # ==============================
    # This also acts as the webhook target for ADWIN drift detection.
    # Chronological splitting and MLflow logging are handled inside the script.
    task_train_models = BashOperator(
        task_id='train_comparison_models',
        bash_command='python /opt/airflow/scripts/train_comparison_models.py'
    )

    # ==============================
    # 4. Inference Phase (AI Prediction)
    # ==============================
    # Generate geospatial flood probabilities using the newest production model.
    task_predict_flood = BashOperator(
        task_id='predict_flood_geospatial',
        bash_command='python /opt/airflow/scripts/predict_flood.py'
    )
    
    # 5. Refresh Observability / Alert
    # A generic notification step upon successful deployment of a newer model.
    task_update_grafana_observability = BashOperator(
        task_id='grafana_risk_map_notifier',
        bash_command='echo "Airflow pipeline completed. Dashboard Demo Praktisi Mengajar data reflects newest geospatial probabilities."'
    )

    # DAG Flow & Hierarchical Dependency
    # Ingest -> (Silver -> Gold) -> Train -> Predict -> Observability Notification
    chain(
        task_ingest_open_meteo,
        task_elt_silver,
        task_elt_gold,
        task_train_models,
        task_predict_flood,
        task_update_grafana_observability
    )

# Catatan: Airflow webhook listener untuk ADWIN di set via REST API (Endpoint /api/v1/dags/...)
