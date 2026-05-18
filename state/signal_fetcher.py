#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime
import os
import sys

BB_TOOL = "/droid/repos/cl_shared/blackboard_tool.py"
FOCUS_PATH = "state/focus.json"
TASK_LIST = ".agent/state/tasks.json"

def get_signals():
    try:
        result = subprocess.check_output([sys.executable, BB_TOOL, "--action", "pull", "--min-pri", "8"], text=True)
        return json.loads(result) if result.strip() else []
    except Exception as e:
        print(f"[ERROR] Failed to poll blackboard: {e}")
        return []

def process_signal(entry):
    message = entry.get("payload") or ""
    source = entry.get("source", "Unknown")
    priority = entry.get("priority", 5)
    
    # Check for specific patterns like [SOTABRAIN] or [C0RTANA:TARGET]
    if "[URGENT]" in message or priority >= 9:
        update_focus(message, source, priority)
    elif "[NEW TASK]" in message:
        append_task(message, source)
    else:
        log_observation(message, source)

def update_focus(text, source, priority):
    with open(FOCUS_PATH, 'r') as f:
        data = json.load(f)
    
    print(f"Updating focus from signal ({source})!")
    data["active_stream"] = f"Blackboard Sync: {source}"
    data["target"] = text[:200] # truncate long signals
    data["last_sync"] = datetime.now().isoformat()
    data["priority"] = max(data.get("priority", 1), priority)
    
    with open(FOCUS_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def append_task(text, source):
    import os
    if not os.path.exists(".agent/state"):
        os.makedirs(".agent/state")
        
    tasks = []
    if os.path.exists(TASK_LIST):
        try:
            with open(TASK_LIST, 'r') as f:
                tasks = json.load(f)
        except: pass
    
    new_id = len(tasks) + 1 if tasks else 1
    tasks.append({
        "id": new_id,
        "description": f"[BB-{source}] {text}",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "category": "blackboard_signal"
    })
    
    with open(TASK_LIST, 'w') as f:
        json.dump(tasks, f, indent=2)

def log_observation(text, source):
    # For lower pri signals that aren't direct focus shifts
    log_entry = f"{datetime.now()} | Signal from {source}: {text[:500]}\n"
    with open("logs/external_signals.log", "a") as f:
        f.write(log_entry)

if __name__ == "__main__":
    signals = get_signals()
    if not signals:
        print("No high-pri signals.")
        sys.exit(0)
        
    for s in signals:
        process_signal(s)
    print(f"Processed {len(signals)} signal(s).")
