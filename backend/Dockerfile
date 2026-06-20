# syntax=docker/dockerfile:1.7
# ---- Builder ----
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for psycopg2/asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first for layer caching
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# ---- Runtime ----
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime deps only (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv and source
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Non-root user
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run migrations on container start (see docker-compose), then serve.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
