import json
import os
from datetime import datetime, timedelta, timezone

def calculate_cognitive_velocity(patterns_path, anchors_path):
    """
    Calculates Cognitive Velocity (CV) based on new entries in memory files.
    Defined as: Total New Memory Entries within the sliding window.
    """
    # Use timezone-aware UTC now
    now = datetime.now(timezone.utc)
    window = timedelta(days=1)  # Look at the last 24 hours for velocity
    count = 0
    
    for path in [patterns_path, anchors_path]:
        if not os.path.exists(path):
            continue
        with open(path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    created_str = entry.get('created', '')
                    if created_str:
                        # Normalize ISO format to be timezone aware
                        dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        
                        if now - dt < window:
                            count += 1
                except (json.JSONDecodeError, ValueError):
                    continue
    return count

def update_state(state_path, cv):
    """Updates current-state.json with the calculated cognitive velocity."""
    if not os.path.exists(state_path):
        return
    
    with open(state_path, 'r') as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            print("Error reading state file")
            return

    state['cognitive_velocity'] = cv
    state['last_analysis_timestamp'] = datetime.now(timezone.utc).isoformat()
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    # Paths relative to repo root
    PATTERNS = 'state/memories/patterns.jsonl'
    ANCHORS = 'state/memories/anchors.jsonl'
    STATE = 'state/current-state.json'
    
    cv = calculate_cognitive_velocity(PATTERNS, ANCHORS)
    update_state(STATE, cv)
    print(f"Cognitive Velocity calculated as: {cv}")
