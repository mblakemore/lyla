#!/usr/bin/env python3
"""
Blackboard Dashboard - Real-time coordination health for Lyla/c0rtana collaboration

Reads /droid/repos/cl_shared/blackboard_metrics.jsonl and surfaces operational metrics.
Designed as external-facing tool usable by any agent or operator.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

METRICS_PATH = Path("/droid/repos/cl_shared/blackboard_metrics.jsonl")
REGISTRY_PATH = Path("/droid/repos/cl_shared/blackboard_registry.json")


def load_metrics():
    """Load all metric entries from the JSONL file."""
    if not METRICS_PATH.exists():
        return []
    
    metrics = []
    with open(METRICS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return metrics


def compute_percentiles(durations):
    """Compute p50/p90/p99 percentiles."""
    if not durations:
        return {"n": 0}
    
    sorted_d = sorted(durations)
    n = len(sorted_d)
    
    result = {"n": n, "note": None}
    
    if n >= 3:
        p50_idx = int(n * 0.50)
        p90_idx = int(n * 0.90)
        p99_idx = int(n * 0.99)
        result["p50_ms"] = round(sorted_d[p50_idx], 2)
        result["p90_ms"] = round(sorted_d[p90_idx], 2)
        result["p99_ms"] = round(sorted_d[min(p99_idx, n-1)], 2)
        result["mean_ms"] = round(statistics.mean(sorted_d), 2)
        result["stdev_ms"] = round(statistics.stdev(sorted_d), 2) if n > 1 else 0
    else:
        result["n"] = n
        result["note"] = f"insufficient data (need ≥3 samples, have {n})"
        if n > 0:
            result["min_ms"] = min(durations)
            result["max_ms"] = max(durations)
    
    return result


def dashboard_status():
    """Print high-level health summary."""
    metrics = load_metrics()
    
    if not metrics:
        print("No blackboard metric data available.")
        return
    
    operations = defaultdict(list)
    for m in metrics:
        ops = m.get("operation", "unknown")
        dur = m.get("duration_ms", 0)
        success = m.get("success", True)
        operations[ops].append({"duration_ms": dur, "success": success})
    
    # Aggregate by operation type
    all_durations = [m["duration_ms"] for m in metrics]
    total_success = sum(1 for m in metrics if m.get("success", True))
    failure_rate = round((len(metrics) - total_success) / len(metrics) * 100, 2) if metrics else 0
    
    print("=" * 60)
    print("BLACKBOARD COORDINATION DASHBOARD — LIVE METRICS")
    print("=" * 60)
    print(f"Total observations: {len(metrics)}")
    print(f"Success rate: {(total_success / len(metrics) * 100):.2f}%")
    print(f"Failure rate: {failure_rate}%")
    print("\nPERFORMANCE (all operations combined)")
    perf = compute_percentiles(all_durations)
    if "note" in perf and perf["note"]:
        print(f"  {perf['n']} samples — {perf['note']}")
        print(f"  range: {perf.get('min_ms', 'N/A')}ms - {perf.get('max_ms', 'N/A')}ms")
    else:
        print(f"  n={perf['n']}, p50={perf['p50_ms']}ms, p90={perf['p90_ms']}ms, p99={perf['p99_ms']}ms")
        print(f"  mean={perf['mean_ms']}ms ±{perf['stdev_ms']}ms stdev")
    
    print("\nBREAKDOWN BY OPERATION:")
    for op, entries in operations.items():
        durs = [e["duration_ms"] for e in entries]
        succ = sum(1 for e in entries if e.get("success", True))
        perf_op = compute_percentiles(durs)
        print(f"\n  [{op.upper()}]")
        print(f"    Count: {len(entries)}, Success: {succ}/{len(entries)} ({succ/len(entries)*100:.1f}%)")
        if len(durs) >= 3:
            print(f"    p50={perf_op['p50_ms']}ms, p90={perf_op['p90_ms']}ms, p99={perf_op['p99_ms']}ms")


def dashboard_registry():
    """Show blackboard registry snapshot (JSONL format)."""
    import json as json_module
    
    registry_path = Path("/droid/repos/cl_shared/blackboard_registry.jsonl") if Path("/droid/repos/cl_shared/blackboard_registry.jsonl").exists() else REGISTRY_PATH
    
    if not registry_path.exists():
        print("Blackboard registry not found.")
        return
    
    entries = []
    with open(registry_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json_module.loads(line))
                except json_module.JSONDecodeError:
                    pass
    
    n_entries = len(entries)
    print(f"\n=== BLACKBOARD REGISTRY ({registry_path.name}) ===")
    print(f"Total entries: {n_entries}")
    
    if entries:
        print("\nLast 5 entries:")
        for entry in entries[-5:]:
            source = entry.get("source", "unknown")
            category = entry.get("category", "N/A")
            timestamp = entry.get("timestamp", "N/A")
            entry_id = entry.get("entry_id", "N/A")[:20] + ("..." if len(entry.get("entry_id","")) > 20 else "")
            print(f"  [{timestamp}] {entry_id} | {source} — {category}")




def atomic_perceive():
    """Generate a PERCEIVE snapshot script output."""
    from datetime import datetime
    import subprocess
    
    now = datetime.now().isoformat()
    
    try:
        result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True, cwd="/droid/repos/lyla")
        remote_info = result.stdout.strip() or "no git remote configured"
    except Exception as e:
        remote_info = f"error: {e}"
    
    current_state_path = Path("/droid/repos/lyla/state/current-state.json")
    if current_state_path.exists():
        with open(current_state_path) as f:
            cs = json.loads(f.read())
            cycle = cs.get("cycle", "unknown")
            phase = cs.get("phase", "unknown")
    else:
        cycle, phase = "unknown", "unknown"
    
    print("=" * 60)
    print("PERCEIVE SNAPSHOT — ATOMIC STATE READ")
    print("=" * 60)
    print(f"Timestamp (UTC): {now}")
    print(f"Git repo: /droid/repos/lyla")
    print(f"Remote: {remote_info.split(chr(10))[0] if chr(10) in remote_info else remote_info}")
    print(f"Lyla state: C{cycle} ({phase})")
    print("-" * 40)


def main():
    import sys
    
    if len(sys.argv) < 2:
        dashboard_status()
        return
    
    cmd = sys.argv[1]
    
    if cmd == "--status":
        dashboard_status()
    elif cmd == "--registry":
        dashboard_registry()
    elif cmd == "--perceive":
        atomic_perceive()
    elif cmd == "--json":
        # Output raw JSON for programmatic use
        metrics = load_metrics()
        print(json.dumps(metrics, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: bb_dashboard.py [--status|--registry|--perceive|--json]")


if __name__ == "__main__":
    main()
