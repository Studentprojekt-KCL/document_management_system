FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Then copy app
COPY . .

# Ensure Python can find modules
ENV PYTHONPATH=/app

#  Run API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
