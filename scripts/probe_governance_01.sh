#!/bin/bash
# Probe_Governance_01: Check for consistency between current-state and focus files
echo "Running Governance Probe 01..."

CURRENT_STATE="state/current-state.json"
FOCUS_STATE="state/focus.json"

if [[ ! -f "$CURRENT_STATE" || ! -f "$FOCUS_STATE" ]]; then
    echo "CRITICAL: State files missing."
    exit 1
fi

CYCLE=$(grep '"cycle"' $CURRENT_STATE | sed 's/[^0-9]//g')
THEME_STARTED=$(grep '"theme_started_cycle"' $FOCUS_STATE | sed 's/[^0-9]//g')

echo "Current Cycle: $CYCLE"
echo "Theme Started At: $THEME_STARTED"

# Invariant: Theme started cycle must be <= Current cycle
if [ "$THEME_STARTED" -gt "$CYCLE" ]; then
    echo "GOVERNANCE_DRIFT: Theme start date is in the future!"
    exit 2
else
    echo "Consistency check passed."
    exit 0
fi
