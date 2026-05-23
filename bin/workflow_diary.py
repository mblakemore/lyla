#!/usr/bin/env python3
"""
Operator Workflow Diary — log coordination frictions in real-time during work sessions.

Usage:
    python workflow_diary.py log --category CATEGORY [--severity N] "description"
    python workflow_diary.py list           # Show recent entries
    python workflow_diary.py export         # Export as JSONL to stdout

Categories:
    coordination-friction, tooling-gap, context-mismatch, timing-issue, content-relevance

Severity: 1-5 (1 = minor annoyance, 5 = workflow-blocking)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

DIARY_PATH = Path("logs/operator_diary.jsonl")
CATEGORIES = [
    "coordination-friction",
    "tooling-gap", 
    "context-mismatch",
    "timing-issue",
    "content-relevance"
]


def ensure_log_dir():
    """Create logs directory if it doesn't exist."""
    DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_entry(category: str, description: str, severity: int = 3):
    """Append a new friction entry to the diary."""
    if category not in CATEGORIES:
        print(f"Error: Invalid category '{category}'. Valid options: {', '.join(CATEGORIES)}")
        return False
    
    if not (1 <= severity <= 5):
        print("Error: Severity must be between 1 and 5.")
        return False
    
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "category": category,
        "severity": severity,
        "description": description,
        "source": "operator_workflow_diary"
    }
    
    ensure_log_dir()
    with open(DIARY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"Logged [{category}] severity-{severity}: {description}")
    return True


def list_entries(limit: int = 10):
    """Display recent entries from the diary."""
    if not DIARY_PATH.exists():
        print("No entries found. Use 'log' command to record frictions.")
        return
    
    entries = []
    with open(DIARY_PATH, "r") as f:
        for line in f:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    
    if not entries:
        print("Diary is empty.")
        return
    
    # Show most recent first
    for entry in reversed(entries[-limit:]):
        ts = entry["timestamp"][:19].replace("T", " ")
        print(f"[{ts}] [{entry['category']}] S{entry['severity']}: {entry['description']}")


def export_entries(format_type: str = "jsonl"):
    """Export all entries to stdout."""
    if not DIARY_PATH.exists():
        print("No entries to export.")
        return
    
    with open(DIARY_PATH, "r") as f:
        content = f.read()
    
    if format_type == "jsonl":
        print(content)
    elif format_type == "json":
        entries = []
        for line in content.strip().split("\n"):
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        print(json.dumps(entries, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Operator Workflow Diary — log coordination frictions")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Log command
    log_parser = subparsers.add_parser("log", help="Log a new friction entry")
    log_parser.add_argument("--category", "-c", required=True, choices=CATEGORIES,
                           help="Friction category")
    log_parser.add_argument("--severity", "-s", type=int, default=3,
                           help="Severity 1-5 (default: 3)")
    log_parser.add_argument("description", nargs="?", help="Brief description of the friction")
    
    # List command
    list_parser = subparsers.add_parser("list", help="Show recent entries")
    list_parser.add_argument("--limit", "-n", type=int, default=10,
                            help="Number of entries to show (default: 10)")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export entries to stdout")
    export_parser.add_argument("--format", "-f", choices=["jsonl", "json"], default="jsonl",
                              help="Output format (default: jsonl)")
    
    args = parser.parse_args()
    
    if args.command == "log":
        if not args.description:
            print("Error: Description required for logging.")
            return 1
        success = log_entry(args.category, args.description, args.severity)
        return 0 if success else 1
    
    elif args.command == "list":
        list_entries(args.limit)
        return 0
    
    elif args.command == "export":
        export_entries(args.format)
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    exit(main())
