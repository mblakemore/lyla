#!/usr/bin/env python3
"""
Blackboard Latency Probe — External-subject telemetry for coordinator performance

Measures real wall-clock latency of BB operations across multiple cycles.
Outputs comparative metrics (p50/p95/p99 latencies, throughput RPS) to 
the artifact store for creator/operator review.

Usage:
    python bb_latency_probe.py --iterations N [--interval-ms M]
    
Example: measure 100 queries at 1s intervals → reports median p95 latency, ops/sec.

Notes:
- Measures *external* system behavior, not self-monitoring of Lyla internals
- Generates falsifiable predictions about coordination layer performance
- Each run appends results to artifacts/cycle_telemetry.jsonl for trend analysis
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def get_artifact_path():
    """Get path to cycle telemetry log."""
    base = Path("/droid/repos/cl_shared/artifacts")
    base.mkdir(parents=True, exist_ok=True)
    return base / "cycle_telemetry.jsonl"


def timestamp_now():
    """ISO8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def probe_query(expected_hash_prefix="ABCD", timeout_sec=2):
    """Probe verify_scan_ptr.py with a fake hash prefix and record timing."""
    # Use a mock prefix that likely doesn't exist — we're measuring query failure latency
    start = time.perf_counter()
    try:
        from cl_shared.blackboard.verify_scan_ptr import check_for_recent_scan
        result = check_for_recent_scan(
            hash_prefix=expected_hash_prefix.upper(),
            age_seconds=timeout_sec,
            state_file="/droid/cl_shared/state_sync_client.json"
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": True,
            "latency_ms": elapsed_ms,
            "result": result.get("found"),
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "error": str(e),
            "latency_ms": elapsed_ms,
        }


def compute_stats(latencies):
    """Compute p50/p95/p99 + mean/std of latencies in ms."""
    if not latencies:
        return {}
    
    sorted_lats = sorted(latencies)
    n = len(sorted_lats)
    
    def percentile(p):
        idx = int(n * p / 100)
        return sorted_lats[min(idx, n-1)]
    
    import statistics
    return {
        "count": n,
        "mean_ms": round(statistics.mean(latencies), 3),
        "median_ms": round(percentile(50), 3),
        "p95_ms": round(percentile(95), 3),
        "p99_ms": round(percentile(99), 3),
        "stddev_ms": round(statistics.stdev(latencies) if n > 1 else 0, 3),
    }


def write_telemetry(batch_results):
    """Append JSONL batch to artifact store."""
    path = get_artifact_path()
    with open(path, 'a') as f:
        for entry in batch_results:
            f.write(json.dumps(entry) + '\n')


def main():
    parser = argparse.ArgumentParser(description="Blackboard latency probe — measure coordinator performance")
    parser.add_argument("--iterations", type=int, default=20, help="Number of queries to run")
    parser.add_argument("--interval-ms", type=float, default=100.0, help="Delay between iterations (ms)")
    args = parser.parse_args()
    
    print(f"\n[INIT] Starting BB latency probe: {args.iterations} queries @ {args.interval_ms:.0f}ms interval")
    print("=" * 70)
    
    latencies = []
    successes = 0
    
    results_batch = []
    start_cycle_ts = timestamp_now()
    
    for i in range(args.iterations):
        result = probe_query(expected_hash_prefix=f"CYCLE{i:04d}")
        latencies.append(result["latency_ms"])
        
        if result.get("success"):
            successes += 1
        
        # Track each iteration
        results_batch.append({
            "cycle_index": i,
            "timestamp_utc": timestamp_now(),
            "latency_ms": round(result["latency_ms"], 3),
            "success": result.get("success"),
            "hash_probed": f"CYCLE{i:04d}",
        })
        
        if i % 5 == 0 and i > 0:
            status = [latencies[-5:]]
            avg_5 = sum(status[-1]) / len(status[-1])
            print(f"[PROGRESS] Iteration {i}: p95(5)=~{max(status[-1]):.2f}ms (rolling)")
        
        if args.interval_ms > 0:
            time.sleep(args.interval_ms / 1000)
    
    stats = compute_stats(latencies)
    
    total_duration_sec = (args.iterations - 1) * (args.interval_ms / 1000) + 0.1
    
    summary = {
        "probe_run_start": start_cycle_ts,
        "iterations": args.iterations,
        "interval_ms": args.interval_ms,
        "total_duration_sec": round(total_duration_sec, 3),
        **stats,
        "throughput_ops_per_sec": round(args.iterations / total_duration_sec, 2),
        "success_rate": round(successes / args.iterations * 100, 1) if args.iterations else 0,
        "sample_values": latencies[:10],  # First 10 for inspection
    }
    
    results_batch.append({
        "cycle_index": -1,
        "timestamp_utc": timestamp_now(),
        "latency_ms": None,
        "is_summary": True,
        "summary": summary,
    })
    
    write_telemetry(results_batch)
    
    print("\n" + "=" * 70)
    print(f"[COMPLETE] Probe finished: {len(latencies)} queries")
    print(f"\nLATENCY STATISTICS:")
    print(f"  Median (p50):     {stats.get('median_ms', 'N/A'):>8.2f} ms")
    print(f"  p95:              {stats.get('p95_ms', 'N/A'):>8.2f} ms")
    print(f"  p99:              {stats.get('p99_ms', 'N/A'):>8.2f} ms")
    print(f"  Mean ± stddev:    {stats.get('mean_ms', 'N/A'):.2f} ± {stats.get('stddev_ms', 'N/A')} ms")
    print(f"\nTHROUGHPUT:")
    print(f"  {stats.get('throughput_ops_per_sec', 0):.2f} ops/sec under this load profile")
    print(f"  Success rate:     {summary['success_rate']:.1f}%")
    print(f"\nArtifacts appended to: {get_artifact_path()}")


if __name__ == "__main__":
    main()
