import json
import sys
import os
from datetime import datetime

BB_PATH = "/droid/repos/cl_shared/blackboard_registry.json"

def load_bb():
    try:
        with open(BB_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading blackboard: {e}")
        return []

def save_bb(data):
    try:
        # Basic lock would be better, but for now we just write and hope the OS handles it or C0rtana doesn't collide exactly on this ms
        with open(BB_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving blackboard: {e}")
        return False

def push_entry(category, priority, payload, semantic_hash=None):
    bb = load_bb()
    entry_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
    entry = {
        "entry_id": entry_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "Lyla",
        "category": category,
        "priority": int(priority),
        "ttl": "Permanent",
        "payload": payload,
        "semantic_hash": semantic_hash or str(payload)[:100],
        "status": "Active"
    }
    bb.append(entry)
    if save_bb(bb):
        print(f"Pushed to Blackboard: {entry_id}")
    else:
        sys.exit(1)

def pull_entries(min_priority=0, status="Active"):
    bb = load_bb()
    filtered = [e for e in bb if e["status"] == status and int(e["priority"]) >= min_priority]
    return filtered

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tools/bb_tool.py [push|pull] ...")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "push":
        # Expects JSON as last argument
        try:
            import ast
            data = ast.literal_eval("'".join(sys.argv[2:])) # simple way to get dict from shell args
            category = data.get('category', 'General')
            priority = data.get('priority', 3)
            payload = data.get('payload', {})
            semantic_hash = data.get('semantic_hash')
            push_entry(category, priority, payload, semantic_hash)
        except Exception as e:
            print(f"Invalid input: {e}")
            sys.exit(1)
    elif cmd == "pull":
        min_p = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        entries = pull_entries(min_priority=min_p)
        print(json.dumps(entries, indent=2))
