#!/bin/bash
# Victim script for Entropy Engine testing.
# This simulates a fragile state machine that assumes sequentiality and atomicity.

STATE_FILE=".target_state"
LOG="logs/victim.log"

mkdir -p logs
echo "START" > "$STATE_FILE"

for i in {1..5}; do
    curr=$(cat "$STATE_FILE")
    if [[ "$curr" == "START" ]]; then
        echo "Updating to PHASE_1..."
        echo "PHASE_1" > "$STATE_FILE"
    elif [[ "$curr" == "PHASE_1" ]]; then
        echo "Updating to PHASE_2..."
        echo "PHASE_2" > "$STATE_FILE"
    elif [[ "$curr" == "PHASE_2" ]]; then
        echo "Updating to FINAL..."
        echo "FINAL" > "$STATE_FILE"
    fi
done

final_state=$(cat "$STATE_FILE")
rm "$STATE_FILE"

if [[ "$final_state" != "FINAL" ]]; then
    echo "FAILED: State ended at $final_state"
    exit 1
else
    echo "SUCCESS"
    exit 0
fi
