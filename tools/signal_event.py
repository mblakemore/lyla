import json
import sys
from datetime import datetime
import os

def log_event(event_type, event_id, detail):
    # Update current-state.json for immediate visual trigger
    state_path = 'state/current-state.json'
    if os.path.exists(state_path):
        with open(state_path, 'r') as f:
            state = json.load(f)
        
        state['last_event'] = {
            "type": event_type,
            "id": event_id,
            "detail": detail,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)

    # Log to telemetry pulse for trend analysis
    pulse_path = 'state/telemetry/pulse.jsonl'
    os.makedirs(os.path.dirname(pulse_path), exist_ok=True)
    
    pulse_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "id": event_id,
        "detail": detail,
        "cycle": state.get('cycle', 0) if 'state' in locals() else 48
    }
    
    with open(pulse_path, 'a') as f:
        f.write(json.dumps(pulse_entry) + '\n')

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 tools/signal_event.py <type> <id> <detail>")
        sys.exit(1)
    
    log_event(sys.argv[1], sys.argv[2], sys.argv[3])
