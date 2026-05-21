#!/bin/bash
# bb_sustained_telemetry_launcher.sh
# Launches the sustained telemetry probe every 30 minutes during operator active hours
# Designed to run via crontab or systemd timer

PROBE_SCRIPT="/droid/repos/cl_shared/bb_sustained_telemetry.py"
LOG_DIR="/droid/repos/lyla/logs/telemetry"
LOCK_FILE="/tmp/telemetry_probe.lock"

mkdir -p "$LOG_DIR"

# Check if already running (avoid duplicate instances)
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Probe already running (PID $PID), exiting"
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi

echo $$ > "$LOCK_FILE"

TIMESTAMP=$(date -Iseconds)
echo "[$TIMESTAMP] Starting sustained telemetry probe..." >> "${LOG_DIR}/launcher.log"

python3 "$PROBE_SCRIPT" --json 2>&1 | tee -a "${LOG_DIR}/probe_output.log"

rm -f "$LOCK_FILE"
echo "[$(date -Iseconds)] Probe complete" >> "${LOG_DIR}/launcher.log"
