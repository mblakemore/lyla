#!/bin/bash
# Launcher for bb_sustained_telemetry.py
# Runs every 15 minutes during active hours (06:00-23:00 UTC)
# Outputs to /droid/repos/lyla/logs/sustained-telemetry.log

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/droid/repos/lyla/logs/sustained-telemetry.log"

# Check if we're in active hours (Python does the real check)
python3 "$SCRIPT_DIR/bb_sustated_telemetry.py" --check-active-hours | grep -q "ACTIVE HOURS" || exit 0

# Run full analysis and append to log
echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Running sustained telemetry probe" >> "$LOG_FILE"
python3 "$SCRIPT_DIR/bb_sustained_telemetry.py" >> "$LOG_FILE" 2>&1 || echo "[ERROR] Probe failed at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG_FILE"
