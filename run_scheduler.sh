#!/usr/bin/env bash
# 📄 /home/mcd/email-platform/run_scheduler.sh

BASEDIR=/home/mcd/email-platform
LOGDIR=$BASEDIR/logs
LOGFILE=$LOGDIR/cron_invocations.log
ARCHIVE=$LOGDIR/archive

# Ensure directories exist
mkdir -p "$LOGDIR" "$ARCHIVE"

# Archive yesterday's log if this is the first invocation of today
TODAY=$(date '+%Y-%m-%d')
LAST_RUN_DATE_FILE=$LOGDIR/.last_cron_archive

# If we haven’t stamped today yet, archive and reset
if [ ! -f "$LAST_RUN_DATE_FILE" ] || grep -qxv "$TODAY" "$LAST_RUN_DATE_FILE"; then
  if [ -s "$LOGFILE" ]; then
    # compress yesterday’s log under archive
    gzip -c "$LOGFILE" > "$ARCHIVE/cron_invocations_$TODAY.log.gz"
  fi
  # truncate live log
  : > "$LOGFILE"
  # mark this date so we only archive once
  echo "$TODAY" > "$LAST_RUN_DATE_FILE"
fi

# --- now do the usual logging ---
# timestamp the firing
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cron job fired" >> "$LOGFILE"

# fire the scheduler endpoint; capture HTTP code
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8000/run-scheduler)
echo "→ HTTP $HTTP_CODE at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOGFILE"

# blank line for readability
echo "" >> "$LOGFILE"

