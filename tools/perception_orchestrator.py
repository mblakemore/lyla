import json
import subprocess
from datetime import datetime
import os

# Paths relative to repo root
STATE_PATHS = {
    "current_state": "state/current-state.json",
    "focus": "state/focus.json",
    "patterns": "state/memories/patterns.jsonl",
    "anchors": "state/memories/anchors.jsonl"
}

def run_cmd(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.STDOUT).decode().strip()
    except Exception as e:
        return f"Error executing {' '.join(args)}: {e}"

def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_jsonl(path):
    lines = []
    try:
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    lines.append(json.loads(line))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return lines

def orchestrate_perception():
    print(f"\n{'='*60}")
    print(f"LYLA PERCEPTION ORCHESTRATOR | Cycle Start Sequence")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    # 1. Environment & Identity Check
    remote = run_cmd(["git", "remote", "-v"])
    branch = run_cmd(["git", "branch", "--show-current"])
    cwd = os.getcwd()
    
    print("[IDENTITY]")
    print(f"CWD: {cwd}")
    print(f"Branch: {branch}")
    print(f"Remote:\n{remote}\n")

    # 2. State Integration (Using Synthesis Logic)
    current = load_json(STATE_PATHS["current_state"])
    focus = load_json(STATE_PATHS["focus"])
    patterns = load_jsonl(STATE_PATHS["patterns"])
    anchors = load_jsonl(STATE_PATHS["anchors"])

    print("[COGNITIVE STATE]")
    if current:
        print(f"Cycle: {current.get('cycle', '?')} | Phase: {current.get('phase', '?')} | Status: {current.get('status', '?')}")
    else:
        print("No state file found.")

    if focus:
        print(f"Goal: {focus.get('current_goal', '?')} | Task: {focus.get('active_task', '?')}")
    else:
        print("No focus defined.")
    
    print(f"Memory Volume: Patterns({len(patterns)}) / Anchors({len(anchors)})\n")

    # 3. Git Delta Analysis
    log = run_cmd(["git", "log", "-n", "5", "--oneline"])
    print("[RECENT HISTORY]")
    print(f"{log}\n")

    # 4. Drift Detection (Simplified Self-Diagnostic)
    print("[DRIFT ANALYSIS]")
    drift_detected = False
    if current and current.get('cycle'):
        last_commit = run_cmd(["git", "log", "-1", "--pretty=%B"])
        expected_prefix = f"C{current['cycle']}"
        if not last_commit.startswith(expected_prefix):
            print(f"⚠️ DRIFT DETECTED: State cycle is {current['cycle']}, but last commit is '{last_commit}'")
            drift_detected = True
        else:
            print("✅ State and History are synchronized.")
    else:
        print("Unable to calculate drift: state file missing or invalid.")

    print(f"\n{'='*60}")
    print("PERCEPTION COMPLETE: System oriented for next cognitive loop.")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    orchestrate_perception()
