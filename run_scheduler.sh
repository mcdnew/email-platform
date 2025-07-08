#!/usr/bin/env bash
# 📄 /home/mcd/email-platform/run_scheduler.sh

LOGFILE=/home/mcd/email-platform/logs/cron_invocations.log

# ensure the log directory exists
mkdir -p "$(dirname "$LOGFILE")"

# timestamp the firing
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron job fired" >> "$LOGFILE"

# fire the scheduler endpoint, quietly capture its JSON response (even if it's a 500)
curl -s -X POST http://127.0.0.1:8000/run-scheduler >> "$LOGFILE" 2>&1

# blank line for readability
echo "" >> "$LOGFILE"

