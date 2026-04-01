import os
import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.pyfunc
from sqlalchemy import create_engine, text
import datetime

# Konfigurasi Database (Port 5432 di dalam Docker network)
DB_URL = "postgresql://airflow:airflow@postgres:5432/airflow"

import socket

import socket
try:
    # Resolusi IP dinamis untuk memintas proteksi Host Header MLflow
    MLFLOW_IP = socket.gethostbyname("mlflow")
    MLFLOW_URL = f"http://{MLFLOW_IP}:5000"
except Exception:
    MLFLOW_URL = os.getenv("MLFLOW_URL", "http://localhost:5000")

def get_latest_features():
    """
    Mengambil fitur cuaca dan geospasial terbaru (jam terakhir) untuk setiap lokasi.
    """
    engine = create_engine(DB_URL)
    query = """
    WITH latest_data AS (
        SELECT 
            *,
            ROW_NUMBER() OVER (PARTITION BY latitude, longitude ORDER BY timestamp DESC) as rn
        FROM gold_features_ml
    )
    SELECT 
        latitude, 
        longitude, 
        elevation_meters, 
        rainfall_rolling_3d, 
        rainfall_rolling_7d, 
        rainfall_rolling_14d,
        timestamp
    FROM latest_data
    WHERE rn = 1
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=result.keys())
    return df

def predict_and_save():
    print(f"[*] Menghubungkan ke MLflow di {MLFLOW_URL}...")
    mlflow.set_tracking_uri(MLFLOW_URL)
    
    # Ambil Fitur Terlebih Dahulu
    print("[*] Mengambil fitur terbaru dari database...")
    features_df = get_latest_features()
    
    if features_df.empty:
        print("[!] Tidak ada data fitur untuk diprediksi.")
        return

    features_list = ["elevation_meters", "rainfall_rolling_3d", "rainfall_rolling_7d", "rainfall_rolling_14d"]
    X = features_df[features_list]

    # Mencari model-model dari eksperimen perbandingan
    try:
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("Samarinda_Flood_Comparison")
        if not experiment:
            print("[!] Eksperimen 'Samarinda_Flood_Comparison' tidak ditemukan.")
            return

        # Ambil run terbaru
        all_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=20 # Ambil cukup banyak untuk mencari 4 arsitektur berbeda
        )
        
        # Filter untuk mendapatkan satu run terbaru per arsitektur
        architectures = ["XGBoost", "Random Forest", "Logistic Regression", "Neural Network"]
        latest_runs = {}
        for run in all_runs:
            arch = run.data.params.get("model_architecture")
            if arch in architectures and arch not in latest_runs:
                latest_runs[arch] = run
            if len(latest_runs) == len(architectures):
                break

        if not latest_runs:
            print("[!] Tidak ada model perbandingan yang ditemukan di MLflow.")
            return

        # Database Engine
        engine = create_engine(DB_URL)
        
        # Prepare Table (Update Schema)
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS gold_flood_predictions")) # Reset table for new schema
            conn.execute(text("""
                CREATE TABLE gold_flood_predictions (
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    model_name VARCHAR(50),
                    risk_probability DOUBLE PRECISION,
                    prediction_threshold DOUBLE PRECISION,
                    is_high_risk INTEGER,
                    predicted_at TIMESTAMP,
                    last_data_timestamp TIMESTAMP,
                    PRIMARY KEY (latitude, longitude, model_name)
                )
            """))

        # Jalankan Inferensi untuk setiap model yang ditemukan
        for arch_name, run in latest_runs.items():
            run_id = run.info.run_id
            print(f"[*] Melakukan inferensi dengan model: {arch_name} (Run: {run_id})")
            
            model_uri = f"runs:/{run_id}/model"
            model = mlflow.pyfunc.load_model(model_uri)
            best_threshold = run.data.metrics.get("optimal_threshold", 0.5)
            
            # Predict
            probs = model.predict(X)
            
            # Prepare Dataframe for this specific model
            model_df = features_df.copy()
            model_df['model_name'] = arch_name
            model_df['risk_probability'] = probs
            model_df['prediction_threshold'] = best_threshold
            model_df['is_high_risk'] = (probs >= best_threshold).astype(int)
            model_df['predicted_at'] = datetime.datetime.now()

            # Insert to DB
            print(f"[*] Menyimpan {len(model_df)} prediksi untuk {arch_name}...")
            with engine.begin() as conn:
                for _, row in model_df.iterrows():
                    insert_query = text("""
                        INSERT INTO gold_flood_predictions 
                        (latitude, longitude, model_name, risk_probability, prediction_threshold, is_high_risk, predicted_at, last_data_timestamp)
                        VALUES (:lat, :lon, :model, :prob, :th, :risk, :now, :ts)
                    """)
                    conn.execute(insert_query, {
                        'lat': row['latitude'],
                        'lon': row['longitude'],
                        'model': row['model_name'],
                        'prob': row['risk_probability'],
                        'th': row['prediction_threshold'],
                        'risk': row['is_high_risk'],
                        'now': row['predicted_at'],
                        'ts': row['timestamp']
                    })

    except Exception as e:
        print(f"[ERROR] Gagal menjalankan multi-model inference: {e}")
        return

    print("[SUCCESS] Seluruh model perbandingan telah diperbarui di Database.")

    print("[SUCCESS] Prediksi risiko banjir telah diperbarui di Database.")

if __name__ == "__main__":
    predict_and_save()
