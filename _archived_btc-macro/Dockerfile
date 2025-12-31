FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env* ./

# Set environment
ENV PYTHONPATH=/app/src
ENV TZ=Asia/Seoul

# Run service
CMD ["python", "src/btc_engine/service.py", "--daemon"]
