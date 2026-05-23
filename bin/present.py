#!/usr/bin/env python3
"""
present.py - Minimal viable embodied presence indicator

Polls state/current-state.json every 3 seconds and displays:
- Current phase as color-coded prefix
- Confidence level as emoji tag [HIGH/MEDIUM/LOW]  
- One-line summary of current focus

Usage: python3 bin/present.py [--once | --continuous]
  --once    : Show status once, then exit (for CI/testing)
  --continuous (default): Keep running until Ctrl+C
"""

import json
import os
import sys
import time
from datetime import datetime

# Colors for phases (ANSI escape codes)
PHASE_COLORS = {
    "PERCEIVE": "\033[94m",    # Blue
    "REFLECT": "\033[93m",     # Yellow/Gold
    "DECIDE": "\033[95m",      # Magenta
    "ACT": "\033[92m",         # Green
    "CONSOLIDATE": "\033[96m", # Cyan
    "PERSIST": "\033[91m",     # Red
    "COMPLETE": "\033[97m",    # White
}

RESET = "\033[0m"

STATE_FILE = "state/current-state.json"


def load_state():
    """Load and parse current-state.json."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def get_confidence_emoji(confidence):
    """Map confidence score to emoji tag."""
    if confidence is None:
        return "❓"
    if confidence >= 0.8:
        return "🟢 HIGH"
    elif confidence >= 0.5:
        return "🟡 MEDIUM"
    else:
        return "🔴 LOW"


def display_status(state, once=False):
    """Display the presence indicator status."""
    phase = state.get("phase", "UNKNOWN")
    focus = state.get("current_focus", "No active focus")
    completed_at = state.get("completed_at", "")
    
    color = PHASE_COLORS.get(phase, RESET)
    emoji = get_confidence_emoji(state.get("confidence"))
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Clear screen for continuous mode (creates visual rhythm)
    if not once:
        print("\033[2J\033[H", end="")
    
    line1 = f"{color}● {phase}{RESET} | {emoji} | {focus}"
    line2 = f"   Updated: {timestamp} | Cycle: C{state.get('cycle', '?')}"
    
    print(line1)
    print(line2)
    
    if once:
        sys.stdout.flush()


def main():
    """Main entry point."""
    once = "--once" in sys.argv
    
    if not os.path.exists(STATE_FILE):
        print(f"Error: {STATE_FILE} not found. Run from repo root.", file=sys.stderr)
        sys.exit(1)
    
    if once:
        # Show once and exit
        state = load_state()
        if state is None:
            print("Error: Could not parse state file", file=sys.stderr)
            sys.exit(1)
        display_status(state, once=True)
        return
    
    # Continuous polling mode
    print(f"Present running. Ctrl+C to stop.")
    print(f"Polling every 3 seconds... Press Enter after each cycle to force refresh.\n")
    
    last_update = time.time()
    
    try:
        while True:
            now = time.time()
            
            # Force refresh on Enter press (simple UX for operator feedback)
            if sys.stdin.isatty():
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read()
                    last_update = 0  # Force immediate reload
            
            if now - last_update >= 3 or last_update == 0:
                state = load_state()
                if state:
                    display_status(state, once=False)
                    last_update = now
            
            time.sleep(0.5)  # Check stdin frequently for Enter press
            
    except KeyboardInterrupt:
        print("\n\nStopped.", RESET)


if __name__ == "__main__":
    main()
