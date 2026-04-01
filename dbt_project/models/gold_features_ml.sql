{{
  config(
    materialized='table',
    tags=['gold']
  )
}}

WITH base AS (
    SELECT
        kelurahan_id,
        kelurahan_nama,
        latitude,
        longitude,
        elevation_meters,
        timestamp,
        rainfall_mm,
        soil_moisture,
        -- Rolling 3d (72 hours)
        SUM(rainfall_mm) OVER (PARTITION BY kelurahan_id ORDER BY timestamp ROWS BETWEEN 71 PRECEDING AND CURRENT ROW) as rainfall_rolling_3d,
        -- Rolling 7d (168 hours)
        SUM(rainfall_mm) OVER (PARTITION BY kelurahan_id ORDER BY timestamp ROWS BETWEEN 167 PRECEDING AND CURRENT ROW) as rainfall_rolling_7d,
        -- Rolling 14d (336 hours)
        SUM(rainfall_mm) OVER (PARTITION BY kelurahan_id ORDER BY timestamp ROWS BETWEEN 335 PRECEDING AND CURRENT ROW) as rainfall_rolling_14d
    FROM {{ ref('stg_weather_data') }}
),
target_logic AS (
    SELECT
        *,
        CASE 
            WHEN elevation_meters < 10 AND rainfall_rolling_3d > 100 THEN 1
            WHEN elevation_meters >= 10 AND elevation_meters <= 30 AND rainfall_rolling_3d > 150 THEN 1
            WHEN elevation_meters > 30 AND rainfall_rolling_3d > 200 THEN 1
            ELSE 0 
        END as proxy_target_flood
    FROM base
)
SELECT * FROM target_logic
