# syntax=docker/dockerfile:1.7
# Build context: repository root (needs libs/python/claims-common).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY libs/python/claims-common /opt/claims-common
COPY services/ml-service/requirements.txt .
RUN pip install -r requirements.txt "/opt/claims-common[otel,redis]"

COPY services/ml-service/ .

# Bake synthetic data + trained models into the image so the container is
# self-contained and reproducible (seeding into Mongo happens at startup).
RUN python -m data_gen.generate_data && python -m ml.train_models

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && chmod +x entrypoint.sh \
    && chown -R app:app /app
USER 10001:10001

EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=3s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health/live', timeout=2).status == 200 else 1)"

ENTRYPOINT ["./entrypoint.sh"]
