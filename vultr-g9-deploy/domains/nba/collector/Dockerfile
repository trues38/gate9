FROM python:3.11-slim

WORKDIR /app

# System packages
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Port
EXPOSE 8001

# Create data directory
RUN mkdir -p /app/data

# Run
CMD ["python", "app_api.py"]
