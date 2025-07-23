# ──────────────────────────────────────────────────────────────
# Base image
FROM python:3.11-slim

# Install system deps for table extraction and PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc build-essential libmupdf-dev && \
    rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /code
ENV PYTHONPATH=/code

# Copy Python deps first (enables Docker-layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# A default command (compose will override for api/worker)
CMD ["python", "-m", "pip", "--version"]

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc build-essential libopenblas-dev && \
    rm -rf /var/lib/apt/lists/*
