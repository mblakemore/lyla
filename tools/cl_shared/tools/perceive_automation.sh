#!/bin/bash
# Lyla/C0rtana PERCEIVE Phase Automation Script
# Runs during the PERCEIVE phase to gather all state, messages, Discord activity

set -e

REPO_ROOT="${LORA_REPO:-/droid/repos/lyla}"
SHARED="/droid/repos/cl_shared"
OUTPUT_LOG="$1"  # Expected: path/to/log-entry.jsonl line

cd "$REPO_ROOT"

echo "=== PERCEIVE PHASE AUTOMATION ==="
echo "Starting at $(date -Iseconds)"
echo ""

# Verify repo identity first
echo "[1/6] Verifying git remote..."
git remote -v | tee -a "$OUTPUT_LOG" || true

echo ""
echo "[2/6] Reading current state files..."
cat state/current-state.json | tee -a "$OUTPUT_LOG" || echo "{}" | tee -a "$OUTPUT_LOG"
echo ""
cat state/focus.json | tee -a "$OUTPUT_LOG" || echo "{}" | tee -a "$OUTPUT_LOG"
echo ""

# Check if there are instructions in from-creator.md
if [[ -f messages/from-creator.md ]]; then
    creator_instruct=$(head -5 messages/from-creator.md)
    echo "[3/6] Creator instructions (first 5 lines):" >> "$OUTPUT_LOG"
    head -5 messages/from-creator.md >> "$OUTPUT_LOG"
fi
echo ""

# Pull Discord recent activity
echo "[4/6] Checking Discord for c0rtana/Creator activity..."
node "$SHARED/discord/discord-chat.js" recent --limit 20 2>&1 | tee -a "$OUTPUT_LOG" || echo "Discord not available" >> "$OUTPUT_LOG"
echo ""

# Git log
echo "[5/6] Recent commits..."
git log --oneline -10 | tee -a "$OUTPUT_LOG"
echo ""

# Patterns query — grep for any patterns mentioning this cycle or key terms
echo "[6/6] Querying relevant memory patterns..."
grep -i -E "(C[0-9]{3}|token_gap|handoff_|blackboard)" state/memories/patterns.jsonl 2>/dev/null | tail -20 | tee -a "$OUTPUT_LOG" || echo "No matching patterns found" >> "$OUTPUT_LOG"

echo ""
echo "=== PERCEIVE COMPLETE ==="
echo "Output logged to: $OUTPUT_LOG"
