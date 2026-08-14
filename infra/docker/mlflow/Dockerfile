FROM ghcr.io/mlflow/mlflow:v2.22.0

RUN python -m pip install --no-cache-dir psycopg2-binary==2.9.10

COPY infra/docker/mlflow/healthcheck.py /opt/mlflow/healthcheck.py
