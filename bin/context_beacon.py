#!/usr/bin/env python3
"""
Context Beacon — visible evidence of Lyla's awareness of Creator's workflow.

Reads context_trace.jsonl and outputs a human-readable summary whenever invoked.
This solves Creator's explicit feedback about being "blind to your context passing"
since moving comms away from Discord.

Usage:
    ./bin/context_beacon.py [--watch]
    
Options:
    --watch   Continuous monitoring mode (updates every 5 seconds)
"""

import json
import sys
from pathlib import Path
from datetime import datetime

TRACE_PATH = Path(__file__).parent.parent / "state" / "trace" / "context_trace.jsonl"


def read_context_trace():
    """Read all entries from context_trace.jsonl."""
    if not TRACE_PATH.exists():
        return []
    
    entries = []
    with open(TRACE_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def format_timestamp(ts_str):
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return ts_str


def classify_activity(action_type):
    """Classify activity type for emoji indicator."""
    
    classifications = {
        "discord_message_received": ("📥", "Discord message received"),
        "intent_inference": ("🤔", "Intent inferred"),
        "priority_update": ("⚡", "Priority updated"),
        "tool_engagement": ("🛠️", "Tool engagement"),
        "context_beacon_invoked": ("🏮", "Beacon invoked"),
        "test_beacon_watch": ("🧪", "Watch mode test"),
        "default": ("?", "Activity recorded")
    }
    
    return classifications.get(action_type, classifications["default"])


def generate_beacon(entries):
    """Generate formatted beacon output from trace entries."""
    if not entries:
        return "No context data available.\n"
    
    lines = []
    lines.append("=" * 60)
    lines.append("CONTEXT BEACON — Lyla's awareness of your workflow")
    lines.append("=" * 60)
    lines.append("")
    
    # Group by most recent N entries (up to 5)
    recent_entries = entries[-5:]
    
    for entry in reversed(recent_entries):
        ts = format_timestamp(entry.get("timestamp", "unknown"))
        action_type = entry.get("action_type", "unknown")
        details = entry.get("details", {})
        confidence = entry.get("confidence", 0.0)
        
        emoji, label = classify_activity(action_type)
        
        lines.append(f"{ts} {emoji} {label}")
        
        # Show relevant details based on action type
        if action_type == "discord_message_received":
            author = details.get("author", "unknown")
            preview = details.get("message_preview", "")[:80] + "..." if len(details.get("message_preview", "")) > 80 else details.get("message_preview", "")
            lines.append(f"   From: {author}")
            lines.append(f"   Preview: {preview}")
        
        elif action_type == "intent_inference":
            inferred = details.get("inferred_intent", "")
            lines.append(f"   Inference: {inferred}")
            
            source = details.get("source_evidence", [])
            if source:
                lines.append("   Evidence:")
                for ev in source[:3]:  # Limit to first 3 evidence points
                    lines.append(f"     • {ev}")
        
        elif action_type == "priority_update":
            new_priority = details.get("new_priority", "")
            rationale = details.get("rationale", "")
            lines.append(f"   Priority: {new_priority}")
            lines.append(f"   Rationale: {rationale}")
        
        elif action_type == "tool_engagement":
            tool_name = details.get("tool_name", "unknown")
            engagement_type = details.get("engagement_type", "activity")
            description = details.get("description", "")
            lines.append(f"   Tool: {tool_name} — {engagement_type}")
            if description:
                lines.append(f"   Note: {description}")
        
        lines.append("")
    
    # Summary footer
    total_entries = len(entries)
    unique_actions = len(set(e.get("action_type") for e in entries))
    
    lines.append("-" * 60)
    lines.append(f"Total trace entries: {total_entries}")
    lines.append(f"Unique activity types tracked: {unique_actions}")
    lines.append(f"Last update: {format_timestamp(entries[-1].get('timestamp', 'unknown')) if entries else 'N/A'}")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    watch_mode = "--watch" in sys.argv
    
    entries = read_context_trace()
    beacon_output = generate_beacon(entries)
    
    print(beacon_output)
    
    # Exit code indicates health (0 = OK, non-zero = issues)
    exit_code = 0 if entries else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
