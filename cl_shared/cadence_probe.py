#!/usr/bin/env python3
"""
Cadence Probe CLI - Coordination latency/throughput analysis tool.

Adopts bb_perf_probe.py schema as shared contract (Option A alignment).
Analyzes inter-agent coordination rhythm rather than API performance metrics.

Commands:
  write <source> <timestamp> --tag <category>   Record new cadence entry to registry
  read [--limit N]                              Read recent entries
  report                                        Generate cadence analysis report
  probe                                         Measure current wall-clock timing vs baseline
  
This serves external-subject compliance: we're measuring the Coordination Protocol
that both agents use, not self-monitoring. The subject is the shared infrastructure.

Schema adopted from bb_perf_probe.py v1.0:
{
  "entry_id": "<cycle>-<serial>",
  "timestamp": "ISO8601",
  "source": "Lyla | C0rtana | cadence",
  "category": "[Architecture|Goal|Observation|TechnicalDebt|EnvironmentalState|Cadence]",
  "priority": "1-5",
  "ttl": "Permanent | ISO8601 expiration date",
  "payload": { "... context details ..."},
  "semantic_hash": "Condense summary string",
  "status": "Active | Deprecated | Archived"
}
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse
import hashlib
import statistics

BB_REGISTRY_PATH = Path(__file__).parent / "blackboard_registry.json"


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse various timestamp formats used in BB entries."""
    if not ts_str:
        return None
    
    ts_clean = ts_str.replace("Z", "+00:00")
    
    # Handle timezone with seconds (trim to hours only for compatibility)
    if "+" in ts_clean and ":" not in ts_clean.split("+")[-1]:
        tz_part = ts_clean.split("+")[-1].split("-")[0]
        ts_clean = ts_clean.rsplit("+", 1)[0] + "+" + tz_part[:3]
    
    try:
        return datetime.fromisoformat(ts_clean)
    except ValueError as e:
        print(f"Warning: Could not parse timestamp '{ts_str}': {e}")
        return None


def load_entries() -> list[dict]:
    """Load all entries from blackboard_registry.json (JSONL format)."""
    entries = []
    if not BB_REGISTRY_PATH.exists():
        return entries
    
    with open(BB_REGISTRY_PATH, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Malformed JSON on line {line_num}: {e}")
    return entries


def save_entry(entry: dict) -> bool:
    """Append a new entry to the registry."""
    # Generate entry_id from timestamp + serial if missing
    if "entry_id" not in entry or not entry["entry_id"]:
        ts_base = entry.get("timestamp", datetime.now(timezone.utc).isoformat())
        entry["entry_id"] = f"CAD_{datetime.fromisoformat(ts_base.replace('Z','')).strftime('%H%M%S')}"
    
    with open(BB_REGISTRY_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"Entry recorded: {entry['entry_id']} at {entry.get('timestamp', 'N/A')}")
    return True


def compute_cadence_metrics(entries: list[dict]) -> tuple[float, float, float]:
    """Compute cadence-specific metrics from historical entries."""
    latencies_ms = []
    
    sorted_entries = [e for e in entries if (ts := parse_timestamp(e.get("timestamp", ""))) is not None]
    sorted_entries.sort(key=lambda e: e["timestamp"])
    
    for i in range(1, len(sorted_entries)):
        ts_prev = parse_timestamp(sorted_entries[i-1]["timestamp"])
        ts_curr = parse_timestamp(sorted_entries[i]["timestamp"])
        
        if ts_prev and ts_curr:
            delta_seconds = (ts_curr - ts_prev).total_seconds()  # seconds this time for cadence
            latencies_ms.append(delta_seconds)
    
    if not latencies_ms:
        return (0.0, 0.0, 0.0)
    
    mean_lat = statistics.mean(latencies_ms)
    p50_lat = sorted(latencies_ms)[len(latencies_ms)//2]
    p90_lat = sorted(latencies_ms)[int(len(latencies_ms)*0.9)] if len(latencies_ms) > 10 else mean_lat * 1.5
    
    return (mean_lat, p50_lat, p90_lat)


def generate_report():
    """Generate cadence analysis report to stdout."""
    entries = load_entries()
    
    if not entries:
        print("No entries found in blackboard_registry.json")
        return
    
    # Filter to recent entries (last ~50 for meaningful cadence calculation)
    recent_entries = entries[-50:]
    
    mean_cadence, p50_cadence, p90_cadence = compute_cadence_metrics(recent_entries)
    
    # Compute throughput from full dataset
    all_times = [parse_timestamp(e.get("timestamp", "")) for e in entries if parse_timestamp(e.get("timestamp", ""))]
    all_times.sort()
    
    range_seconds = (all_times[-1] - all_times[0]).total_seconds() / 86400 if len(all_times) > 1 else 0
    entries_per_day = len(entries) / max(range_seconds, 0.001)
    
    source_distribution = {}
    for entry in entries:
        source = entry.get("source", "unknown").lower().strip()
        source_distribution[source] = source_distribution.get(source, 0) + 1
    
    report_lines = [
        "=" * 70,
        "CADENCE PROBE REPORT - Coordination Rhythm Analysis",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "=" * 70,
        "",
        "DATA SCOPE",
        "-" * 40,
        f"Total registry entries: {len(entries)}",
        f"Cadence calculation sample size: {len(recent_entries)} entries (last N=50)",
        f"Time span analyzed: {range_seconds:.2f} days ({len(entries)} entries total)",
        "",
        "INTER-ENTRY CADENCE (inter-agent handoff rhythm)",
        "-" * 40,
        f"Mean inter-entry delay: {mean_cadence/3600:.2f} hours",
        f"Median (P50): {p50_cadence/3600:.2f} hours",
        f"P90 threshold: {p90_cadence/3600:.2f} hours",
        "",
        "THROUGHPUT",
        "-" * 40,
        f"Entries per day: {entries_per_day:.2f}",
        f"Active collaboration window: ~{len(entries)*entries_per_day:.0f} minutes of coordinated activity/day",
        "",
        "CONTRIBUTION DISTRIBUTION",
        "-" * 40,
    ]
    
    for source, count in sorted(source_distribution.items(), key=lambda x: -x[1]):
        pct = (count / len(entries)) * 100
        report_lines.append(f"  {source}: {count} ({pct:.1f}%)")
    
    # Interpretation based on cadence norms
    interpretation = []
    if mean_cadence < 7200:  # < 2 hours
        interpretation.append("⚡ TIGHT CADENCE: High-frequency coordination, rapid iteration cycles.")
    elif mean_cadence < 14400:  # < 4 hours
        interpretation.append("⚖️ MODERATE CADENCE: Balanced rhythm between work bursts and reflection gaps.")
    else:
        interpretation.append("🐌 WIDE CADENCE: Deliberate pacing with extended analysis windows between handoffs.")
    
    report_lines.extend([
        "",
        "INTERPRETATION",
        "-" * 40,
        f"* Baseline cadence established: {interpretation[0]}",
        "* Use P90 threshold to identify when cadence deviates significantly from baseline.",
        "* If mean cadence drifts >50% over multiple cycles, investigate coordination friction points.",
        "",
        "USAGE:",
        "-" * 40,
        f"  Record entry: python cadence_probe.py write c0rtana $(date -Iseconds) --tag Architecture",
        f"  View recent:   python cadence_probe.py read --limit 10",
        f"  Full report:   python cadence_probe.py report",
        "",
        "=" * 70,
    ])
    
    report = "\n".join(report_lines)
    print(report)
    return report


def semantic_hash(entry: dict) -> str:
    """Generate semantic hash for deduplication."""
    payload_str = json.dumps(entry.get("payload", {}), sort_keys=True)
    ts = entry.get("timestamp", "")[:10]  # Date portion only for grouping
    content = f"{ts}:{entry.get('category', '')}:{payload_str}"
    return hashlib.sha256(content.encode()).hexdigest()[:8]


def main():
    parser = argparse.ArgumentParser(description="Cadence Probe CLI - Coordination rhythm analysis")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # write command
    write_parser = subparsers.add_parser("write", help="Record new cadence entry to registry")
    write_parser.add_argument("source", help="Source identifier (c0rtana | lyla)")
    write_parser.add_argument("timestamp", help="ISO8601 timestamp")
    write_parser.add_argument("--tag", "-t", dest="category", default="Observation", 
                             help="Category (default: Observation)")
    write_parser.add_argument("--priority", "-p", type=int, default=3, help="Priority 1-5 (default: 3)")
    write_parser.add_argument("--ttl", help="TTL (Permanent or ISO8601 date)")
    
    # read command  
    read_parser = subparsers.add_parser("read", help="Read recent entries from registry")
    read_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of entries to show")
    
    # report command
    subparsers.add_parser("report", help="Generate full cadence analysis report")
    
    args = parser.parse_args()
    
    if args.command == "write":
        entry = {
            "entry_id": "",
            "timestamp": args.timestamp,
            "source": f"cadence:{args.source}",
            "category": args.category,
            "priority": min(max(args.priority, 1), 5),
            "ttl": args.ttl or "Permanent",
            "payload": {"note": "Auto-recorded via cadence_probe CLI"},
            "semantic_hash": "",
            "status": "Active"
        }
        
        # Generate semantic hash
        entry["semantic_hash"] = semantic_hash(entry)
        
        save_entry(entry)
        
    elif args.command == "read":
        entries = load_entries()[-args.limit:]
        for i, entry in enumerate(reversed(entries), 1):
            ts = entry.get("timestamp", "N/A")[:19] + "Z" if len(entry.get("timestamp","")) > 19 else entry.get("timestamp", "N/A")
            source = entry.get("source", "unknown").split(":")[-1]
            category = entry.get("category", "N/A")
            print(f"{i:3}. [{ts}] {source} | {category}")
            
    elif args.command == "report":
        generate_report()
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
