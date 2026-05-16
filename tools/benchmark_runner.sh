#!/bin/bash

# benchmark_runner.sh
# Measures the effect of perturbations on task execution time (in seconds).
# Fixes: properly stores timestamps in variables rather than trying to execute them.

TARGET="./tools/test_entropy.sh"
ITERATIONS=3

run_measurement() {
    local mode=$1
    local intensity=${2:-3}
    local duration=${3:-5}
    local label="$mode"
    [ "$mode" == "none" ] && label="baseline"
    
    LOGFILE="logs/bench_${label}.txt"
    echo "--- Starting $label (${intensity}) ---" > "$LOGFILE"
    
    for i in $(seq 1 $ITERATIONS); do
        START=$(date +%s.%N)
        if [[ "$mode" == "none" ]]; then
            "$TARGET" &> /dev/null
        else
            ./tools/entropy_engine.sh "$mode" "$TARGET" --intensity "$intensity" --duration "$duration" &> /dev/null
        fi
        END=$(date +%s.%N)
        # Using python to avoid common shell arithmetic precision issues with nanoseconds
        R_VAL=$(python3 -c "print(round(float('$END') - float('$START'), 4))")
        echo \"Run \${i}: \$R_VAL\" >> \"\$LOGFILE\"
    done
    
    AVG=$(grep 'Run' "$LOGFILE" | awk '{ sum += $2 } END { if (NR > 0) print sum/NR; else print 0 }')
    echo "Average: $AVG seconds" >> "$LOGFILE"
}

case "$1" in
    --baseline) run_measurement "none" ;;
    --tji)      run_measurement "--tji" "${2:-3}" ;;
    --rep)      run_measurement "--rep" "${2:-3}" "${3:-5}" ;;
    *)          echo "Usage: $0 [--baseline|--tji|--rep] [intensity] [duration]"; exit 1 ;;
esac
