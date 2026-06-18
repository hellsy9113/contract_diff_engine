FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies needed by PyMuPDF and common PDF tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen || uv sync

# Copy source code
COPY . .

# FastAPI port
EXPOSE 8000

# Run the FastAPI app
EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn contract_diff_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]