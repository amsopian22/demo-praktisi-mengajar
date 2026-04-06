---
name: code-review
description: "Pakar audit kode untuk mendeteksi bug, mengoptimalkan performa, dan memvalidasi integritas integrasi antar komponen (Meteo-API, PostgreSQL, MLflow, Airflow, Streamlit)."
---

# Panduan Code Review: Intelijen Banjir Samarinda 🏯

Gunakan keahlian ini untuk melakukan audit sistematis terhadap basis kode proyek. Fokus utama adalah pada **Reliabilitas**, **Keamanan Data**, dan **Efisiensi Integrasi**.

## 🎯 Tujuan Utama
1.  **Deteksi Bug**: Menemukan kesalahan logika, *race conditions*, dan kebocoran memori.
2.  **Optimasi Performa**: Mengurangi latensi kueri SQL dan mempercepat proses inferensi AI.
3.  **Evaluasi Integrasi**: Memastikan aliran data antar Docker container (API/DB) berjalan tanpa kegagalan koneksi.
4.  **Rekomendasi Efektif**: Memberikan solusi kode yang mengikuti prinsip *Clean Code* dan *DRY (Don't Repeat Yourself)*.

## 🔍 Checklist Audit Teknis

### 1. Logika Python (ML & Ingestion)
- **Error Handling**: Setiap fungsi pemanggilan API atau koneksi eksternal WAJIB memiliki blok `try-except` yang detail.
- **Data Integrity**: Validasi tipe data (DataFrames) sebelum melakukan operasi agregasi atau pelatihan model.
- **MLflow Logging**: Pastikan setiap *training run* mencatat metrik (`f1`, `auc`, `recall`) dan parameter (`model_architecture`) dengan nama yang standar.

### 2. Efisiensi Database (PostgreSQL)
- **Connection Management**: Gunakan `engine.begin()` atau penutupan koneksi secara eksplisit untuk mencegah *connection leak*.
- **SQL Optimization**: Hindari kueri `SELECT *` pada tabel yang besar; hanya ambil kolom yang diperlukan.
- **Upsert Logic**: Gunakan `ON CONFLICT (PRIMARY KEY) DO UPDATE` untuk mencegah duplikasi data spasial.

### 3. Dashboard Streamlit (UI/UX & State)
- **State Optimization**: Gunakan `st.cache_data` atau `st.cache_resource` untuk fungsi penarikan data dari database yang lambat.
- **UI Responsiveness**: Pastikan elemen interaktif (dropdown, slider) memberikan umpan balik visual yang cepat.
- **Consistency**: Pastikan nama model yang ditampilkan sama dengan nama model yang tercatat di MLflow.

### 4. Integrasi & API (Docker Environment)
- **Environment Variables**: Audit penggunaan `os.getenv()` untuk URI layanan (DB_URL, MLFLOW_URL). Pastikan memiliki nilai *fallback* yang aman.
- **Internal Networking**: Gunakan nama layanan Docker (cth: `http://mlflow:5000`) daripada IP statis untuk fleksibilitas skalabilitas.

## 🛠️ Langkah Menghasilkan Rekomendasi
Saat melakukan review, selalu berikan output dalam format berikut:
1.  **Temuan (Issue)**: Lokasi baris kode dan jenis masalah (Bug/Security/Performance).
2.  **Dampak (Impact)**: Apa yang akan terjadi jika tidak diperbaiki.
3.  **Kode Rekomendasi (Solution)**: Potongan kode perbaikan yang siap pasang.
4.  **Rasional (Rationale)**: Alasan mengapa kode baru lebih baik.

---
**Penting**: Selalu prioritaskan keamanan data dan stabilitas infrastruktur yang beroperasi pada RAM terbatas (< 8GB).