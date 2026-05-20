FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached on re-deploys
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory (ephemeral on Cloud Run, fine for demo)
RUN mkdir -p logs

# Cloud Run injects $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
