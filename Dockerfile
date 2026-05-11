FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# System deps for asyncpg
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy everything (README.md needed by hatch metadata)
COPY . .

# Install Python deps
RUN pip install --upgrade pip && \
    pip install ".[dev]"

EXPOSE 8000

# 2 workers for CX32 (4 vCPU); uvloop for perf
CMD ["uvicorn", "apps.api.src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop"]
