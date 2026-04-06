---
name: praktisi-mengajar-demo
description: Panduan implementasi end-to-end sistem Intelijen Banjir Samarinda untuk program Praktisi Mengajar. Mencakup ingest data cuaca, rekayasa fitur dengan dbt, pelatihan model XGBoost/MLflow, orkestrasi Airflow, dan dashboard Streamlit.
---

# 🌊 Samarinda Flood Intelligence - Praktisi Mengajar Guide

Skill ini dirancang untuk memandu implementasi sistem deteksi dini banjir Samarinda secara langkah demi langkah, mulai dari pengambilan data mentah hingga visualisasi real-time. Dokumentasi ini berfungsi sebagai referensi teknis lengkap bagi pengembang dan pengajar.

## 🏗️ Arsitektur Sistem (Stack Teknologi)

Sistem ini mengimplementasikan siklus hidup Data Science penuh (EDSL) dengan efisiensi tinggi:
- **Ingestion**: Python `asyncio` + Open-Meteo API (Mengambil data cuaca historis & forecast).
- **Storage & Transformation**: PostgreSQL 16 + **dbt** (Mengelola arsitektur medali: Bronze, Silver, Gold).
- **Machine Learning**: **XGBoost**, Random Forest, LR, NN + **MLflow** untuk pelacakan eksperimen.
- **Orchestration**: **Apache Airflow 2.8+** (Menjadwalkan pipeline dari hulu ke hilir).
- **Monitoring & Visualization**: **Grafana** (Health monitoring) & **Streamlit** (Interactive Risk Map).

---

## 🚀 Langkah-Langkah Implementasi Lengkap

### 1. Inisialisasi Infrastruktur (Docker)
Menjalankan seluruh stack layanan dalam satu perintah menggunakan Docker Compose untuk memastikan portabilitas (Clone & Play).
- **Komponen**: Database, Airflow, MLflow, Grafana, Streamlit.
- **Perintah Utama**:
  ```bash
  docker-compose up -d
  ```
- **Penjelasan Teknis**: Docker memastikan tidak ada konflik dependensi (misal: versi Python atau library SQL) antar modul sistem.

### 2. Penarikan Data (Batch Ingestion)
Mengambil data mentah (raw data) cuaca dari Open-Meteo untuk 59 kelurahan di Samarinda.
- **Teknologi**: `aiohttp` & `asyncio` untuk pengambilan paralel.
- **Penjelasan Teknis**: Mengambil data selama 5-10 tahun membutuhkan kecepatan. Dengan asinkronus, kita bisa menarik jutaan baris data dalam hitungan menit tanpa membebani memori laptop.
- **Perintah**:
  ```bash
  docker exec -it demo-prediksi-praktisi-mengajar-airflow-scheduler-1 python /opt/airflow/scripts/ingest_open_meteo.py --initial
  ```

### 3. Rekayasa Fitur (ELT dengan dbt)
Mengubah data mentah menjadi format yang bisa dipahami oleh AI.
- **Konsep Medallion**:
    - **Bronze**: Data tabel mentah.
    - **Silver**: Pembersihan data (handling nulls, deduplikasi).
    - **Gold (Feature Store)**: Pembuatan fitur "pintar" seperti akumulasi hujan 3 jam, 6 jam, dan pergerakan rata-rata curah hujan.
- **Penjelasan Teknis**: dbt memungkinkan kita menulis transformasi data menggunakan SQL murni namun tetap memiliki fitur "software engineering" seperti testing dan version control.
- **Perintah**:
  ```bash
  docker exec -it demo-prediksi-praktisi-mengajar-airflow-scheduler-1 python /opt/airflow/scripts/run_elt_pipeline.py --layer gold
  ```

### 4. Pelatihan & Evaluasi AI (Battle of Models)
Melatih beberapa arsitektur model AI untuk mencari prediksi yang paling akurat.
- **Primary Model**: **XGBoost** (Extreme Gradient Boosting).
- **MLflow Tracking**: Mencatat setiap percobaan, parameter, dan hasil (F1-Score, AUC).
- **Penjelasan Teknis**: Kita menggunakan *Chronological Splitting*. Artinya, kita melatih model dengan data masa lalu dan mengujinya dengan data yang paling baru di masa depan untuk mensimulasikan kondisi dunia nyata.
- **Perintah**:
  ```bash
  docker exec -it demo-prediksi-praktisi-mengajar-airflow-scheduler-1 python /opt/airflow/scripts/train_comparison_models.py
  ```

### 5. Deployment & Visualisasi (Operationalizing)
Menampilkan hasil prediksi ke pengguna akhir (Wali Kota / BPBD).
- **Streamlit Dashboard**: Peta risiko 2D interaktif.
- **Grafana Dashboard**: Visualisasi teknis untuk Command Center 112.
- **Penjelasan Teknis**: Prediksi probabilitas dari model AI disimpan kembali ke PostgreSQL (lapisan Gold), yang kemudian dibaca secara real-time oleh dashboard.

---

## 🧠 Penjelasan Teknis Utama

### 1. Mengapa Menggunakan Feature Store?
Dalam banjir, penyebabnya bukan hanya hujan saat ini, tapi akumulasi hujan beberapa jam sebelumnya. Fitur-fitur seperti `rain_sum_3h` atau `rain_rolling_avg` dibuat di tingkat database agar inferensi (prediksi) berjalan sangat cepat.

### 2. Drift Detection (ADWIN)
Sistem ini memantau perubahan distribusi data cuaca. Jika pola cuaca tiba-tiba berubah secara drastis (misal: siklon ekstrem yang belum pernah didata sebelumnya), algoritma ADWIN akan mendeteksi "Drift" dan secara otomatis membangunkan Airflow untuk melatih ulang (retraining) model AI.

### 3. Optimasi Resource (< 8GB RAM)
Untuk menjalankan Airflow, MLflow, Database, dan AI di satu laptop, kita menggunakan:
- **Sampling**: Melatih AI pada 100.000 data terpilih alih-alih seluruh 2,6 juta baris.
- **Isolated Containers**: Membatasi penggunaan memori per kontainer jika diperlukan via Docker.

---

## 💻 Bedah Kode Penting (Deep Dive)

Berikut adalah beberapa bagian kode krusial yang perlu dipahami oleh pengajar dan mahasiswa:

### 1. Ingestion Asinkronus (`asyncio` & `aiohttp`)
Digunakan untuk menarik data dari ribuan titik koordinat secara paralel tanpa menunggu satu per satu selesai.
```python
# scripts/ingest_open_meteo.py
async with aiohttp.ClientSession() as session:
    tasks = []
    for kel in batch:
        tasks.append(fetch_weather(session, url, kel["id"], kel["nama"]))
    
    # Menjalankan semua task secara paralel
    responses = await asyncio.gather(*tasks)
```
*   **Poin Edukasi**: Jelaskan perbedaan antara pemrograman sinkronus (antre) vs asinkronus (simultan). Tanpa `asyncio`, penarikan data 5 tahun bisa memakan waktu berjam-jam, namun dengan asinkronus hanya memakan waktu beberapa menit.

### 2. Integritas Data SQL (`ON CONFLICT`)
Memastikan database tetap bersih meskipun skrip dijalankan berkali-kali untuk rentang tanggal yang sama.
```sql
-- scripts/ingest_open_meteo.py
INSERT INTO bronze_weather_raw 
(...) VALUES (...)
ON CONFLICT (kelurahan_id, timestamp) DO NOTHING;
```
*   **Poin Edukasi**: Jelaskan konsep **Idempotency**. Skrip harus bisa dijalankan berulang kali tanpa merusak atau menduplikasi data yang sudah ada di database.

### 3. Strategi Pelatihan AI (Chronological Splitting)
Mencegah *Data Leakage* dengan membagi data berdasarkan waktu, bukan secara acak.
```python
# scripts/train_comparison_models.py
df = df.sort_values("timestamp")
split_index = int(len(df) * 0.8)
train_df = df.iloc[:split_index] # 80% masa lalu
test_df = df.iloc[split_index:]  # 20% masa depan
```
*   **Poin Edukasi**: Dalam prediksi cuaca/banjir, kita tidak boleh memberikan "contekkan" berupa data masa depan ke dalam model saat pelatihan. Mahasiswa harus paham mengapa metode `train_test_split` acak biasa seringkali memberikan hasil akurasi yang "palsu" atau terlalu tinggi.

### 4. Penanganan Ketidakseimbangan Data (`scale_pos_weight`)
Banjir adalah kejadian langka (kelas minoritas). Model cenderung mengabaikan banjir jika tidak dikonfigurasi.
```python
# scripts/train_comparison_models.py
count_neg = (y_train == 0).sum()
count_pos = (y_train == 1).sum()
pos_weight = count_neg / count_pos

model = xgb.XGBClassifier(scale_pos_weight=pos_weight)
```
*   **Poin Edukasi**: Jelaskan mengapa **F1-Score** lebih penting daripada **Accuracy** pada kasus banjir. `scale_pos_weight` memberikan "pemberat" lebih besar pada kesalahan prediksi banjir agar AI lebih sensitif terhadap risiko besar.

### 5. Deteksi Drift (Algoritma ADWIN)
Memantau integritas data secara real-time dan memicu tindakan otomatis jika pola cuaca berubah drastis.
```python
# scripts/monitor_drift_adwin.py
adwin = drift.ADWIN()

for i, val in enumerate(stream_data):
    in_drift = adwin.update(val)
    if in_drift:
        send_webhook_to_airflow()
```
*   **Poin Edukasi**: Jelaskan bahwa AI tidak statis. Konsep **Data Drift** (perubahan distribusi data) sangat krusial dalam MLOps. Pengajar bisa menjelaskan bagaimana `Hoeffding Bound` dalam ADWIN bekerja untuk membedakan antara "noise" biasa dengan perubahan tren yang nyata.

---

## 🛠️ Perintah & Endpoint Penting

- **Peta Risiko (Streamlit)**: `http://localhost:8501`
- **Laboratorium AI (MLflow)**: `http://localhost:5001`
- **Orkestrasi (Airflow)**: `http://localhost:8080`
- **Gudang Data (pgAdmin)**: `http://localhost:5050`

---
**Skill ini siap digunakan untuk memandu proses pengembangan dan troubleshooting sistem Samarinda Flood Intelligence secara mendalam.**
