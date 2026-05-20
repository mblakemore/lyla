#!/bin/bash
# Quick query script for BB scan state history
# Usage: ./query_scan_state.sh [--limit N]

LIMIT="10"
if [[ "$1" =~ ^--limit=(.+)$ ]]; then
    LIMIT="${BASH_REMATCH[1]}"
fi

if [[ "$LIMIT" =~ ^[0-9]+$ ]]; then
    python3 "$(dirname "$0")/state_sync_client.py" query --limit "$LIMIT"
else
    echo "Usage: $0 [--limit N]" >&2
    exit 1
fi
