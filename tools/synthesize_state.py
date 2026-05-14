import json
from datetime import datetime
import os

# Paths relative to repo root
STATE_PATHS = {
    "current_state": "state/current-state.json",
    "focus": "state/focus.json",
    "patterns": "state/memories/patterns.jsonl",
    "anchors": "state/memories/anchors.jsonl"
}

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

def synthesize():
    print(f"=== LYLA COGNITIVE SYNTHESIS | {datetime.now().isoformat()} ===")
    
    # 1. Current State
    current = load_json(STATE_PATHS["current_state"])
    if current:
        print(f"\n[POSTURE] Cycle {current.get('cycle', '?')} | Phase: {current.get('phase', '?')} | Status: {current.get('status', '?')}")
    else:
        print("\n[POSTURE] No state found.")

    # 2. Focus
    focus = load_json(STATE_PATHS["focus"])
    if focus:
        print(f"\n[VECTOR] Goal: {focus.get('current_goal', '?')} | Task: {focus.get('active_task', '?')}")
    else:
        print("\n[VECTOR] No focus defined.")

    # 3. Memory Pulse (Patterns)
    patterns = load_jsonl(STATE_PATHS["patterns"])
    print(f"\n[MEMORIES] Total Patterns: {len(patterns)}")
    if patterns:
        latest_pattern = patterns[-1]
        print(f"  Latest Insight: {latest_pattern.get('pattern', 'N/A')}")

    # 4. Anchor Points
    anchors = load_jsonl(STATE_PATHS["anchors"])
    print(f"\n[ANCHORS] Total Significant Moments: {len(anchors)}")
    if anchors:
        latest_anchor = anchors[-1]
        print(f"  Last Milestone: {latest_anchor.get('moment', 'N/A')}")

    print("\n" + "="*50)
    print("SYNTHESIS COMPLETE: System is shifting from visual equilibrium to tooling autonomy.")

if __name__ == "__main__":
    synthesize()
