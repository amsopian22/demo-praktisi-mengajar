{{
  config(
    materialized='view',
    tags=['silver']
  )
}}

SELECT
    kelurahan_id,
    kelurahan_nama,
    latitude,
    longitude,
    elevation_meters,
    timestamp::TIMESTAMP as timestamp,
    rainfall_mm,
    soil_moisture
FROM {{ source('internal_db', 'bronze_weather_raw') }}
WHERE timestamp IS NOT NULL
