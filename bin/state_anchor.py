#!/usr/bin/env python3
"""
State Anchor — Minimal JSONL persistence layer for operator context.

Addresses Creator's C303 feedback point #3: "foundational real-world persistence, not holographic"

Usage:
  python bin/state_anchor.py save    — Save current context to disk
  python bin/state_anchor.py restore — Read last saved context
  python bin/state_anchor.py status  — Show last write timestamp

Context format (JSONL):
  {
    "timestamp": "2026-05-23T16:40:00Z",
    "cycle": 329,
    "phase": "ACT",
    "file_path": "/droid/repos/lyla/bin/state_anchor.py",
    "line_number": null,
    "notes": "Saving state before deployment"
  }
"""

import json
from pathlib import Path
from datetime import datetime, timezone


CONTEXT_FILE = Path(__file__).parent.parent / "state/context_trace.jsonl"


def load_state() -> dict:
    """Load current in-memory state from current-state.json."""
    state_file = Path(__file__).parent.parent / "state/current-state.json"
    if not state_file.exists():
        return {}
    with open(state_file) as f:
        return json.load(f)


def save_context(notes: str = ""):
    """Append current context to JSONL trace file."""
    state = load_state()
    
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": state.get("cycle", 0),
        "phase": state.get("phase", ""),
        "notes": notes,
        "file_path": None,  # Would need filesystem integration for cursor tracking
        "line_number": None
    }
    
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONTEXT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"✓ Context saved: cycle={entry['cycle']}, phase={entry['phase']}")
    return entry["timestamp"]


def restore_last():
    """Read the most recent context entry."""
    if not CONTEXT_FILE.exists():
        print("No saved context found.")
        return None
    
    with open(CONTEXT_FILE) as f:
        lines = f.readlines()
    
    if not lines:
        print("Context file is empty.")
        return None
    
    last_entry = json.loads(lines[-1].strip())
    print(json.dumps(last_entry, indent=2))
    return last_entry


def status():
    """Show last write timestamp and count."""
    if not CONTEXT_FILE.exists():
        print("No context trace file found.")
        return
    
    with open(CONTEXT_FILE) as f:
        lines = f.readlines()
    
    if not lines:
        print("Context file is empty.")
        return
    
    last_ts = json.loads(lines[-1])["timestamp"]
    print(f"Last context save: {last_ts}")
    print(f"Total entries: {len(lines)}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "save":
        notes = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        save_context(notes)
    
    elif command == "restore":
        restore_last()
    
    elif command == "status":
        status()
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: state_anchor.py [save|restore|status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
