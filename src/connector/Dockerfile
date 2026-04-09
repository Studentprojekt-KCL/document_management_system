FROM python:3.11-slim

WORKDIR /app

# Install build tools (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install gateway dependencies first for layer caching
COPY gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only gateway service code
COPY gateway/ ./

# Ensure local imports (core/) resolve
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.unified_api:app", "--host", "0.0.0.0", "--port", "8000"]
