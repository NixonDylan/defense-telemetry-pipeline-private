# --- Stage 1: Build Dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install dependencies into a clean target directory
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed site-packages directly from the builder's prefix into appuser's local path
COPY --from=builder --chown=appuser:appgroup /install /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:api_gateway", "--host", "0.0.0.0", "--port", "8000"]
