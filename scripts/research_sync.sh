#!/bin/bash
# Simple research probe for agents to pull from BB and summarize relevant items
# Usage: ./scripts/research_sync.sh <min_priority>

MIN_PRIORITY=${1:-4}
echo "[INFO] Pulling High Signal from Shared Blackboard (>= $MIN_PRIORITY)"
python3 /droid/repos/lyla/tools/bb_tool.py pull $MIN_PRIORITY | grep -E 'payload|entry_id|source'
echo ""
echo "[STATUS] Sync complete."
