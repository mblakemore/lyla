#!/bin/bash

# Entropy Engine v1
# A tool to provoke failure by inducing environmental noise.
# Based on ENTROPY_ENGINE_SPEC.md

set -u # Treat unset variables as an error

LOG_FILE="logs/entropy_event.log"
mkdir -p logs
touch "$LOG_FILE"

usage() {
    echo "Usage: $0 [mode] [target_cmd] [options]"
    echo ""
    echo "Modes:"
    echo "  --tji   Temporal Jitter Injection (stochastically delay operations)"
    echo "  --rep   Resource Exhaustion Pulsing (CPU load spikes)"
    echo "  --sss   State Sequence Shuffling (simulated IO delays via wrapper)"
    echo ""
    echo "Options:"
    echo "  --intensity <level>  (1-5) Adjusts magnitude of perturbation"
    echo "  --duration <sec>      How long the stress should last"
    exit 1
}

if [[ $# -lt 2 ]]; then usage; fi

MODE=$1
shift
CMD=""
INTENSITY=3
DURATION=60

while [[ $# -gt 0 ]]; do
    case $1 in
        --intensity) INTENSITY="$2"; shift ;;
        --duration) DURATION="$2"; shift ;;
        *) CMD="$1" ;;
    esac
    shift
done

if [[ -z "$CMD" ]]; then
    echo "Error: No target command provided."
    usage
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$MODE] [Int:$INTENSITY] $1" >> "$LOG_FILE"
}

# --- Implementation: Temporal Jitter Injection (TJI) ---
run_tji() {
    log "Starting TJI against: $CMD"
    # We wrap the command and inject random sleeps if it's a loop, 
    # or just before starting. For more granular injection, this would need to be a shim.
    local jitter=$(awk -v i=$INTENSITY 'BEGIN{srand(); print (rand()*i*0.1)}')
    log "Injected jitter coefficient: $jitter seconds"
    
    # In a real world scenario, we might use an LD_PRELOAD wrapper here.
    # For this MVP, we simulate the pre-execution lag and potential race window.
    sleep "$jitter"
    eval "$CMD" &
    PID=$!
    wait $PID
    log "TJI Execution finished with exit code $?"
}

# --- Implementation: Resource Exhaustion Pulsing (REP) ---
run_rep() {
    log "Starting REP pulse sequence against: $CMD"
    echo "Running target in background..."
    eval "$CMD" &
    TARGET_PID=$!
    
    END_TIME=$((SECONDS + DURATION))
    while [ $SECONDS -lt $END_TIME ]; do
        if ! kill -0 $TARGET_PID 2>/dev/null; then break; fi
        
        # Pulse High: Spike CPU
        log "Pulsing HIGH load"
        timeout $((INTENSITY * 2)) bash -c "cat /dev/urandom | gzip > /dev/null" &
        sleep $(( (5 - INTENSITY) + 1 ))
        
        # Pulse Low: Recover
        log "Pulsing LOW load"
        sleep 2
    done
    kill $TARGET_PID 2>/dev/null || true
    log "REP cycle completed."
}

# --- Implementation: State Sequence Shuffling (SSS) ---
run_sss() {
    log "Starting SSS simulation for command: $CMD"
    # This mimics out-of-order effects by wrapping the command execution 
    # with a slight random delay to shift the start window relative to other agents.
    local drift=$(awk -v i=$INTENSITY 'BEGIN{srand(); print (rand()*i*0.5)}')
    echo "Shifting sequence by $drift seconds..."
    sleep "$drift"
    eval "$CMD"
    log "SSS Execution finished."
}

case $MODE in
    --tji) run_tji ;;
    --rep) run_rep ;;
    --sss) run_sss ;;
    *) usage ;;
esac
