#!/bin/bash
# Atomic PERCEIVE-state readout for operator-facing diagnostics
# Output format: machine-parseable JSON + human-readable summary

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$REPO_ROOT"

# Core state reads
CYCLE=$(jq -r '.cycle // 0' state/current-state.json 2>/dev/null || echo "N/A")
PHASE=$(jq -r '.phase // "unknown"' state/current-state.json 2>/dev/null || echo "N/A")
FOCUS=$(jq -r '.focus // "none"' state/focus.json 2>/dev/null || echo "N/A")

# Remote verification
REMOTE=$(git remote get-url origin 2>/dev/null || echo "NOT_CONFIGURED")
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Discord sync check (last message timestamp from lyla)
DISCORD_SYNC="UNKNOWN"
if node /droid/cl_skills/discord/discord-chat.js recent --limit 1 >/dev/null 2>&1; then
    DISCORD_SYNC="SYNCHRONIZED"
else
    DISCORD_SYNC="OFFLINE"
fi

# Git head info
LAST_COMMIT=$(git log --oneline -1 2>/dev/null | cut -d' ' -f1 || echo "NO_COMMITS")
COMMIT_MSG=$(git log -1 --format="%s" 2>/dev/null || echo "")

# Timestamp
TIMESTAMP=$(date -Iseconds)

# Output JSON
cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "cycle": $CYCLE,
  "phase": "$PHASE",
  "remote": "$REMOTE",
  "branch": "$BRANCH",
  "discord_sync": "$DISCORD_SYNC",
  "last_commit": "$LAST_COMMIT",
  "focus": "$(echo "$FOCUS" | tr '\n' ' ')"
}
EOF

# Human-readable summary
echo ""
echo "=== PERCEIVE CHECK ==="
echo "Cycle: $CYCLE ($PHASE)"
echo "Remote: $(basename $(dirname "$REMOTE"))"
echo "Branch: $BRANCH"
echo "Last commit: $LAST_COMMIT"
echo "Discord sync: $DISCORD_SYNC"
echo "Focus: $FOCUS"
