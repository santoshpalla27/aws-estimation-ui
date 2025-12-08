FROM python:3.9-slim

WORKDIR /app

# Install system deps if needed (sqlite3 is usually in slim, but good to ensure)
# RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set python path to include root if needed, but we run scripts explicitly
ENV PYTHONPATH=/app
