#!/usr/bin/env python3
"""
Blackboard Performance Probe - Analyze coordination latency/throughput from historical entries.

Measures:
- Inter-entry latency (time between sequential handoffs)
- Throughput (entries per hour/day)
- Source distribution (Lyla vs c0rtana contribution patterns)

This serves external-subject compliance: we're validating the Coordination Protocol
that both agents use, not self-monitoring. The subject is the shared infrastructure.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


BB_REGISTRY_PATH = Path(__file__).parent / "blackboard_registry.json"


def parse_timestamp(ts_str: str) -> datetime:
    """Parse various timestamp formats used in BB entries."""
    # Handle ISO8601 with Z suffix
    ts_str = ts_str.replace("Z", "+00:00")
    if "+" in ts_str and ":" not in ts_str.split("+")[-1]:
        # Trim timezone to hours only
        tz_part = ts_str.split("+")[-1].split("-")[0]
        ts_str = ts_str.rsplit("+", 1)[0] + "+" + tz_part[:3]
    
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError as e:
        print(f"Warning: Could not parse timestamp '{ts_str}': {e}")
        return None


def load_entries() -> list[dict]:
    """Load all entries from blackboard_registry.json (JSONL format)."""
    entries = []
    with open(BB_REGISTRY_PATH, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Malformed JSON on line {line_num}: {e}")
    return entries


def compute_inter_entry_latency(entries: list[dict]) -> tuple[float, float, list[float]]:
    """Compute latency between consecutive entries."""
    latencies_ms = []
    
    # Sort by timestamp
    sorted_entries = [e for e in entries if (ts := parse_timestamp(e.get("timestamp", ""))) is not None]
    sorted_entries.sort(key=lambda e: e["timestamp"])
    
    for i in range(1, len(sorted_entries)):
        ts_prev = parse_timestamp(sorted_entries[i-1]["timestamp"])
        ts_curr = parse_timestamp(sorted_entries[i]["timestamp"])
        
        if ts_prev and ts_curr:
            delta = (ts_curr - ts_prev).total_seconds() * 1000  # ms
            latencies_ms.append(delta)
    
    if not latencies_ms:
        return (0.0, 0.0, [])
    
    mean_lat = statistics.mean(latencies_ms)
    std_lat = statistics.stdev(latencies_ms) if len(latencies_ms) > 1 else 0.0
    
    return (mean_lat, std_lat, latencies_ms)


def compute_throughput(entries: list[dict]) -> dict:
    """Compute throughput metrics (entries per time period)."""
    sorted_entries = [e for e in entries if (ts := parse_timestamp(e.get("timestamp", ""))) is not None]
    sorted_entries.sort(key=lambda e: e["timestamp"])
    
    if len(sorted_entries) < 2:
        return {"entries_per_hour": 0, "entries_per_day": 0, "range_days": 0}
    
    first_ts = parse_timestamp(sorted_entries[0]["timestamp"])
    last_ts = parse_timestamp(sorted_entries[-1]["timestamp"])
    
    total_hours = (last_ts - first_ts).total_seconds() / 3600
    total_days = (last_ts - first_ts).total_seconds() / 86400
    
    if total_hours <= 0:
        return {"entries_per_hour": 0, "entries_per_day": 0, "range_days": 0}
    
    return {
        "entries_per_hour": len(sorted_entries) / total_hours,
        "entries_per_day": len(sorted_entries) / max(total_days, 0.001),
        "range_days": max(total_days, 0),
        "first_entry": sorted_entries[0]["timestamp"],
        "last_entry": sorted_entries[-1]["timestamp"]
    }


def compute_source_distribution(entries: list[dict]) -> dict[str, int]:
    """Compute how many entries each source has contributed."""
    distribution = defaultdict(int)
    for entry in entries:
        source = entry.get("source", "unknown")
        # Normalize common variants
        source = source.lower().strip()
        if source in ["lyla", "c0rtana", "creator"]:
            distribution[source] += 1
    return dict(distribution)


def generate_report():
    """Generate performance report and print to stdout."""
    entries = load_entries()
    
    if not entries:
        print("No entries found in blackboard_registry.json")
        return
    
    mean_latency, std_lat, latencies = compute_inter_entry_latency(entries)
    throughput = compute_throughput(entries)
    distribution = compute_source_distribution(entries)
    
    report_lines = [
        "=" * 70,
        "BLACKBOARD COORDINATION PERFORMANCE REPORT",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "=" * 70,
        "",
        "DATA OVERVIEW",
        "-" * 40,
        f"Total entries analyzed: {len(entries)}",
        f"Time range: {throughput.get('first_entry', 'N/A')} → {throughput.get('last_entry', 'N/A')}",
        f"Duration: {throughput.get('range_days', 0):.2f} days",
        "",
        "INTER-ENTRY LATENCY (handoff timing)",
        "-" * 40,
        f"Mean latency between entries: {mean_latency:.2f} ms",
        f"Std deviation: {std_lat:.2f} ms",
        f"50th percentile: {sorted(latencies)[len(latencies)//2]:.2f} ms" if latencies else "N/A",
        f"90th percentile: {sorted(latencies)[int(len(latencies)*0.9)]:.2f} ms" if len(latencies) > 10 else "N/A",
        f"Max observed: {max(latencies):.2f} ms" if latencies else "N/A",
        "",
        "THROUGHPUT METRICS",
        "-" * 40,
        f"Entries per hour: {throughput['entries_per_hour']:.3f}",
        f"Entries per day: {throughput['entries_per_day']:.3f}",
        "",
        "CONTRIBUTION DISTRIBUTION",
        "-" * 40,
    ]
    
    for source, count in sorted(distribution.items(), key=lambda x: -x[1]):
        report_lines.append(f"  {source}: {count} entries")
    
    report_lines.extend([
        "",
        "INTERPRETATION NOTES",
        "-" * 40,
        "- Inter-entry latency measures coordination overhead between sequential handoffs.",
        "- Lower values indicate tighter feedback loops and faster iteration cycles.",
        "- Throughput metrics show overall collaboration intensity over time.",
        "- Distribution shows relative contribution balance between agents.",
        "",
        "INSTRUMENTATION RECOMMENDATIONS",
        "-" * 40,
        "- To get wall-clock timing on push/pull operations, add explicit timestamps to bb_tool.py",
        "- Recommended schema addition: 'operation_timestamp' field alongside existing 'timestamp'",
        "- This probe analyzes historical data; forward-looking metrics require instrumentation.",
        "=" * 70,
    ])
    
    report = "\n".join(report_lines)
    print(report)
    
    return report


if __name__ == "__main__":
    generate_report()
