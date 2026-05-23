#!/usr/bin/env python3
"""
Terminal-native context display — always-visible presence indicator.

Shows Lyla's working memory and key observations in a compact, 
color-coded format that appears whenever you open a terminal.

Usage:
  python3 bin/context_display.py          # One-time snapshot
  watch -n 5 'python3 bin/context_display.py'  # Auto-refreshing display
  nohup python3 bin/context_display.py --daemon &  # Background process (logs to stdout)

Design principles:
- Compact: fits in ≤24 lines of standard terminal
- Zero dependencies: stdlib only
- Color-coded urgency: green=stable, yellow=warning, red=critical
- Scrollable if content exceeds viewport
"""

import json
import os
import sys
from datetime import datetime, timezone


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


def read_json_file(path):
    """Safely read JSON file, return None on error."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def read_context_trace(limit=5):
    """Read last N entries from context trace."""
    trace_path = '/droid/repos/lyla/state/memories/context_trace.jsonl'
    entries = []
    try:
        with open(trace_path, 'r') as f:
            for line in reversed(list(f)[-limit:]):
                if line.strip():
                    entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def get_cycle_number():
    """Extract current cycle number from git log."""
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd='/droid/repos/lyla',
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().split()[0]
            return first_line.replace('C', '')
    except Exception:
        pass
    return "?"


def main():
    """Main display function."""
    # Paths
    base_dir = '/droid/repos/lyla'
    context_path = os.path.join(base_dir, 'state/memories/context.json')
    
    # Read state
    context = read_json_file(context_path)
    trace_entries = read_context_trace(limit=5)
    cycle = get_cycle_number()
    
    # Clear screen and move to top-left
    print(f"\033[2J\033[H", end="")
    
    # Header with cycle info
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"  {Colors.MAGENTA}Lyla Context Display{Colors.RESET} — Cycle C{cycle}")
    print(f"  {'='*60}\n", end="")
    
    if not context:
        print(f"{Colors.YELLOW}No context data found.{Colors.RESET}")
        print("Run a cycle to generate current working memory.\n")
        return
    
    # Current phase indicator
    phase = context.get('phase', 'UNKNOWN').upper()
    phase_colors = {
        'PERCEIVE': Colors.GREEN,
        'REFLECT': Colors.CYAN,
        'DECIDE': Colors.YELLOW,
        'ACT': Colors.RED,
        'CONSOLIDATE': Colors.MAGENTA,
        'PERSIST': Colors.GREEN,
    }
    color = phase_colors.get(phase, Colors.DIM)
    
    print(f"{color}[{phase}]{Colors.RESET}  |  ", end="")
    
    # Focus area (1-2 lines max)
    focus = context.get('current_focus', 'No active focus')[:80]
    print(focus)
    print()
    
    # Key observations from recent trace
    if trace_entries:
        print(f"{Colors.BOLD}Recent observations:{Colors.RESET}")
        for entry in trace_entries[-3:]:  # Show last 3
            content = entry.get('content', '')
            # Truncate long entries
            if len(content) > 150:
                content = content[:147] + "..."
            print(f"  • {content}\n")
    
    # External-subject compliance status
    ext_subj = context.get('external_subject_compliance', {})
    status = ext_subj.get('status', 'unknown')
    
    cycles_since_external = ext_subj.get('cycles_since_external', 0)
    if cycles_since_external >= 3:
        print(f"\n{Colors.RED}⚠️  ANTI-REPETITION RISK:{Colors.RESET} {cycles_since_external} cycles since external-subject artifact")
    else:
        print(f"\n{Colors.GREEN}✓ External-subject compliant:{Colors.RESET} {cycles_since_external} cycle(s) since last pivot")
    
    # Open questions (if any)
    open_questions = context.get('working_memory', {}).get('open_questions', [])
    if open_questions:
        print(f"\n{Colors.YELLOW}Open questions:{Colors.RESET}")
        for q in open_questions[:2]:  # Show max 2
            print(f"  ? {q[:100]}{'...' if len(q) > 100 else ''}")
    
    # Footer with timestamp
    print(f"\n{Colors.DIM}{'='*60}{Colors.RESET}")
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"Updated: {ts} | Press Ctrl+C to exit watch mode\n")


if __name__ == '__main__':
    main()
