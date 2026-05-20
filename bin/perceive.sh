#!/usr/bin/env bash
# bin/perceive.sh - PERCEIVE phase automation script
# Reads git state, current-state.json, focus.json, outputs JSON summary

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="${REPO_ROOT}/state"
CURRENT_STATE="${STATE_DIR}/current-state.json"
FOCUS_FILE="${STATE_DIR}/focus.json"
LOGS_DIR="${REPO_ROOT}/logs"
MESSAGES_DIR="${REPO_ROOT}/messages"

# Verify repo identity - check for ly(l)a in remote URL
GIT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "NONE")
if [[ "$GIT_REMOTE" == "NONE" ]] || [[ ! "$GIT_REMOTE" =~ ly[l]a ]]; then
    echo '{"error": "repo_mismatch", "remote": "'"$GIT_REMOTE"'"}'
    exit 1
fi

# Use cycle number from internal state (more reliable than parsing git log)
if [[ -f "$CURRENT_STATE" ]]; then
    CYCLE_NUM=$(jq -r '.cycle // 0' "$CURRENT_STATE")
else
    CYCLE_NUM=0
fi

# Read current state for other fields
if [[ -f "$CURRENT_STATE" ]]; then
    CURRENT_CYCLE=$((CYCLE_NUM))
    LAST_PHASE=$(jq -r 'if .last_phase then .last_phase else "unknown" end' "$CURRENT_STATE")
else
    CURRENT_CYCLE=0
    LAST_PHASE="none"
fi

# Get focus - properly encode subject as string or null in JSON
if [[ -f "$FOCUS_FILE" ]] && jq -e '.subject' "$FOCUS_FILE" >/dev/null 2>&1; then
    FOCUS_SUBJECT_JSON=$(jq -r '"\(.subject)"' "$FOCUS_FILE")
    FOCUS_STATUS=$(jq -r 'if .status then .status else "uninitialized" end' "$FOCUS_FILE")
else
    FOCUS_SUBJECT_JSON='null'
    FOCUS_STATUS="uninitialized"
fi


# Check messages from creator
HAS_NEW_MESSAGES=false
if [[ -f "${MESSAGES_DIR}/from-creator.md" ]] && [[ -s "${MESSAGES_DIR}/from-creator.md" ]]; then
    MSG_LINES=$(wc -l < "${MESSAGES_DIR}/from-creator.md")
    if [[ $MSG_LINES -gt 0 ]]; then
        HAS_NEW_MESSAGES=true
    fi
fi

# Check discord for recent messages (quiet, just presence check)
DISCORD_RECENT=""
if command -v node &>/dev/null; then
    DISCORD_RECENT=$(node /droid/cl_skills/discord/discord-chat.js recent --limit 3 2>&1 | head -5 || echo "")
fi

# Get git commit count in last 5 commits
GIT_COMMIT_COUNT=$(git log --oneline HEAD~5..HEAD 2>/dev/null | wc -l | tr -d '[:space:]')
[[ -z "${GIT_COMMIT_COUNT}" ]] && GIT_COMMIT_COUNT=0

# Output JSON summary (properly format focus_subject as variable)
cat <<EOF
{
  "phase": "PERCEIVE",
  "cycle_number": ${CYCLE_NUM},
  "last_cycle_at_repo": ${CURRENT_CYCLE},
  "git_commit_count": ${GIT_COMMIT_COUNT},
  "focus_subject": ${FOCUS_SUBJECT_JSON},
  "focus_status": "$(echo "$FOCUS_STATUS" | sed "s/'/\\\\'/g; s/\"/\\\\\"/g")",
  "has_creator_messages": ${HAS_NEW_MESSAGES},
  "state_files_exist": {
    "current-state.json": true,
    "focus.json": true
  },
  "discord_active": $([ -n "$DISCORD_RECENT" ] && echo true || echo false),
  "git_remote_clean": "$(echo "$GIT_REMOTE" | sed 's/[^a-zA-Z0-9._-]/_/g')"
}
EOF
