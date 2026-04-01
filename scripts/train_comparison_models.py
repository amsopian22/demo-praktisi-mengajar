import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score, roc_auc_score, recall_score
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import mlflow.xgboost
from sqlalchemy import create_engine, text
import time
import os
import sys
import socket

# Configuration
MLFLOW_URL = os.getenv("MLFLOW_TRACKING_URI", "http://192.168.147.4:5000")

if "mlflow:5000" in MLFLOW_URL:
    try:
        _mlflow_ip = socket.gethostbyname("mlflow")
        MLFLOW_URL = MLFLOW_URL.replace("mlflow:5000", f"{_mlflow_ip}:5000")
    except Exception:
        pass

def load_gold_data():
    try:
        db_url = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        engine = create_engine(db_url)
        query = "SELECT * FROM gold_features_ml WHERE proxy_target_flood IS NOT NULL ORDER BY timestamp ASC"
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=result.keys())
        return df
    except Exception as e:
        print(f"Warning: No database data found ({e}). Using dummy data for demo purposes.")
        dates = pd.date_range('2024-01-01', periods=1000)
        df = pd.DataFrame({
            "timestamp": dates,
            "elevation_meters": np.random.randint(2, 40, size=1000),
            "rainfall_rolling_3d": np.random.uniform(0, 200, size=1000),
            "rainfall_rolling_7d": np.random.uniform(20, 300, size=1000),
            "rainfall_rolling_14d": np.random.uniform(50, 400, size=1000),
        })
        df['proxy_target_flood'] = np.where(
            ((df['elevation_meters'] < 10) & (df['rainfall_rolling_3d'] > 100)) |
            ((df['elevation_meters'] >= 10) & (df['elevation_meters'] <= 30) & (df['rainfall_rolling_3d'] > 150)) |
            ((df['elevation_meters'] > 30) & (df['rainfall_rolling_3d'] > 200)),
            1, 0
        )
        return df

def train_multiple_models():
    df = load_gold_data()
    df = df.sort_values("timestamp")
    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]
    
    features = ["elevation_meters", "rainfall_rolling_3d", "rainfall_rolling_7d", "rainfall_rolling_14d"]
    target = "proxy_target_flood"
    
    X_train, y_train = train_df[features], train_df[target]
    X_test, y_test = test_df[features], test_df[target]

    # Imbalance calculation
    count_neg = (y_train == 0).sum()
    count_pos = (y_train == 1).sum()
    pos_weight = count_neg / count_pos if count_pos > 0 else 1.0

    print(f"Dataset Size: {len(df)} rows. Positive/Negative: {count_pos}/{count_neg}")
    
    mlflow.set_tracking_uri(MLFLOW_URL)
    mlflow.set_experiment("Samarinda_Flood_Comparison")
    
    models = {
        "XGBoost": xgb.XGBClassifier(scale_pos_weight=pos_weight, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42),
        "Neural Network": MLPClassifier(hidden_layer_sizes=(100,), max_iter=500, random_state=42)
    }

    best_f1 = 0
    best_model_name = ""

    for name, model in models.items():
        with mlflow.start_run(run_name=name):
            print(f"Training {name}...")
            start_time = time.time()
            model.fit(X_train, y_train)
            train_time = time.time() - start_time
            
            # Predict
            preds_proba = None
            if hasattr(model, "predict_proba"):
                preds_proba = model.predict_proba(X_test)[:, 1]
            else:
                preds_proba = model.decision_function(X_test)
                # Normalize decision function if needed or just use binary for metrics
                
            # Choose threshold based on F1 tuning
            best_threshold = 0.5
            max_f1 = 0
            for th in np.arange(0.1, 0.9, 0.05):
                temp_preds = (preds_proba >= th).astype(int)
                temp_f1 = f1_score(y_test, temp_preds, zero_division=0)
                if temp_f1 > max_f1:
                    max_f1 = temp_f1
                    best_threshold = th
            
            final_preds = (preds_proba >= best_threshold).astype(int)
            f1 = f1_score(y_test, final_preds, zero_division=0)
            auc = roc_auc_score(y_test, preds_proba) if len(np.unique(y_test)) > 1 else 0.5
            recall = recall_score(y_test, final_preds, zero_division=0)

            # Metadata Logging
            mlflow.log_param("model_architecture", name)
            mlflow.log_metrics({
                "f1_score": f1,
                "auc": auc,
                "recall": recall,
                "training_time": train_time,
                "optimal_threshold": best_threshold
            })
            
            if name == "XGBoost":
                mlflow.xgboost.log_model(model, "model")
            else:
                mlflow.sklearn.log_model(model, "model")
            
            print(f"[{name}] F1: {f1:.3f} | AUC: {auc:.3f} | Time: {train_time:.4f}s")
            
            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name

    print(f"\nTraining Complete. Best Model: {best_model_name} with F1-Score: {best_f1:.3f}")

if __name__ == "__main__":
    train_multiple_models()
