import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
from sqlalchemy import create_engine, text
import os
import mlflow
import datetime

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="Samarinda Flood Command Center", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Glassmorphism & High-Tech UI
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: radial-gradient(circle, #1a1c24 0%, #0e1117 100%);
    }
    [data-testid="stSidebar"] {
        background-color: rgba(20, 26, 40, 0.95);
        border-right: 1px solid #30363d;
    }
    .stMetric {
        background: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00d4ff;
    }
    .stDataFrame {
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    h1, h2, h3 {
        color: #00d4ff !important;
        font-family: 'Inter', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

DB_URL = os.getenv("DB_URL", "postgresql://airflow:airflow@postgres:5432/airflow")
MLFLOW_URL = os.getenv("MLFLOW_TRACKING_URI", "http://192.168.147.4:5000")

# --- DATA LOADING FUNCTIONS ---
def load_data():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="postgres", 
            database="airflow", 
            user="airflow", 
            password="airflow"
        )
        query = "SELECT * FROM gold_flood_predictions"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def load_weather_data():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="postgres", 
            database="airflow", 
            user="airflow", 
            password="airflow"
        )
        query = """
        SELECT 
            latitude, longitude, elevation_meters as elev_m, 
            rainfall_rolling_3d as rain_3d, 
            rainfall_rolling_7d as rain_7d,
            timestamp as last_observation
        FROM gold_features_ml
        ORDER BY timestamp DESC
        LIMIT 15;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def load_mlflow_metrics():
    try:
        mlflow.set_tracking_uri(MLFLOW_URL)
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name("Samarinda_Flood_Comparison")
        if experiment:
            runs = client.search_runs([experiment.experiment_id])
            metrics_list = []
            for run in runs:
                metrics_list.append({
                    "Model": run.data.params.get("model_architecture", run.info.run_name),
                    "F1-Score": run.data.metrics.get("f1_score", 0),
                    "AUC": run.data.metrics.get("auc", 0),
                    "Recall": run.data.metrics.get("recall", 0),
                    "Precision": run.data.metrics.get("precision", 0),
                    "Train Time (s)": run.data.metrics.get("training_time", 0)
                })
            return pd.DataFrame(metrics_list)
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🛰️ Command Controls")
st.sidebar.markdown("Memonitor intelijen banjir Samarinda secara real-time.")

architectures = ["XGBoost", "Random Forest", "Logistic Regression", "Neural Network"]
selected_model = st.sidebar.selectbox("🎯 Target Intelligence Model:", architectures, index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🕹️ Simulation Engine")
sim_rain = st.sidebar.slider("Curah Hujan (3 Hari)", 0, 300, 100)
sim_elev = st.sidebar.slider("Ketinggian Wilayah (m)", 2, 50, 10)

def simulate_risk(rain, elev):
    risk = (rain / 300) * 0.8 + (1 - (elev / 50)) * 0.2
    return min(max(risk, 0), 1)

current_risk = simulate_risk(sim_rain, sim_elev)
st.sidebar.metric("Simulated Risk Chance", f"{current_risk:.2%}", delta=f"{current_risk-0.5:.2%}")

if current_risk > 0.7:
    st.sidebar.error("🚨 CRITICAL RISK DETECTED")
elif current_risk > 0.4:
    st.sidebar.warning("⚡ ELEVATED ALERT")
else:
    st.sidebar.success("⚓ NORMAL CONDITIONS")

# --- MAIN DASHBOARD LAYOUT ---
st.title("🏯 Samarinda Flood Command Center")
st.caption("Advanced AI Geospatial Intelligence Platform • Demo Praktisi Mengajar")

tab1, tab2 = st.tabs(["🏙️ Risk Intelligence (3D Map)", "📉 Model Performance Lab"])

# Shared metrics
metrics_df = load_mlflow_metrics()

with tab1:
    col_map, col_details = st.columns([3, 1])
    
    with col_map:
        st.subheader(f"🌐 2D Interactive Risk Intelligence - {selected_model}")
        df_all = load_data()
        
        if not df_all.empty:
            if 'model_name' in df_all.columns:
                df = df_all[df_all['model_name'] == selected_model]
            else:
                df = df_all
                
            if not df.empty:
                # Add calculated columns for tooltip
                df = df.copy()
                df['risk_pct'] = (df['risk_probability'] * 100).round(2).astype(str) + "%"
                df['status_label'] = df['is_high_risk'].apply(lambda x: "⚠️ BAHAYA" if x == 1 else "✅ AMAN")

                # Modern 2D Visual with ScatterplotLayer
                view_state = pdk.ViewState(
                    latitude=-0.49,
                    longitude=117.14,
                    zoom=11.5,
                    pitch=0,
                    bearing=0
                )

                layer = pdk.Layer(
                    "ScatterplotLayer",
                    df,
                    get_position=["longitude", "latitude"],
                    get_radius=300,
                    get_fill_color=[
                        "risk_probability * 255", 
                        "(1 - risk_probability) * 200", 
                        "255 * (1-risk_probability)", 
                        200
                    ],
                    pickable=True,
                    opacity=0.8,
                    stroked=True,
                    filled=True,
                    radius_min_pixels=8,
                    radius_max_pixels=100,
                )

                st.pydeck_chart(pdk.Deck(
                    layers=[layer],
                    initial_view_state=view_state,
                    map_style="mapbox://styles/mapbox/dark-v11",
                    tooltip={
                        "html": "<b>Model:</b> {model_name}<br/>"
                                "<b>Probabilitas:</b> {risk_pct}<br/>"
                                "<b>Status:</b> {status_label}",
                        "style": {"color": "white", "backgroundColor": "#0e1117", "border": "1px solid #30363d"}
                    }
                ))
            else:
                st.warning("Data model ini belum siap di database.")
        else:
            st.info("Sistem sedang menunggu aliran data pertama dari Airflow...")

    with col_details:
        st.subheader("📊 Statistics")
        if not df_all.empty and not metrics_df.empty:
            model_info = metrics_df[metrics_df["Model"] == selected_model]
            if not model_info.empty:
                st.metric("Model F1-Score", f"{model_info['F1-Score'].values[0]:.4f}")
                st.metric("Training Speed", f"{model_info['Train Time (s)'].values[0]:.2f}s")
            
            high_risk_count = len(df[df['is_high_risk'] == 1])
            st.metric("Wilayah Waspada", high_risk_count, delta="Real-time")

    # Recent Weather Table
    st.markdown("---")
    st.subheader("🛰️ Observasi Cuaca Terbaru (Samarinda)")
    rain_df = load_weather_data()
    if not rain_df.empty:
        st.dataframe(rain_df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("🧪 Battle of Models: Deep Evaluation")
    
    if not metrics_df.empty:
        col_table, col_radar = st.columns([1, 1.2])
        
        with col_table:
            st.markdown("#### Detailed Comparison Matrix")
            st.dataframe(metrics_df.sort_values("F1-Score", ascending=False), height=400, hide_index=True)
            
            st.info("""
                **Interpretasi:**
                - **F1-Score**: Keseimbangan Precision dan Recall (Sangat penting untuk banjir).
                - **AUC**: Kemampuan model membedakan antara banjir vs tidak banjir.
                - **Recall**: Seberapa baik model menangkap SEMUA kejadian banjir (menghindari False Negatives).
            """)

        with col_radar:
            st.markdown("#### Radar Performance Profile")
            # radar chart preparation
            categories = ['F1-Score', 'AUC', 'Precision', 'Recall', 'Train Time (Inv)']
            
            fig = go.Figure()
            
            # Normalize train time for radar (smaller time is better)
            max_time = metrics_df['Train Time (s)'].max() if metrics_df['Train Time (s)'].max() > 0 else 1
            metrics_df['Train Time (Inv)'] = 1 - (metrics_df['Train Time (s)'] / max_time) + 0.1
            metrics_df['Train Time (Inv)'] = metrics_df['Train Time (Inv)'] / metrics_df['Train Time (Inv)'].max()

            for i, row in metrics_df.iterrows():
                fig.add_trace(go.Scatterpolar(
                    r=[row['F1-Score'], row['AUC'], row['Precision'], row['Recall'], row['Train Time (Inv)']],
                    theta=categories,
                    fill='toself',
                    name=row['Model']
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1]),
                    bgcolor="rgba(0,0,0,0)"
                ),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white")
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Menunggu training pertama selesai untuk menampilkan evaluasi model.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #555;'>Samarinda Predictive Intelligence System • Developed for Demo Praktisi Mengajar 2026</div>", unsafe_allow_html=True)
