# syntax=docker/dockerfile:1.7
FROM python:3.15-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Built with the repository root as context (see infra/docker/compose.yaml) so the
# shared library can be installed. Dependencies first for layer caching.
COPY libs/python/claims-common /opt/claims-common
COPY services/claims-api/requirements.txt .
RUN pip install -r requirements.txt "/opt/claims-common[otel,redis]"

COPY services/claims-api/ .

# Run as an unprivileged user; the app only needs read access to /app.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
    && chmod +x entrypoint.sh \
    && chown -R app:app /app
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).status == 200 else 1)"

ENTRYPOINT ["./entrypoint.sh"]
