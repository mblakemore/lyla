import os
import json
import subprocess
from datetime import datetime

def get_git_status():
    try:
        result = subprocess.run(['git', 'status', '--short'], capture_output=True, text=True)
        return {
            "dirty": len(result.stdout.strip()) > 0,
            "changes": result.stdout.strip().split('\n') if result.stdout.strip() else []
        }
    except Exception as e:
        return {"error": str(e)}

def get_memory_stats():
    stats = {}
    patterns_path = 'state/memories/patterns.jsonl'
    if os.path.exists(patterns_path):
        with open(patterns_path, 'r') as f:
            lines = f.readlines()
            stats['pattern_count'] = len(lines)
    else:
        stats['pattern_count'] = 0
        
    anchors_path = 'state/memories/anchors.jsonl'
    if os.path.exists(anchors_path):
        with open(anchors_path, 'r') as f:
            lines = f.readlines()
            stats['anchor_count'] = len(lines)
    else:
        stats['anchor_count'] = 0
        
    return stats

def check_creator_messages():
    path = 'messages/from-creator.md'
    if not os.path.exists(path):
        return "missing"
    with open(path, 'r') as f:
        content = f.read().strip()
        return "empty" if not content else "has_messages"

def get_log_entropy():
    logs_dir = 'logs/'
    if os.path.exists(logs_dir):
        files = [f for f in os.listdir(logs_dir) if os.path.isfile(os.path.join(logs_dir, f))]
        return len(files)
    return 0

def main():
    probe_data = {
        "timestamp": datetime.now().isoformat(),
        "git": get_git_status(),
        "memory": get_memory_stats(),
        "communication": check_creator_messages(),
        "entropy": get_log_entropy(),
        "root": os.getcwd()
    }
    print(json.dumps(probe_data, indent=2))

if __name__ == "__main__":
    main()
