import json
import subprocess
from datetime import datetime

def get_git_info():
    try:
        remote = subprocess.check_output(["git", "remote", "-v"], stderr=subprocess.STDOUT).decode().strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], stderr=subprocess.STDOUT).decode().strip()
        log = subprocess.check_output(["git", "log", "-n", "5", "--oneline"], stderr=subprocess.STDOUT).decode().strip()
        return {
            "remote": remote,
            "branch": branch,
            "log": log
        }
    except Exception as e:
        return {"error": str(e)}

def read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": str(e)}

def main():
    # Paths relative to repo root
    paths = {
        "current_state": "state/current-state.json",
        "focus": "state/focus.json",
        "capabilities": "state/memories/capabilities.jsonl"
    }
    
    git_info = get_git_info()
    state = read_json(paths["current_state"])
    focus = read_json(paths["focus"])
    
    # Count capabilities
    cap_count = 0
    try:
        with open(paths["capabilities"], 'r') as f:
            cap_count = len(f.readlines())
    except FileNotFoundError:
        pass

    print("--- LYLA PERCEPTION REPORT ---")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Repo Remote: {git_info.get('remote', 'Unknown')}")
    print(f"Current Branch: {git_info.get('branch', 'Unknown')}")
    print(f"Recent History:\n{git_info.get('log', 'No logs found')}")
    print("-" * 30)
    print(f"Cycle: {state.get('cycle', 'Unknown')} | Phase: {state.get('phase', 'Unknown')}")
    print(f"Status: {state.get('status', 'Unknown')} | Confidence: {state.get('confidence', 'Unknown')}")
    print(f"Last Action: {state.get('last_action', 'Unknown')}")
    print("-" * 30)
    print(f"Focus Goal: {focus.get('current_goal', 'Unknown')}")
    print(f"Next Milestone: {focus.get('next_milestone', 'Unknown')}")
    print(f"Priority: {focus.get('priority', 'Unknown')}")
    print("-" * 30)
    print(f"Registered Capabilities: {cap_count}")
    print("--- END REPORT ---")

if __name__ == "__main__":
    main()
