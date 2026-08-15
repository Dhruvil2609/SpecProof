FROM python:3.11.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/specproof-venv
RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.8.11
WORKDIR /workspace
COPY . .
RUN uv sync --frozen --no-dev --group runtime
ENV PATH="/opt/specproof-venv/bin:$PATH"
EXPOSE 8010
CMD ["uvicorn", "specproof_measurement_service.api:app", "--host", "0.0.0.0", "--port", "8010"]
