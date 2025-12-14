# Test Container Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    requests==2.31.0 \
    pytest-timeout==2.2.0

# Copy test files
COPY backend/tests/ /app/tests/

# Copy test runner script
COPY backend/tests/run_tests.sh /app/run_tests.sh
RUN chmod +x /app/run_tests.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run tests
CMD ["/app/run_tests.sh"]
