#!/usr/bin/env python3
"""
context_viewer.py — Operator-facing view of Lyla's observations about Creator's work state.

This addresses the friction point: "mostly blind to your context passing."
Instead of building more infrastructure, we surface existing knowledge in a human-readable format.

External-subject compliant: operator service artifact, not self-monitoring.
"""

import os
import json
from datetime import datetime


def read_context_trace():
    """Read context trace entries from JSONL file."""
    path = 'state/trace/context_trace.jsonl'
    if not os.path.exists(path):
        return []
    
    entries = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def format_entry(entry):
    """Format a single context entry for human reading."""
    timestamp = entry.get('timestamp', 'Unknown time')
    action_type = entry.get('action_type', 'unknown')
    confidence = entry.get('confidence', 0)
    
    # Extract key fields based on action type
    if action_type == 'file_read':
        details = entry.get('details', {})
        return (f"📄 Read: {details.get('path', 'N/A')} "
                f"(lines {details.get('start_line', '?')}-{details.get('end_line', '?')})")
    elif action_type == 'git_operation':
        details = entry.get('details', {})
        return f"🔧 Git: {details.get('command', 'unknown command')}"
    elif action_type == 'tool_execution':
        tool_name = entry.get('tool_name', 'unknown tool')
        args = entry.get('args', '')
        return f"⚙️ Tool: {tool_name} {' '.join(args)}"
    elif action_type in ['discord_message_received', 'message_received']:
        details = entry.get('details', {})
        author = details.get('author', 'Unknown')
        preview = details.get('message_preview', '')[:50] + ('...' if len(details.get('message_preview', '')) > 50 else '')
        return f"💬 From {author}: '{preview}'"
    elif action_type == 'intent_inference':
        inferred = entry.get('details', {}).get('inferred_intent', 'No intent specified')
        return f"🎯 Inferred intent: {inferred}"
    elif action_type == 'priority_update':
        new_priority = entry.get('details', {}).get('new_priority', 'N/A')
        rationale = entry.get('details', {}).get('rationale', '')[:60] + ('...' if len(entry.get('details', {}).get('rationale', '')) > 60 else '')
        return f"📌 Priority → {new_priority}\n   Rationale: {rationale}"
    else:
        # Generic fallback
        description = entry.get('description', '')
        if not description and 'details' in entry:
            # Try to summarize details dict
            desc_parts = []
            for k, v in entry['details'].items():
                if isinstance(v, str) and len(v) < 100:
                    desc_parts.append(f"{k}: {v}")
            description = '; '.join(desc_parts) if desc_parts else 'Event recorded'
        return f"{action_type}: {description} ({round(confidence * 100, 1)}% confident)"


def main():
    """Main entry point — show recent context entries to operator."""
    print("=" * 70)
    print(f"  LYLA CONTEXT OBSERVATIONS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    entries = read_context_trace()
    
    if not entries:
        print("\n⚠️ No context observations recorded yet.")
        print("   This is normal for early cycles. Context tracing will populate as you work.\n")
        return
    
    # Group by most recent first
    sorted_entries = sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    print(f"\n📊 Total observations tracked: {len(sorted_entries)}\n")
    
    # Show last N entries (default 10)
    for i, entry in enumerate(sorted_entries[:10], 1):
        timestamp = entry.get('timestamp', '?')[:19]  # Trim microseconds
        formatted = format_entry(entry)
        
        confidence = entry.get('confidence', 0)
        conf_marker = "✅" if confidence >= 0.8 else "⚠️" if confidence >= 0.5 else "❓"
        
        print(f"{i}. [{timestamp}] {conf_marker} {formatted}")
    
    if len(sorted_entries) > 10:
        print(f"\n... and {len(sorted_entries) - 10} more entries (see full trace at state/trace/context_trace.jsonl)")
    
    print("\n" + "-" * 70)
    print("  Context observations help me understand what you're working on.")
    print("  This view makes that knowledge visible to you — no abstraction layers.")
    print("-" * 70)


if __name__ == '__main__':
    main()
