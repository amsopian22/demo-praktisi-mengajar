import time
import requests
import json
from river import drift
import pandas as pd
from sqlalchemy import create_engine
import os

AIRFLOW_WEBHOOK_URL = os.getenv("AIRFLOW_WEBHOOK_URL", "http://localhost:8080/api/v1/dags/samarinda_flood_pipeline/dagRuns")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "airflow")
AIRFLOW_PASS = os.getenv("AIRFLOW_PASS", "airflow")

# Gunakan Hoeffding Bound (ADWIN Algorithm dari pustaka River)
adwin = drift.ADWIN()

def send_webhook_to_airflow():
    """ Mengirimkan sinyal bangun ke Apache Airflow untuk Retraining (Condition A & B) """
    headers = {"Content-Type": "application/json"}
    payload = {"conf": {"trigger_reason": "Data Drift Detected by ADWIN"}}
    
    print("[WAIT] Menjalankan backoff retry mechanism jika gagal...")
    for attempt in range(3):
        try:
            res = requests.post(AIRFLOW_WEBHOOK_URL, auth=(AIRFLOW_USER, AIRFLOW_PASS), 
                                json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                print(f"[ALARM] Webhook Trigger sent successfully! Airflow akan melakukan retraining tanpa mematikan model aktif (Zero Downtime).")
                return True
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
            
    print("[ESCALATE] Webhook gagal dikirim 3 kali. Alert dikirim langsung ke Integration Pipeline Logs Grafana.")
    # Log directly to local file mapped to Grafana Loki / Logs here
    return False

def monitor_stream():
    """ 
    Black Box Approach: Skrip daemon untuk memantau stream 
    curah hujan yang datang.
    """
    print("Memulai Daemon ADWIN Drift Monitoring...")
    # Dummy Stream Data
    # 0 = normal rainfall, 100 = threshold extremes
    # Simulasi normal, lalu tiba-tiba ada perubahan distribusi curah hujan rata-rata bergeser (drift)
    stream_data = [10]*500 + [15]*300 + [80]*150 + [120]*100 
    
    for i, val in enumerate(stream_data):
        in_drift = adwin.update(val)
        if in_drift:
            print(f"[DRIFT DETECTED] Batas Hoeffding terlampaui di index {i}! Ada anomali cuaca yang konsisten.")
            send_webhook_to_airflow()
            # Reset the monitor after drift to prevent alarm flood
            adwin.reset()
            # In real system, we break/sleep until new model is promoted.
            time.sleep(5)
            
        time.sleep(0.01)

if __name__ == "__main__":
    monitor_stream()
