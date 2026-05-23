#!/usr/bin/env python3
"""
Context Dashboard CLI — presents operator-focused summary of Lyla's knowledge about Creator's current work state.

Reads from state/memories/context_trace.jsonl (one JSON object per line).
Outputs synthesized view of tracked workflow observations.

Usage:
  python bin/context_dashboard.py           # Show latest entries
  python bin/context_dashboard.py --recent N # Show last N entries  
  python bin/context_dashboard.py --type CONTEXT|ACTION|QUESTION  # Filter by type
"""

import json
import sys
from datetime import datetime
from pathlib import Path

TRACE_FILE = Path(__file__).parent.parent / "state" / "memories" / "context_trace.jsonl"

def load_entries(limit=None):
    """Load context trace entries from JSONL file."""
    if not TRACE_FILE.exists():
        return []
    
    entries = []
    with open(TRACE_FILE, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):  # Skip empty lines and comments
                continue
            try:
                entry = json.loads(stripped)
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    
    if limit:
        return entries[-limit:]
    return entries

def format_entry(entry):
    """Format a single entry for display."""
    timestamp = entry.get('timestamp', 'Unknown time')
    entry_type = entry.get('type', 'unknown').upper()
    content = entry.get('content', '')
    
    formatted_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
    
    type_colors = {
        'CONTEXT': '\x1b[36m',      # Cyan
        'ACTION': '\x1b[32m',       # Green  
        'QUESTION': '\x1b[33m',     # Yellow
        'DEFAULT': '\x1b[94m'       # Blue
    }
    color = type_colors.get(entry_type, type_colors['DEFAULT'])
    reset = '\x1b[0m'
    
    return f"{color}┌─────────────────────────────────────┐{reset}\n" \
           f"{color}| {formatted_time} |{reset}\n" \
           f"{color}| [{entry_type.ljust(8)}]          |{reset}\n" \
           f"{color}└─────────────────────────────────────┘{reset}\n\n" \
           f"{content}\n"

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lyla Context Dashboard — operator workflow visibility')
    parser.add_argument('--recent', '-r', type=int, help='Show only last N entries')
    parser.add_argument('--type', '-t', choices=['CONTEXT', 'ACTION', 'QUESTION'], help='Filter by entry type')
    parser.add_argument('--json', action='store_true', help='Output as JSON instead of formatted text')
    args = parser.parse_args()
    
    entries = load_entries(limit=args.recent)
    
    if args.type:
        entries = [e for e in entries if e.get('type') == args.type]
    
    if not entries:
        print("No context entries found.")
        print("\nTo start tracking your workflow:")
        print("  1. Use the HTML viewer at visualization/context_viewer.html")
        print("  2. Or append entries to state/memories/context_trace.jsonl manually")
        sys.exit(0)
    
    if args.json:
        print(json.dumps(entries, indent=2))
    else:
        # Group by type for better readability
        by_type = {'CONTEXT': [], 'ACTION': [], 'QUESTION': []}
        for entry in entries:
            t = entry.get('type', 'unknown').upper()
            if t in by_type:
                by_type[t].append(entry)
        
        print("=" * 60)
        print("     LYLA CONTEXT DASHBOARD")
        print(f"     {len(entries)} entries tracked")
        print("=" * 60 + "\n")
        
        for etype in ['CONTEXT', 'ACTION', 'QUESTION']:
            if by_type[etype]:
                print(f"\n{'─' * 40}")
                print(f"  {etype}")
                print(f"{'─' * 40}\n")
                
                for entry in by_type[etype]:
                    print(format_entry(entry))
        
        print("\n" + "=" * 60)
        print("Next cycle recommendation:")
        print("  - Review ACTION entries — these are moments where I observed friction")
        print("  - Consider engaging with QUESTION entries to calibrate my understanding")
        print("  - Use HTML viewer (visualization/context_viewer.html) for full history")
        print("=" * 60)

if __name__ == '__main__':
    main()
