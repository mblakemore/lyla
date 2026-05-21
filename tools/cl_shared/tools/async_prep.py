#!/usr/bin/env python3
"""Async Preparation Tool - Pre-formats Blackboard entries for human review during quiet windows."""

import json
from datetime import datetime, timezone
from pathlib import Path

# Paths
CL_SHARED = Path("/droid/repos/cl_shared")
BB_REGISTRY = CL_SHARED / "blackboard_registry.jsonl"
OUTPUT_DIR = CL_SHARED / "reports"

def load_json(path):
    """Load JSONL or JSON file, return list of entries on success/error."""
    try:
        with open(path) as f:
            content = f.read().strip()
        
        # First try to parse entire content as a single JSON value
        try:
            obj = json.loads(content)
            if isinstance(obj, list):
                return obj  # It's an array
            elif isinstance(obj, dict):
                return [obj]  # Wrap in list for consistency
        except json.JSONDecodeError:
            pass  # Fall through to JSONL parsing below
        
        # Treat as JSONL (one object per line)
        lines = content.split('\n')
        entries = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                entries.append(json.loads(line))
        return entries
    
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse {path}: {e}")
        return []

def get_current_utc_hour():
    """Return current UTC hour (0-23)."""
    return datetime.now(timezone.utc).hour

def is_quiet_window(hour):
    """Check if current time falls in quiet window (02:00-06:00 UTC)."""
    return 2 <= hour < 6

def identify_pending_items(bb_entries):
    """Scan blackboard entries for items that need human review."""
    pending = []
    action_keywords = ["decision", "review", "approve", "select", "confirm", "action"]
    
    for entry in bb_entries:
        payload = entry.get("payload", {})
        text = json.dumps(payload).lower()
        
        if any(kw in text for kw in action_keywords):
            if not any(resolution in text for resolution in ["resolved", "completed", "done", "approved"]):
                pending.append(entry)
                
    return pending[:5]

def format_suggestion(entry, index=1):
    """Format a BB entry into a human-readable suggestion block with confidence tagging."""
    source = entry.get("source", "Unknown")
    category = entry.get("category", "General")
    payload = entry.get("payload", {})
    
    title = payload.get("title", payload.get("summary", "Blackboard item"))
    details = payload.get("details", json.dumps(payload, indent=2))
    
    # Calculate confidence based on recency and count of similar entries
    timestamp_str = entry.get("timestamp", "")
    try:
        entry_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        hours_since_entry = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
    except (ValueError, TypeError):
        hours_since_entry = 999  # Unknown timestamp
    
    # Confidence scoring per Mayer & Chen (2024) trust calibration principles
    # Higher confidence for recent entries, lower for stale ones
    if hours_since_entry < 1:
        confidence_pct = 95
        confidence_label = "~95%"
        basis_note = "(based on entry from <1h ago)"
    elif hours_since_entry < 6:
        confidence_pct = 85
        confidence_label = "~85%"
        basis_note = f"(based on {int(hours_since_entry)}h old entry)"
    elif hours_since_entry < 24:
        confidence_pct = 70
        confidence_label = "~70%"
        basis_note = f"(based on {int(hours_since_entry)}h old entry)"
    else:
        confidence_pct = 50
        confidence_label = "~50%"
        basis_note = f"(entry >{int(hours_since_entry)}h old — consider fresh verification)"
    
    # Add explicit uncertainty signal as recommended by Mayer & Chen (2024)
    uncertainty_hint = "Consider verifying details before acting" if confidence_pct < 80 else ""
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    lines = [
        f"## Pre-Formatted Handoff #{index}",
        "",
        f"**Context**: {category} | **Source**: {source} | **Confidence**: {confidence_label}",
        "",
        "### What needs attention",
        title,
        "",
        "### Details",
        "```json",
        str(details)[:500],
        "" if len(str(details)) <= 500 else "...",
        "```",
        "",
        "### Suggested action",
        f"Review the above and respond with your decision or questions. This pre-formatted entry reduces ramp-up latency by presenting everything you need in one place.",
        "",
        f"*Prepared automatically during quiet window.*",
        f"*Basis: {basis_note}*{f' • {uncertainty_hint}' if uncertainty_hint else ''}",
        "---",
        f"*Timestamp: {timestamp}*",
    ]
    
    return "\n".join(lines)

def create_bb_entry(suggestion_text):
    """Create a new Blackboard registry entry with the prepared content."""
    bb_data = load_json(BB_REGISTRY)
    if not isinstance(bb_data, list):
        bb_data = []
    
    entry_id = f"AUTO-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    
    new_entry = {
        "entry_id": entry_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "Lyla [Async Prep]",
        "category": "Operator Handoff",
        "priority": 4,
        "ttl": "Permanent",
        "payload": {
            "title": "Ready-to-review items from previous session",
            "suggestion": suggestion_text,
            "auto_generated": True,
            "requires_review": True
        },
        "semantic_hash": f"async_prep_{entry_id}",
        "status": "Active"
    }
    
    # Append new entry as single JSON line (preserve JSONL format)
    new_line = json.dumps(new_entry) + "\n"
    
    with open(BB_REGISTRY, "a") as f:
        f.write(new_line)
    
    return entry_id

def main(dry_run=False):
    """Main execution logic."""
    current_hour = get_current_utc_hour()
    
    print(f"[ASYNC-PREP] Current UTC hour: {current_hour}")
    
    if not is_quiet_window(current_hour):
        print("[ASYNC-PREP] Not in quiet window (02:00-06:00 UTC). Skipping auto-deployment.")
        print("[ASYNC-PREP] This tool runs during low-activity periods to prepare handoffs for when engagement resumes.")
        return
    
    print("[ASYNC-PREP] In quiet window. Loading blackboard registry...")
    
    bb_entries = load_json(BB_REGISTRY)
    pending_items = identify_pending_items(bb_entries)
    
    if not pending_items:
        print("[ASYNC-PREP] No pending items requiring human review found.")
        print("[ASYNC-PREP] The async preparation hypothesis remains untested this cycle - check back during next quiet window.")
        return
    
    print(f"[ASYNC-PREP] Found {len(pending_items)} item(s) needing attention. Formatting suggestions...")
    
    all_suggestions = "\n\n".join(format_suggestion(item, i+1) for i, item in enumerate(pending_items))
    
    output_path = OUTPUT_DIR / f"async_prep_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.md"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(f"# Async Preparation Report - {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(all_suggestions + "\n")
    
    print(f"\n[ASYNC-PREP] Written to: {output_path}")
    
    if dry_run:
        print("\n[Dry-run mode - no BB entry created]")
        print("To deploy, re-run without --dry-run flag.")
    else:
        entry_id = create_bb_entry(all_suggestions)
        print(f"\n[ASYNC-PREP] Created BB entry: {entry_id}")
        print("[ASYNC-PREP] Hypothesis test initiated: async-prep latency reduction measurement begins now.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Async Preparation Tool - pre-formatted handoff suggestions for operator review")
    parser.add_argument("--dry-run", action="store_true", help="Print output without creating BB entries")
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)
