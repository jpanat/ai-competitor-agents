FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY job_matcher/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project (context is repo root)
COPY . /app/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default: overridden per-service in docker-compose
CMD ["python", "-m", "job_matcher.orchestrator.server"]
