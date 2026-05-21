#!/bin/bash
# Lyla/C0rtana CONSOLIDATE Phase Automation Script
# Appends new patterns/anchors and syncs shared blackboard entries

set -e

REPO_ROOT="${LORA_REPO:-/droid/repos/lyla}"
SHARED="/droid/repos/cl_shared"
BLACKBOARD="$SHARED/blackboard_registry.json"
OUTPUT_FILE="$1"  # Path where this script will write its output JSONL line

cd "$REPO_ROOT"

ISO_TIMESTAMP=$(date -Iseconds)

if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "Error: OUTPUT_FILE not provided or invalid" >&2
    exit 1
fi

echo "" >> "$OUTPUT_FILE"
echo "{\"cycle\":$(cat state/current-state.json | grep -oP '"cycle":\K[0-9]+'),"timestamp\":\"$ISO_TIMESTAMP\",\"source\":\"$USER\",..." >> "$OUTPUT_FILE"

echo "[CONSOLIDATE] Generated timestamp: $ISO_TIMESTAMP"
echo "Output written to: $OUTPUT_FILE"
