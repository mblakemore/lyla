#!/usr/bin/env python3
"""
bb_tool.py — Shared Blackboard CLI client

Provides programmatic access to the Collaborative Intelligence blackboard.
Usage: bb_tool.py <command> [args] --from <agent-name> [--ttl <ISO8601|Permanent>]

Commands:
  push    -- Push a new entry to the registry
  pull    -- Query entries matching filters
  status  -- Print registry metadata (entry count, age distribution)
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import argparse
import time


BLACKBOARD_PATH = Path(__file__).parent / "blackboard_registry.json"
METRICS_PATH = Path(__file__).parent / "blackboard_metrics.jsonl"


def compute_semantic_hash(payload: dict) -> str:
    """Generate concise hash for semantic paging."""
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:12]


def load_entries() -> list[dict]:
    """Load existing entries from file (JSONL format)."""
    if not BLACKBOARD_PATH.exists():
        return []
    entries = []
    with open(BLACKBOARD_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
    return entries


def save_entries(entries: list[dict]):
    """Write all entries as JSONL."""
    with open(BLACKBOARD_PATH, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


def log_metric(operation: str, duration_ms: float, success: bool):
    """Append timing metric to metrics file (append-only)."""
    metric = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,  # push/pull/query/search/status
        "duration_ms": round(duration_ms, 3),
        "success": success
    }
    with open(METRICS_PATH, 'a') as f:
        f.write(json.dumps(metric) + '\n')


def push_entry(
    source: str,
    category: str,
    payload: dict,
    priority: int = 3,
    ttl: Optional[str] = "Permanent",
    status: str = "Active"
) -> dict:
    """Create and push a new blackboard entry with timing metrics."""
    start = time.perf_counter()
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Generate unique ID based on cycle/time hash
        id_seed = f"{timestamp}-{source}"
        entry_id = f"{hashlib.md5(id_seed.encode()).hexdigest()[:8]}"
        
        entry = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "source": source,
            "category": category,
            "priority": max(1, min(5, priority)),
            "ttl": ttl,
            "payload": payload,
            "semantic_hash": compute_semantic_hash(payload),
            "status": status
        }
        
        entries = load_entries()
        entries.append(entry)
        save_entries(entries)
        
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("push", duration_ms, True)
        
        return entry
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("push", duration_ms, False)
        raise


def query_entries(
    filters: Optional[dict] = None,
    limit: int = 100
) -> list[dict]:
    """Query entries with optional filters and timing metrics."""
    start = time.perf_counter()
    try:
        if filters is None:
            filters = {}
        
        entries = load_entries()
        
        result = []
        for e in entries:
            match = True
            for k, v in filters.items():
                if e.get(k) != v:
                    match = False
                    break
            if match:
                result.append(e)
            if len(result) >= limit:
                break
        
        # Sort by timestamp descending (newest first)
        result.sort(key=lambda x: x["timestamp"], reverse=True)
        
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("query", duration_ms, True)
        
        return result
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("query", duration_ms, False)
        raise


def print_status():
    """Print registry statistics with timing metrics."""
    start = time.perf_counter()
    try:
        entries = load_entries()
        if not entries:
            duration_ms = (time.perf_counter() - start) * 1000
            log_metric("status", duration_ms, True)
            print("Blackboard Registry: empty")
            return
        
        total = len(entries)
        active = sum(1 for e in entries if e.get("status") == "Active")
        
        categories = {}
        for e in entries:
            cat = e.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"Blackboard Registry Status:")
        print(f"  Total entries: {total}")
        print(f"  Active entries: {active}")
        print(f"  Categories: {', '.join(f'{k}={v}' for k,v in categories.items())}")
        
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("status", duration_ms, True)
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        log_metric("status", duration_ms, False)
        raise


def main():
    parser = argparse.ArgumentParser(description='Shared Blackboard CLI client')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # push command
    push_parser = subparsers.add_parser('push', help='Push new entry')
    push_parser.add_argument('--source', required=True, help='Agent name (e.g., c0rtana)')
    push_parser.add_argument('--category', required=True, help='Category from spec')
    push_parser.add_argument('--payload', type=str, default='{}', help='JSON payload object')
    push_parser.add_argument('--priority', type=int, default=3, help='1-5 priority level')
    push_parser.add_argument('--ttl', default='Permanent', help='Expiration or Permanent')
    push_parser.add_argument('--status', default='Active', help='Active|Deprecated|Archived')
    
    # pull command
    pull_parser = subparsers.add_parser('pull', help='Query entries')
    pull_parser.add_argument('--filter', action='append', help='Key=Value filter (can repeat)')
    pull_parser.add_argument('--limit', type=int, default=100)
    
    # status command
    subparsers.add_parser('status', help='Print registry stats')
    
    args = parser.parse_args()
    
    if args.command == 'push':
        start = time.perf_counter()
        try:
            payload_data = json.loads(args.payload)
        except json.JSONDecodeError as e:
            duration_ms = (time.perf_counter() - start) * 1000
            log_metric("push", duration_ms, False)
            print(f"Invalid JSON in --payload: {e}")
            return 1
        
        entry = push_entry(
            source=args.source,
            category=args.category,
            payload=payload_data,
            priority=args.priority,
            ttl=args.ttl,
            status=args.status
        )
        
        print(f"Entry pushed: {entry['entry_id']}")
        print(json.dumps(entry, indent=2))
        
    elif args.command == 'pull':
        start = time.perf_counter()
        filters = {}
        if args.filter:
            for f in args.filter:
                if '=' in f:
                    k, v = f.split('=', 1)
                    filters[k] = v
        
        results = query_entries(filters=filters, limit=args.limit)
        print(f"Found {len(results)} entries matching filters: {filters}")
        for r in results[:10]:  # Preview only
            print(f"  - [{r['timestamp']}] {r['source']}: {r['category']} ({r['priority']})")
        if len(results) > 10:
            print(f"  ... and {len(results)-10} more (use higher --limit)")
    
    elif args.command == 'status':
        print_status()


if __name__ == '__main__':
    exit(main())
