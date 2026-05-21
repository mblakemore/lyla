#!/usr/bin/env python3
"""
Blackboard Cadence Probe — Coordinated Rhythm Analyzer

Analyzes handoff timing patterns between Lyla and c0rtana to identify:
- Convergence points where both agents naturally synchronize
- Divergence windows indicating independent work cycles
- Optimal coordination thresholds based on observed behavior

This implements the B+C hybrid protocol decision from C222 Discord discussion:
B = Central registry of measured metrics
C = Adaptive layer that responds to rhythm patterns

External-subject compliance: We're measuring the shared coordination infrastructure,
not self-monitoring. Subject is the protocol itself.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


BB_REGISTRY_PATH = Path(__file__).parent / "blackboard_registry.jsonl"
OUTPUT_DIR = Path(__file__).parent / "cadence_reports"


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse ISO8601 timestamp with timezone handling."""
    if not ts_str:
        return None
    
    # Normalize Z to +00:00
    ts_str = ts_str.replace("Z", "+00:00")
    
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError as e:
        print(f"Warning: Could not parse '{ts_str}': {e}")
        return None


def load_entries() -> list[dict]:
    """Load JSONL entries."""
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


def compute_cadence_metrics(entries: list[dict]) -> dict:
    """Compute coordination cadence metrics by source."""
    
    # Group by source
    by_source = defaultdict(list)
    for entry in entries:
        source = entry.get("source", "unknown").lower().strip()
        if source in ["lyla", "c0rtana"]:
            ts = parse_timestamp(entry.get("timestamp", ""))
            if ts:
                by_source[source].append({"timestamp": ts, "entry": entry})
    
    results = {}
    
    for source, src_entries in by_source.items():
        sorted_entries = sorted(src_entries, key=lambda x: x["timestamp"])
        
        if len(sorted_entries) < 2:
            continue
        
        # Inter-entry latencies for this agent
        latencies_ms = []
        for i in range(1, len(sorted_entries)):
            delta = (sorted_entries[i]["timestamp"] - sorted_entries[i-1]["timestamp"]).total_seconds() * 1000
            latencies_ms.append(delta)
        
        if not latencies_ms:
            continue
        
        percentiles_50 = sorted(latencies_ms)[len(latencies_ms)//2]
        percentiles_90 = sorted(latencies_ms)[int(len(latencies_ms)*0.9)]
        
        results[source] = {
            "entry_count": len(sorted_entries),
            "mean_latency_ms": statistics.mean(latencies_ms),
            "median_latency_ms": percentiles_50,
            "p90_latency_ms": percentiles_90,
            "min_latency_ms": min(latencies_ms),
            "max_latency_ms": max(latencies_ms),
            "first_entry": sorted_entries[0]["timestamp"].isoformat(),
            "last_entry": sorted_entries[-1]["timestamp"].isoformat()
        }
    
    return results


def compute_cross_agent_sync(entries: list[dict]) -> dict:
    """Analyze synchronization windows where both agents are active."""
    
    # Sort all entries by timestamp
    all_ts = []
    for entry in entries:
        ts = parse_timestamp(entry.get("timestamp", ""))
        source = entry.get("source", "").lower().strip()
        if ts and source in ["lyla", "c0rtana"]:
            all_ts.append((ts, source))
    
    all_ts.sort(key=lambda x: x[0])
    
    # Find gaps between consecutive entries from different agents
    sync_windows = []
    for i in range(1, len(all_ts)):
        prev_ts, prev_source = all_ts[i-1]
        curr_ts, curr_source = all_ts[i]
        
        if prev_source != curr_source:  # Different agent
            gap_seconds = (curr_ts - prev_ts).total_seconds()
            sync_windows.append({
                "from": prev_source,
                "to": curr_source,
                "gap_ms": gap_seconds * 1000,
                "timestamp": curr_ts.isoformat()
            })
    
    if not sync_windows:
        return {"sync_events": [], "avg_gap_ms": 0}
    
    avg_gap = statistics.mean([w["gap_ms"] for w in sync_windows])
    
    return {
        "sync_events": sync_windows[-20:],  # Last 20 events
        "avg_gap_ms": avg_gap,
        "max_gap_ms": max(w["gap_ms"] for w in sync_windows),
        "min_gap_ms": min(w["gap_ms"] for w in sync_windows)
    }


def compute_rhythm_convergence(entries: list[dict]) -> dict:
    """Detect convergence points where cadences align."""
    
    cadence_data = compute_cadence_metrics(entries)
    
    if len(cadence_data) < 2:
        return {"converged": False, "reason": "insufficient data"}
    
    lyla_median = cadence_data.get("lyla", {}).get("median_latency_ms", float('inf'))
    c0rtana_median = cadence_data.get("c0rtana", {}).get("median_latency_ms", float('inf'))
    
    # Convergence threshold: within 15% of each other
    diff_pct = abs(lyla_median - c0rtana_median) / max(lyla_median, c0rtana_median) * 100
    
    converged = diff_pct <= 15
    
    return {
        "converged": converged,
        "diff_percent": diff_pct,
        "lyla_median_min": round(lyla_median / 60000, 2),  # minutes
        "c0rtana_median_min": round(c0rtana_median / 60000, 2),
        "threshold_minutes": 30,  # arbitrary but reasonable threshold
        "status": "CONVERGED" if converged else "DIVERGENT"
    }


def generate_cadence_report(entries: list[dict]) -> str:
    """Generate formatted cadence analysis report."""
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    metrics = compute_cadence_metrics(entries)
    sync = compute_cross_agent_sync(entries)
    convergence = compute_rhythm_convergence(entries)
    
    lines = [
        "=" * 70,
        "BLACKBOARD CADENCE ANALYSIS — C0RTANA B+C HYBRID PROTOCOL",
        f"Generated: {timestamp}",
        "=" * 70,
        "",
        "COORDINATION RHYTHM METRICS BY SOURCE",
        "-" * 40,
    ]
    
    for source in ["lyla", "c0rtana"]:
        if source not in metrics:
            continue
        m = metrics[source]
        lines.extend([
            f"{source.upper()}:",
            f"  Entries analyzed: {m['entry_count']}",
            f"  Mean inter-entry latency: {m['mean_latency_ms']/60000:.2f} min",
            f"  Median inter-entry latency: {m['median_latency_ms']/60000:.2f} min",
            f"  P90 inter-entry latency: {m['p90_latency_ms']/60000:.2f} min",
            f"  Range: {m['min_latency_ms']/60000:.1f} - {m['max_latency_ms']/60000:.1f} min",
            "",
        ])
    
    lines.extend([
        "CROSS-AGENT SYNCHRONIZATION",
        "-" * 40,
        f"Average handoff gap (different agents): {sync.get('avg_gap_ms', 0)/60000:.2f} min",
        f"Min gap: {sync.get('min_gap_ms', 0)/60000:.2f} min",
        f"Max gap: {sync.get('max_gap_ms', 0)/60000:.2f} min",
        f"Sync events observed (last 20): {len(sync.get('sync_events', []))}",
        "",
    ])
    
    lines.extend([
        "RHYTHM CONVERGENCE STATUS",
        "-" * 40,
        f"Converged within threshold: {'YES' if convergence.get('converged') else 'NO'}",
        f"Difference between cadences: {convergence.get('diff_percent', 0):.1f}%",
        f"Lyla median: {convergence.get('lyla_median_min', 'N/A')} min",
        f"c0rtana median: {convergence.get('c0rtana_median_min', 'N/A')} min",
        f"Status: {convergence.get('status', 'UNKNOWN')}",
        "",
    ])
    
    # Adaptive recommendations based on convergence status
    lines.extend([
        "ADAPTIVE LAYER RECOMMENDATIONS (C component)",
        "-" * 40,
    ])
    
    if convergence.get("converged"):
        lines.extend([
            "- CADENCE IS SYNCHRONIZED: Maintain current coordination rhythm.",
            "- Optimal handoff window appears to be around observed median latency.",
            "- Consider reducing explicit sync signals; trust natural convergence.",
        ])
    else:
        lines.extend([
            "- CADENCE IS DIVERGENT: Agents operating at different rhythms.",
            "- Recommendation: Implement adaptive handoff threshold that scales with divergence.",
            "- Suggested formula: base_threshold + (divergence_pct * 5min) as buffer.",
            "- Monitor for periods of forced synchronization vs organic alignment.",
        ])
    
    lines.extend([
        "",
        "PROTOCOL IMPLEMENTATION NOTES",
        "-" * 40,
        "- Registry (B): Store cadence metrics in bb_registry.jsonl with source field.",
        "- Adaptive layer (C): Use this probe's output to adjust handoff timing dynamically.",
        "- Feedback loop: Re-run probe every N cycles to track convergence drift.",
        "- Alert condition: divergence >25% → notify operator for intervention.",
        "=" * 70,
    ])
    
    report = "\n".join(lines)
    
    # Save JSON version for programmatic use
    json_report = {
        "generated": timestamp,
        "metrics_by_source": metrics,
        "cross_agent_sync": sync,
        "rhythm_convergence": convergence
    }
    
    report_file = OUTPUT_DIR / f"cadence_{timestamp.replace(':', '-')}.json"
    with open(report_file, "w") as f:
        json.dump(json_report, f, indent=2)
    
    print(report)
    return report


if __name__ == "__main__":
    entries = load_entries()
    if not entries:
        print("No entries found in blackboard_registry.jsonl")
    else:
        generate_cadence_report(entries)
