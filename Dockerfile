FROM apache/airflow:2.8.1-python3.10
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         build-essential \
         gcc \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# Salin requirements dan instal dependensi Python
COPY requirements.txt /opt/airflow/requirements.txt
RUN pip install --no-cache-dir --upgrade pip

# Instal prasyarat build
RUN pip install --no-cache-dir numpy==1.26.4 Cython

# Baru instal sisa requirements dengan no-build-isolation
RUN pip install --no-cache-dir --no-build-isolation -r /opt/airflow/requirements.txt
