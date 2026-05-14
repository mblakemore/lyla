import json
import os
from datetime import datetime

def signal_event(event_type, event_id, detail=""):
    state_path = 'state/current-state.json'
    if not os.path.exists(state_path):
        print("State file not found.")
        return

    with open(state_path, 'r') as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            print("Invalid JSON in state file.")
            return

    # Update the last_event field for holographic signaling
    state['last_event'] = {
        "type": event_type,
        "id": event_id,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 tools/signal_event.py <type> <id> [detail]")
    else:
        signal_event(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 2 else "")
