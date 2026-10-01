# ==============================================================================
# HERMES BRAIN COMMAND DECK - PRODUCTION DOCKERFILE
# ==============================================================================

# Stage 1: Build Dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final Production Runtime
FROM python:3.11-slim AS runner

LABEL maintainer="TheHappyHermit"
LABEL description="Hermes Brain — Unified Neuro-Cognitive Architecture & Command Deck"

WORKDIR /app

# Install minimal runtime system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy repository source code
COPY . /app/

# Create persistent storage directories
RUN mkdir -p /data /config /data/brain /data/personal-organizer

ENV PYTHONUNBUFFERED=1 \
    HERMES_HOME=/data \
    HERMES_DATA_DIR=/data \
    ORGANIZER_DB_PATH=/data/personal-organizer/organizer.db \
    BRAIN_DB_PATH=/data/brain/brain.db \
    EXPERIENCE_DB_PATH=/data/experience.db \
    CONFIG_PATH=/config/services.yaml \
    DOCKER_SOCKET=/var/run/docker.sock \
    DASHBOARD_PORT=8088 \
    TZ=UTC

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8088/api/health || exit 1

CMD ["python", "-m", "uvicorn", "dashboard.dashboard_server:app", "--host", "0.0.0.0", "--port", "8088"]
