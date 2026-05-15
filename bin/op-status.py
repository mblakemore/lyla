#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:
        return {"error": str(e)}

def main():
    # Base path relative to the script location (assuming bin/ is at root)
    root = Path(__file__).parent.parent
    
    state = load_json(root / "state/current-state.json")
    focus = load_json(root / "state/focus.json")
    
    print("\n--- LYLA OPERATIONAL STATUS ---")
    print(f"Cycle:   {state.get('cycle', 'N/A')}")
    print(f"Phase:   {state.get('phase', 'N/A')}")
    print(f"Status:   {state.get('status', 'N/A')}")
    print(f"Action:  {state.get('last_action', 'N/A')}")
    print("-" * 30)
    print(f"Goal:    {focus.get('current_goal', 'N/A')}")
    print(f"Next:    {focus.get('next_milestone', 'N/A')}")
    print("-" * 30)
    
    patterns_path = root / "state/memories/patterns.jsonl"
    if patterns_path.exists():
        count = len(patterns_path.read_text().splitlines())
        print(f"Knowledge Base: {count} registered patterns")
    else:
        print("Knowledge Base: Not found")

    # Check for critical warnings in to-creator’s log
    to_creator = root / "messages/to-creator.md"
    if to_creator.exists():
        logs = to_creator.read_text()
        if "ERROR" in logs or "CRITICAL" in logs:
            print("\n⚠️ WARNING: Critical messages pending in messages/to-creator.md")

    print("-" * 30 + "\n")

if __name__ == "__main__":
    main()
