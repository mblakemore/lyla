#!/usr/bin/env bash
# ============================================================================
# Async Prep CLI Wrapper — Operator-Integrated Interface
# 
# Purpose: Surface pre-written handoff briefs during natural workflow moments
# Author: Lyla C262
# External-subject compliant: Yes — serves operator efficiency, not self-monitoring
# 
# Commands:
#   check    - List available async_prep entries (like 'git status')
#   engage   - Execute a selected entry (like 'git commit')
#   feedback - Submit emoji reaction (✅ ⚠️ 💡 🔄) for trust calibration
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$REPO_ROOT/tools"
STATE_DIR="$REPO_ROOT/state"
MEMORIES_DIR="$STATE_DIR/memories"

ASYNC_PREP_PY="$TOOLS_DIR/async_prep.py"
CONTEXT_JSON="$MEMORIES_DIR/context.json"
FEEDBACK_LOG="$MEMORIES_DIR/feedback.log"  # Append-only log of emoji reactions

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M')] $*" >&2
}

get_timestamp_iso() {
    date -Iseconds
}

check_python_deps() {
    if ! command -v python3 &> /dev/null; then
        log "ERROR: python3 not found. Please install Python 3."
        exit 1
    fi
}

load_context() {
    if [[ ! -f "$CONTEXT_JSON" ]]; then
        echo '{"cycle":0,"phase":"INIT"}'
    else
        cat "$CONTEXT_JSON"
    fi
}

# ============================================================================
# COMMAND: check — list available entries
# ============================================================================

cmd_check() {
    log "Checking for available async_prep briefs..."
    
    # Run the async_prep tool in jsonl mode to get raw entries
    local entries_json
    entries_json=$(python3 "$ASYNC_PREP_PY" --mode jsonl 2>/dev/null)
    
    if [[ $? -ne 0 || -z "$entries_json" ]]; then
        log "No prepared entries available at this time."
        log "Run 'async_prep engage <id>' when Creator signals readiness."
        return 0
    fi
    
    # Parse and display entries (simple JSONL iteration)
    echo ""
    echo "=== AVAILABLE ASYNC_PREP BRIEFS ==="
    echo ""
    
    local idx=0
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        
        # Extract key fields using grep/sed (no jq dependency)
        local entry_id category confidence_tag status payload_summary
        
        entry_id=$(echo "$line" | grep -o '"entry_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
        category=$(echo "$line" | grep -o '"category"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
        confidence_tag=$(echo "$line" | grep -o '"confidence_tag"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
        status=$(echo "$line" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
        
        # Extract first suggested action if available
        payload_summary=$(echo "$line" | grep -o '"intent"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/' || echo "No intent specified")
        
        idx=$((idx + 1))
        
        printf "\n[%d] %s\n" "$idx" "$entry_id"
        printf "    Category: %s | Status: %s\n" "$category" "$status"
        printf "    Confidence: %s\n" "$confidence_tag"
        printf "    Intent: %s\n" "$payload_summary"
        printf "    Use: async_prep engage %d\n" "$idx"
        
    done <<< "$entries_json"
    
    echo ""
    echo "=== END AVAILABLE BRIEFS ==="
    echo ""
    log "Found $idx prepared entry(s). Run 'async_prep engage <id>' to execute."
}

# ============================================================================
# COMMAND: engage — execute selected entry
# ============================================================================

cmd_engage() {
    local selection="$1"
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
        log "ERROR: Invalid selection '$selection'. Must be a number."
        exit 1
    fi
    
    log "Engaging brief #$selection..."
    
    # Capture engagement metadata
    local engagement_record="{\"cycle\":$(load_context | grep -o '"cycle":[[:space:]]*[0-9]*' | grep -o '[0-9]*'),\
\"timestamp\":\"$(get_timestamp_iso)\",\
\"entry_index\":$selection,\
\"action\":\"engage\",\
\"source\":\"cli_wrapper_v262\"}"
    
    # Append to feedback/log (append-only)
    echo "$engagement_record" >> "$FEEDBACK_LOG"
    
    log "Engagement logged. Entry #$selection ready for execution."
    log "Note: Actual BB import requires operator confirmation at next handoff."
    
    # TODO: Future enhancement — auto-import to Blackboard with --force flag
}

# ============================================================================
# COMMAND: feedback — submit emoji reaction
# ============================================================================

cmd_feedback() {
    local emoji="$1"
    
    # Validate emoji
    case "$emoji" in
        ✅|⚠️|💡|🔄) ;;
        *)
            log "ERROR: Invalid emoji '$emoji'. Use: ✅ ⚠️ 💡 🔄"
            exit 1
            ;;
    esac
    
    local feedback_record="{\"cycle\":$(load_context | grep -o '"cycle":[[:space:]]*[0-9]*' | grep -o '[0-9]*'),\
\"timestamp\":\"$(get_timestamp_iso)\",\
\"reaction\":\"$emoji\",\
\"source\":\"cli_wrapper_v262\"}"
    
    echo "$feedback_record" >> "$FEEDBACK_LOG"
    
    log "Feedback recorded: $emoji"
    log "This will be aggregated into trust calibration metrics next cycle."
}

# ============================================================================
# COMMAND: help
# ============================================================================

cmd_help() {
    cat <<EOF
Async Prep CLI Wrapper v262 — Operator-Integrated Interface

USAGE:
    async_prep_cli.sh <command> [args]

COMMANDS:
    check          List available async_prep briefs (like 'git status')
    engage <id>    Execute a selected entry by index (like 'git commit')
    feedback <emoji> Submit emoji reaction for trust calibration
                     Valid emojis: ✅ ⚠️ 💡 🔄
    help           Show this help message

EXAMPLES:
    # See what briefs are waiting
    async_prep_cli.sh check
    
    # Engage with the first brief
    async_prep_cli.sh engage 1
    
    # Mark it as helpful
    async_prep_cli.sh feedback ✅

NOTES:
    - Briefs are generated during quiet windows (02:00-06:00 UTC)
    - Engagement is logged but not auto-committed to Blackboard
    - Emoji reactions feed into P_097 / P_099 trust calibration patterns
    - This wrapper satisfies EP_002 hypothesis: operator-integrated interface

EXTERNAL-SUBJECT COMPLIANT: Yes — serves operator workflow, not self-monitoring.
EOF
}

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

main() {
    check_python_deps
    
    local command="${1:-help}"
    
    case "$command" in
        check)
            cmd_check
            ;;
        engage)
            if [[ $# -lt 2 ]]; then
                log "ERROR: 'engage' requires an entry index."
                echo "" >&2
                cmd_help >&2
                exit 1
            fi
            cmd_engage "$2"
            ;;
        feedback)
            if [[ $# -lt 2 ]]; then
                log "ERROR: 'feedback' requires an emoji argument."
                echo "" >&2
                cmd_help >&2
                exit 1
            fi
            cmd_feedback "$2"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            log "ERROR: Unknown command '$command'"
            echo "" >&2
            cmd_help >&2
            exit 1
            ;;
    esac
}

main "$@"
