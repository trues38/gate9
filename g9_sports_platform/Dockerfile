# ============================================
# G9 Sports Intelligence Platform
# Multi-stage Dockerfile
# ============================================

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# Dependencies Stage
# ============================================
FROM base as dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# Production Stage
# ============================================
FROM dependencies as production

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash g9user && \
    chown -R g9user:g9user /app

USER g9user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Development Stage
# ============================================
FROM dependencies as development

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    black \
    isort \
    mypy

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
