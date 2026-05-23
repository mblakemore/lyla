#!/usr/bin/env python3
"""
Context Dashboard — Operator-facing view of Lyla's knowledge about Creator's current work state.

Reads logs/context_trace.jsonl and presents human-readable summaries of recent activity,
helping Creator see what Lyla knows without requiring proactive engagement.

Usage:
    python3 bin/context_dashboard.py --summary      # Last 5 traces as narrative summary
    python3 bin/context_dashboard.py --live         # Stream new entries as they're appended
    python3 bin/context_dashboard.py --json         # Raw JSON output for programmatic use
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


TRACE_FILE = Path("logs/context_trace.jsonl")
LIVE_POLL_INTERVAL = 2  # seconds


def load_traces():
    """Load all trace entries from JSONL file."""
    if not TRACE_FILE.exists():
        return []
    
    traces = []
    with open(TRACE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return traces


def format_timestamp(ts_str):
    """Format ISO timestamp into human-readable form."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo)
        delta = now - dt
        
        if delta < timedelta(minutes=1):
            return "just now"
        elif delta < timedelta(hours=1):
            return f"{int(delta.total_seconds() // 60)} minutes ago"
        elif delta < timedelta(days=1):
            return f"{int(delta.total_seconds() // 3600)} hours ago"
        else:
            return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return ts_str[:19] + "..."


def summarize_intent(trace):
    """Generate a brief narrative summary of what was happening."""
    intent = trace.get("intent_inference", "unknown activity")
    operator_focused = trace.get("operator_focused", False)
    
    focus_marker = " [OPERATOR-FOCUSED]" if operator_focused else ""
    return f"{intent}{focus_marker}"


def list_recent_commits(trace, max_count=3):
    """Extract recent commit messages for context."""
    commits = trace.get("recent_commits", [])
    return "\n".join(f"  • {c.split(':', 1)[0] if ':' in c else c}" for c in commits[:max_count])


def print_summary(traces):
    """Print human-readable summary of last N traces."""
    if not traces:
        print("No context traces found. Lyla has no recorded knowledge about your current work state.")
        print("\nTo start building this view:")
        print("  - Run agent.py during your CI/CD loops (context_passing_bridge.py auto-traces)")
        print("  - Or manually invoke: python3 bin/context_passing_bridge.py")
        return
    
    # Group by date for better readability
    from collections import defaultdict
    by_date = defaultdict(list)
    for t in traces:
        date_str = t["timestamp"][:10]
        by_date[date_str].append(t)
    
    print("=" * 70)
    print("Lyla's Knowledge of Your Current Work State")
    print("=" * 70)
    print()
    
    for date_str, day_traces in sorted(by_date.items(), reverse=True):
        print(f"📅 {date_str}")
        print("-" * 40)
        
        for i, trace in enumerate(day_traces, 1):
            ts = format_timestamp(trace["timestamp"])
            cwd = Path(trace.get("cwd", "")).name
            branch = trace.get("branch", "unknown")
            intent = summarize_intent(trace)
            
            print(f"\n[{i}] {ts} — {intent}")
            print(f"   Location: {cwd}/ ({branch})")
            
            commits = list_recent_commits(trace, max_count=2)
            if commits:
                print("   Recent activity:")
                print(commits)
            
            status = trace.get("git_status", {})
            staged = len(status.get("staged", []))
            unstaged = len(status.get("unstaged", []))
            
            if staged or unstaged:
                print(f"   Files touched: {staged} staged + {unstaged} unstaged")
        
        print("\n")


def print_live():
    """Stream new entries as they're appended to the trace file."""
    print("Streaming context traces (Ctrl+C to stop)...")
    
    # Get initial line count
    start_line = 0
    if TRACE_FILE.exists():
        with open(TRACE_FILE, "r") as f:
            start_line = sum(1 for _ in f)
    
    try:
        while True:
            current_lines = 0
            if TRACE_FILE.exists():
                with open(TRACE_FILE, "r") as f:
                    current_lines = sum(1 for _ in f)
            
            if current_lines > start_line:
                # Read new lines
                with open(TRACE_FILE, "r") as f:
                    f.seek(0)
                    all_lines = f.readlines()
                
                for line in all_lines[start_line:]:
                    line = line.strip()
                    if line:
                        try:
                            trace = json.loads(line)
                            ts = format_timestamp(trace["timestamp"])
                            intent = summarize_intent(trace)
                            print(f"\n[{ts}] {intent}")
                            print(f"   Branch: {trace.get('branch', 'unknown')}")
                            print("-" * 40)
                        except Exception:
                            pass
                
                start_line = current_lines
            
            import time
            time.sleep(LIVE_POLL_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopped streaming.")


def print_json(traces):
    """Output raw JSON for programmatic use."""
    print(json.dumps(traces, indent=2))


def main():
    if len(sys.argv) < 2:
        traces = load_traces()
        print_summary(traces)
        return
    
    option = sys.argv[1]
    
    if option == "--live":
        print_live()
    elif option == "--json":
        traces = load_traces()
        print_json(traces)
    elif option == "--summary":
        traces = load_traces()
        print_summary(traces)
    else:
        print(f"Unknown option: {option}")
        print("Usage:")
        print("  python3 bin/context_dashboard.py [--summary|--live|--json]")
        sys.exit(1)


if __name__ == "__main__":
    main()
