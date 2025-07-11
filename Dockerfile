# ── app/Dockerfile ──
FROM python:3.10-slim

# Install OS packages: build tools, Postgres headers, cron, curl
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
      cron \
      curl \
 && rm -rf /var/lib/apt/lists/*

# Create app directories
WORKDIR /app
RUN mkdir -p /app/logs

# Copy & install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of your code
COPY . /app

# Make scheduler script executable
RUN chmod +x /app/run_scheduler.sh

# Install cron job: every 15 minutes, run your scheduler and append to /app/logs
RUN echo "*/15 * * * * root /app/run_scheduler.sh >> /app/logs/cron_invocations.log 2>&1" \
     > /etc/cron.d/email-platform \
 && chmod 0644 /etc/cron.d/email-platform \
 && crontab /etc/cron.d/email-platform

# Expose FastAPI port
EXPOSE 8000

# Launch both cron and Uvicorn when the container starts
CMD ["sh", "-c", "cron && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

