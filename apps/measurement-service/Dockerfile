FROM python:3.11.13-slim-bookworm
LABEL org.opencontainers.image.title="SpecProof Measurement Service" \
      org.opencontainers.image.vendor="SpecProof" \
      org.opencontainers.image.source="https://github.com/Dhruvil2609/SpecProof"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/specproof-venv
RUN apt-get update \
    && apt-get install --yes --no-install-recommends curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.8.11 \
    && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin specproof
WORKDIR /workspace
COPY . .
RUN uv sync --frozen --no-dev --group runtime
ENV PATH="/opt/specproof-venv/bin:$PATH"
EXPOSE 8010
USER 10001
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8010/health || exit 1
CMD ["uvicorn", "specproof_measurement_service.api:app", "--host", "0.0.0.0", "--port", "8010"]
