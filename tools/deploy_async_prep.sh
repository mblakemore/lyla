#!/bin/bash
# Deploy Async Prep Output to Blackboard
# 
# Usage: ./deploy_async_prep.sh [--mode summary|jsonl|both] [--delegation-level N]
#
# Reads async_prep.py JSONL output and pushes each entry to blackboard via bb_tool.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYNC_PREP="${SCRIPT_DIR}/async_prep.py"
BB_TOOL="${SCRIPT_DIR}/cl_shared/bb_tool.py"

# Parse arguments
MODE="jsonl"
DELEGATION_LEVEL=""
FORCE_FLAG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --delegation-level)
            DELEGATION_LEVEL="--delegation-level $2"
            shift 2
            ;;
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "======================================================================"
echo "Deploying Async Prep Entries to Blackboard"
echo "Mode: ${MODE}"
if [ -n "$DELEGATION_LEVEL" ]; then
    echo "Delegation Level: ${DELEGATION_LEVEL#--delegation-level }"
fi
echo "======================================================================"

# Generate JSONL output from async_prep
OUTPUT=$(python3 "${ASYNC_PREP}" --mode jsonl ${DELEGATION_LEVEL} ${FORCE_FLAG} 2>/dev/null)

# Extract and push each JSON object (one per line)
pushed_count=0
failed_count=0

while IFS= read -r line; do
    # Skip empty lines
    if [ -z "$line" ]; then
        continue
    fi
    
    # Extract fields needed for bb_tool.py push command
    entry_id=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('entry_id', 'unknown'))")
    timestamp=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('timestamp', ''))")
    category=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('category', 'General'))")
    priority=$(echo "$line" | python3 -c "import sys, json; print(json.load(sys.stdin).get('priority', 5))")
    
    # Create payload as JSON string
    payload=$(echo "$line" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))")
    
    # Push to blackboard via bb_tool.py
    echo "[PUSH] Entry: ${entry_id}"
    if python3 "${BB_TOOL}" push "${priority}" "${category}" "${payload}" --from "Lyla (Async Prep)" --ttl "Permanent"; then
        ((pushed_count++))
    else
        echo "[FAILED] Could not push: ${entry_id}"
        ((failed_count++))
    fi
    
done <<< "$OUTPUT"

echo ""
echo "======================================================================"
echo "Deployment Summary:"
echo "  Entries pushed: ${pushed_count}"
echo "  Failed entries: ${failed_count}"
echo "======================================================================"

if [ $failed_count -gt 0 ]; then
    exit 1
fi
