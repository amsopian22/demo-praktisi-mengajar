import asyncio
import aiohttp
import pandas as pd
import numpy as np
import argparse
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import sys
import time

# Konfigurasi Database PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "airflow")
DB_PASS = os.getenv("DB_PASS", "airflow")
DB_NAME = os.getenv("DB_NAME", "airflow")

# List 59 Kelurahan Samarinda (Simulasi koordinat)
np.random.seed(42)
lats = np.random.uniform(-0.54, -0.45, 59)
lons = np.random.uniform(117.08, 117.20, 59)
kelurahan_list = [
    {
        "id": i+1,
        "nama": f"Kelurahan_{i+1}",
        "lat": round(lats[i], 4),
        "lon": round(lons[i], 4)
    } for i in range(59)
]

async def fetch_weather(session, url, kel_id, kel_nama):
    try:
        async with session.get(url) as response:
            if response.status == 429:
                # Jika kena rate limit, tunggu lebih lama
                wait_time = 10
                print(f"[Warning] Rate Limit (429) hit for {kel_nama}. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await fetch_weather(session, url, kel_id, kel_nama)
            
            if response.status == 400:
                # Sering terjadi jika tanggal archive belum mencukupi (hari ini)
                return None
                
            response.raise_for_status()
            data = await response.json()
            return {"kel_id": kel_id, "kel_nama": kel_nama, "data": data}
    except Exception as e:
        print(f"Error fetching data for {kel_nama}: {e}")
        return None

def get_date_chunks(start_date, end_date, chunk_days=90):
    """Membagi rentang tanggal menjadi potongan kecil untuk menghindari load besar"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    chunks = []
    curr = start
    while curr < end:
        chunk_end = min(curr + timedelta(days=chunk_days), end)
        chunks.append((curr.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        curr = chunk_end + timedelta(days=1)
    return chunks

async def process_chunk(start_date, end_date, throttle_sec=10):
    results = []
    print(f"Processing chunk: {start_date} to {end_date}...")
    
    async with aiohttp.ClientSession() as session:
        # Kita batasi pararelisme agar tidak memicu rate limit global
        # Memproses per 10 lokasi sekaligus, lalu istirahat singkat
        batch_size = 10
        for i in range(0, len(kelurahan_list), batch_size):
            batch = kelurahan_list[i : i + batch_size]
            tasks = []
            for kel in batch:
                url = f"https://archive-api.open-meteo.com/v1/archive?latitude={kel['lat']}&longitude={kel['lon']}&start_date={start_date}&end_date={end_date}&hourly=rain,soil_moisture_0_to_7cm&timezone=Asia%2FSingapore"
                tasks.append(fetch_weather(session, url, kel["id"], kel["nama"]))
            
            responses = await asyncio.gather(*tasks)
            
            for res in responses:
                if res and "data" in res:
                    data = res["data"]
                    elevation = data.get("elevation", 0)
                    hourly = data.get("hourly", {})
                    times = hourly.get("time", [])
                    rain = hourly.get("rain", [])
                    soil_m = hourly.get("soil_moisture_0_to_7cm", [])
                    
                    for idx in range(len(times)):
                        results.append({
                            "kelurahan_id": res["kel_id"],
                            "kelurahan_nama": res["kel_nama"],
                            "latitude": next(k['lat'] for k in kelurahan_list if k['id'] == res["kel_id"]),
                            "longitude": next(k['lon'] for k in kelurahan_list if k['id'] == res["kel_id"]),
                            "elevation_meters": elevation,
                            "timestamp": times[idx],
                            "rainfall_mm": rain[idx],
                            "soil_moisture": soil_m[idx]
                        })
            
            # THROTTLING (Sesuai permintaan USER: 10-30 detik)
            if i + batch_size < len(kelurahan_list):
                print(f"  Throttling for {throttle_sec}s between location batches...")
                await asyncio.sleep(throttle_sec)
                
    return results

def save_to_postgres(results):
    if not results:
        return
    
    db_url = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    engine = create_engine(db_url)
    
    print(f"Saving {len(results)} rows to PostgreSQL Bronze Layer (Direct Bulk Insert)...")
    
    try:
        with engine.begin() as conn:
            # Pastikan tabel bronze ada
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bronze_weather_raw (
                    kelurahan_id INTEGER,
                    kelurahan_nama TEXT,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    elevation_meters DOUBLE PRECISION,
                    timestamp TIMESTAMP,
                    rainfall_mm DOUBLE PRECISION,
                    soil_moisture DOUBLE PRECISION,
                    PRIMARY KEY (kelurahan_id, timestamp)
                )
            """))
            
            # Gunakan direct bulk insert dengan ON CONFLICT
            # results adalah list of dictionaries yang sesuai dengan parameter query
            insert_query = text("""
                INSERT INTO bronze_weather_raw 
                (kelurahan_id, kelurahan_nama, latitude, longitude, elevation_meters, timestamp, rainfall_mm, soil_moisture)
                VALUES 
                (:kelurahan_id, :kelurahan_nama, :latitude, :longitude, :elevation_meters, :timestamp, :rainfall_mm, :soil_moisture)
                ON CONFLICT (kelurahan_id, timestamp) DO NOTHING
            """)
            
            # SQLAlchemy 1.4+ secara otomatis menangani list of dicts sebagai executemany
            conn.execute(insert_query, results)
            
        print("Data successfully committed.")
    except Exception as e:
        print(f"Database error during save: {e}")


        # Kita tidak re-raise agar main loop tetap berjalan untuk chunk berikutnya


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", help="Format YYYY-MM-DD")
    parser.add_argument("--end-date", help="Format YYYY-MM-DD")
    parser.add_argument("--initial", action="store_true", help="Fetch 5 years of history")
    parser.add_argument("--throttle", type=int, default=15, help="Throttle seconds between batches")
    args = parser.parse_args()

    start_date = args.start_date
    end_date = args.end_date

    if args.initial:
        # Hitung 5 tahun ke belakang dari hari ini
        end_dt = datetime.now() - timedelta(days=2) # Archive biasanya butuh jeda 2 hari
        start_dt = end_dt - timedelta(days=5*365)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")
        print(f"MODE INITIAL: Menarik sejarah 5 tahun ({start_date} s/d {end_date})")

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required if not using --initial")
        sys.exit(1)

    # Bagi menjadi chunks (misal per 180 hari agar tidak terlalu banyak request ke server)
    chunks = get_date_chunks(start_date, end_date, chunk_days=180)
    
    for c_start, c_end in chunks:
        results = await process_chunk(c_start, c_end, throttle_sec=args.throttle)
        save_to_postgres(results)
        if len(chunks) > 1:
            print(f"Waiting 30s between time chunks to be safe...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
