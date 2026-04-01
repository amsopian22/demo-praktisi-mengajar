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

_default_mlflow_host = "mlflow"
try:
    _mlflow_ip = socket.gethostbyname(_default_mlflow_host)
    _default_url = f"http://{_mlflow_ip}:5000"
except Exception:
    _default_url = "http://localhost:5000"

DB_HOST = os.getenv("DB_HOST", "postgres")
MLFLOW_URL = os.getenv("MLFLOW_TRACKING_URI", _default_url)

if "mlflow:5000" in MLFLOW_URL:
    try:
        _mlflow_ip = socket.gethostbyname("mlflow")
        MLFLOW_URL = MLFLOW_URL.replace("mlflow:5000", f"{_mlflow_ip}:5000")
    except Exception:
        pass

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
    
    # Mencari model dengan stage 'Production'
    model_name = "Samarinda_Flood_XGBoost"
    # Catatan: Di script train_xgboost.py kita belum secara eksplisit set alias/stage 'Production' lewat API.
    # Namun sesuai best practice, kita ambil model terbaru yang paling oke.
    
    try:
        # Load model dari run terbaru yang sukses (Staging/Production)
        # Cara termudah: ambil path model dari experiment terbaru
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("Samarinda_Flood_Prediction")
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["metrics.f1_score DESC"],
            max_results=1
        )
        
        if not runs:
            print("[!] Tidak ada model yang ditemukan di MLflow. Harap jalankan training terlebih dahulu.")
            return

        run_id = runs[0].info.run_id
        model_uri = f"runs:/{run_id}/model"
        print(f"[*] Memuat model dari Run ID: {run_id}")
        
        # Load as pyfunc for easy inference
        model = mlflow.pyfunc.load_model(model_uri)
        
        # Ambil Best Threshold if available in metrics
        best_threshold = runs[0].data.metrics.get("optimal_threshold", 0.5)
        print(f"[*] Menggunakan Threshold Optimal: {best_threshold}")

    except Exception as e:
        print(f"[ERROR] Gagal memuat model dari MLflow: {e}")
        return

    # Load Fitur
    print("[*] Mengambil fitur terbaru dari database...")
    features_df = get_latest_features()
    
    if features_df.empty:
        print("[!] Tidak ada data fitur untuk diprediksi.")
        return

    # Siapkan input (pastikan urutan kolom sesuai training)
    features_list = ["elevation_meters", "rainfall_rolling_3d", "rainfall_rolling_7d", "rainfall_rolling_14d"]
    X = features_df[features_list]

    # Prediksi Probabilitas
    print("[*] Menjalankan inferensi AI...")
    probs = model.predict(X) 
    # Catatan: Jika dilog sebagai XGBoost model, predict() mungkin langsung biner jika tidak hati-hati.
    # Tapi mlflow.pyfunc biasanya mengembalikan ndarray probabilitas untuk klasifikasi biner.
    
    # Simpan hasil
    features_df['risk_probability'] = probs
    features_df['prediction_threshold'] = best_threshold
    features_df['is_high_risk'] = (probs >= best_threshold).astype(int)
    features_df['predicted_at'] = datetime.datetime.now()

    # Save to PostgreSQL (Upsert Mode)
    engine = create_engine(DB_URL)
    print(f"[*] Menyimpan {len(features_df)} prediksi ke tabel gold_flood_predictions...")
    
    with engine.begin() as conn:
        # Buat tabel jika belum ada
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS gold_flood_predictions (
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                risk_probability DOUBLE PRECISION,
                prediction_threshold DOUBLE PRECISION,
                is_high_risk INTEGER,
                predicted_at TIMESTAMP,
                last_data_timestamp TIMESTAMP,
                PRIMARY KEY (latitude, longitude)
            )
        """))
        
        # Insert/Update Data
        for _, row in features_df.iterrows():
            upsert_query = text("""
                INSERT INTO gold_flood_predictions 
                (latitude, longitude, risk_probability, prediction_threshold, is_high_risk, predicted_at, last_data_timestamp)
                VALUES (:lat, :lon, :prob, :th, :risk, :now, :ts)
                ON CONFLICT (latitude, longitude) DO UPDATE SET
                    risk_probability = EXCLUDED.risk_probability,
                    is_high_risk = EXCLUDED.is_high_risk,
                    predicted_at = EXCLUDED.predicted_at,
                    last_data_timestamp = EXCLUDED.last_data_timestamp;
            """)
            conn.execute(upsert_query, {
                'lat': row['latitude'],
                'lon': row['longitude'],
                'prob': row['risk_probability'],
                'th': row['prediction_threshold'],
                'risk': row['is_high_risk'],
                'now': row['predicted_at'],
                'ts': row['timestamp']
            })

    print("[SUCCESS] Prediksi risiko banjir telah diperbarui di Database.")

if __name__ == "__main__":
    predict_and_save()
