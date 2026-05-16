#!/bin/bash
# Target script for Entropy Engine testing.
# It performs simple tasks that are sensitive to timing or resource spikes.

TARGET_FILE="state/entropy_canary.tmp"

do_work() {
    # Task: Write small fragments of data and then verify them.
    # In a noisy environment, if the tool disrupts filesystem IO or process scheduling’s atomicity, 
    # we might see anomalies (though unlikely on local disk).
    for i in {1..10}; do
        echo "fragment_$i: $(date +%s)" >> "$TARGET_FILE"
        if [ $i -eq 5 ]; then sleep 0.5; fi # Artifical gap for TJI targets
    done
    COUNT=$(wc -l < "$TARGET_FILE")
    echo "Fragments written: $COUNT"
}

rm -f "$TARGET_FILE"
do_work
