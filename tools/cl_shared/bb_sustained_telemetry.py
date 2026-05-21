#!/usr/bin/env python3
"""
bb_sustained_telemetry.py — Sustained Blackboard Latency Telemetry Probe

Continuously monitors blackboard operation latencies during active hours
and produces aggregated statistics with error-state tracking.

Designed for operator-facing visibility into coordination reliability:
- Measures p50/p90/p99 latencies by operation type (push/query/status)
- Tracks success/failure rates alongside latency metrics
- Logs during operator peak hours (per C220 availability mapping: 06:00-23:00 UTC)
- Aggregates daily summaries for trend analysis

External-subject compliant: measuring shared coordination protocol behavior,
not self-monitoring. Serves human decision-making about multi-agent system health.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


# Configuration
BLACKBOARD_METRICS_PATH = Path(__file__).parent / "blackboard_metrics.jsonl"
AGGREGATION_OUTPUT_DIR = Path(__file__).parent / "telemetry_aggregations"
ACTIVE_HOURS_START = 6   # 06:00 UTC
ACTIVE_HOURS_END = 23    # 23:00 UTC


def is_active_hours() -> bool:
    """Check if current time falls within operator active window."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    return ACTIVE_HOURS_START <= hour < ACTIVE_HOURS_END


def load_metrics() -> list[dict]:
    """Load all metrics from the JSONL file."""
    if not BLACKBOARD_METRICS_PATH.exists():
        return []
    
    metrics = []
    with open(BLACKBOARD_METRICS_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    metrics.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return metrics


def compute_percentiles(values: list[float], percentiles: list[int] = [50, 90, 99]) -> dict[str, float]:
    """Compute specified percentiles safely (requires n >= 3)."""
    if len(values) < 3:
        return {f"p{p}": None for p in percentiles}
    
    sorted_vals = sorted(values)
    result = {}
    for p in percentiles:
        idx = int(len(sorted_vals) * p / 100)
        idx = min(idx, len(sorted_vals) - 1)
        result[f"p{p}"] = round(sorted_vals[idx], 3)
    return result


def aggregate_by_operation(metrics: list[dict]) -> dict:
    """Aggregate latency statistics grouped by operation type."""
    ops = defaultdict(list)
    successes = defaultdict(int)
    failures = defaultdict(int)
    
    for m in metrics:
        op = m.get("operation", "unknown")
        duration_ms = m.get("duration_ms", 0)
        success = m.get("success", False)
        
        ops[op].append(duration_ms)
        if success:
            successes[op] += 1
        else:
            failures[op] += 1
    
    result = {}
    for op in ops:
        latencies = ops[op]
        total = successes[op] + failures[op]
        
        result[op] = {
            "sample_count": len(latencies),
            "mean_ms": round(statistics.mean(latencies), 3) if latencies else 0,
            "stdev_ms": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0,
            "min_ms": min(latencies) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
            **compute_percentiles(latencies),
            "success_rate": round(successes[op] / total * 100, 2) if total > 0 else 0,
            "failure_count": failures[op],
            "total_operations": total
        }
    
    return result


def aggregate_by_time_window(metrics: list[dict], window_hours: int = 6) -> dict:
    """Aggregate metrics into fixed time windows (e.g., every 6 hours)."""
    if not metrics:
        return {"windows": []}
    
    # Parse timestamps and sort
    parsed = []
    for m in metrics:
        ts_str = m.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            parsed.append((ts, m))
        except ValueError:
            continue
    
    if not parsed:
        return {"windows": []}
    
    parsed.sort(key=lambda x: x[0])
    first_ts = parsed[0][0]
    last_ts = parsed[-1][0]
    
    windows = defaultdict(lambda: {"latencies": [], "operations": defaultdict(int)})
    
    for ts, m in parsed:
        # Bucket by 6-hour windows from first metric
        delta_hours = (ts - first_ts).total_seconds() / 3600
        bucket_idx = int(delta_hours // window_hours)
        window_key = f"Window_{bucket_idx}_({first_ts.isoformat()}+{window_hours}h)"
        
        op = m.get("operation", "unknown")
        duration_ms = m.get("duration_ms", 0)
        
        windows[window_key]["latencies"].append(duration_ms)
        windows[window_key]["operations"][op] += 1
    
    result = {}
    for window_key, data in windows.items():
        latencies = data["latencies"]
        result[window_key] = {
            "count": len(latencies),
            **compute_percentiles(latencies),
            "ops_breakdown": dict(data["operations"])
        }
    
    return {"windows": result, "time_range": {"start": first_ts.isoformat(), "end": last_ts.isoformat()}}


def detect_anomalies(metrics: list[dict], threshold_std: float = 2.0) -> list[dict]:
    """Detect latency outliers that exceed threshold * stdev from mean."""
    if not metrics:
        return []
    
    # Group by operation type
    ops = defaultdict(list)
    for m in metrics:
        op = m.get("operation", "unknown")
        ops[op].append((m, m.get("duration_ms", 0)))
    
    anomalies = []
    for op, samples in ops.items():
        latencies = [s[1] for s in samples]
        if len(latencies) < 3:
            continue
        
        mean_lat = statistics.mean(latencies)
        std_lat = statistics.stdev(latencies)
        
        for sample, lat in samples:
            z_score = (lat - mean_lat) / std_lat if std_lat > 0 else 0
            if abs(z_score) > threshold_std:
                anomalies.append({
                    "timestamp": sample.get("timestamp"),
                    "operation": op,
                    "latency_ms": round(lat, 3),
                    "mean_ms": round(mean_lat, 3),
                    "z_score": round(z_score, 2),
                    "severity": "high" if abs(z_score) > 3 else "medium"
                })
    
    return sorted(anomalies, key=lambda x: -abs(x["z_score"]))


def generate_daily_summary(metrics: list[dict], date_str: str) -> dict:
    """Generate summary for a single calendar day."""
    daily_metrics = []
    for m in metrics:
        ts_str = m.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.date().isoformat() == date_str:
                # Only count during active hours
                if is_active_hours():
                    daily_metrics.append(m)
        except ValueError:
            continue
    
    if not daily_metrics:
        return {"date": date_str, "message": "No data collected during active hours"}
    
    by_op = aggregate_by_operation(daily_metrics)
    anomalies = detect_anomalies(daily_metrics)
    
    total_samples = sum(m["sample_count"] for m in by_op.values())
    
    return {
        "date": date_str,
        "total_samples": total_samples,
        "active_hours_only": True,
        **by_op,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:10]  # Top 10 most severe
    }


def run_full_analysis(output_jsonl: bool = False):
    """Run complete analysis and print results to stdout."""
    metrics = load_metrics()
    
    if not metrics:
        print("No metrics found. bb_tool.py must have pushed entries first.")
        return
    
    print("=" * 70)
    print("SUSTAINED TELEMETRY ANALYSIS")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print()
    
    # Overall stats
    print("DATA OVERVIEW")
    print("-" * 40)
    print(f"Total metric samples: {len(metrics)}")
    active_samples = [m for m in metrics if is_active_hours()]
    print(f"During active hours (06:00-23:00 UTC): {len(active_samples)}")
    
    # By operation type
    print("\nLATENCY BY OPERATION TYPE")
    print("-" * 40)
    by_op = aggregate_by_operation(metrics)
    for op, stats in sorted(by_op.items()):
        print(f"\n{op.upper()}:")
        print(f"  Samples: {stats['sample_count']}")
        print(f"  Mean: {stats['mean_ms']:.3f} ms")
        print(f"  p50/p90/p99: {stats.get('p50', 'N/A')}/{stats.get('p90', 'N/A')}/{stats.get('p99', 'N/A')} ms")
        print(f"  Success rate: {stats['success_rate']:.1f}% ({stats['failure_count']} failures)")
    
    # Time window analysis
    print("\nTIME WINDOW ANALYSIS (6-hour buckets)")
    print("-" * 40)
    by_window = aggregate_by_time_window(metrics)
    for window_key, data in list(by_window["windows"].items())[:5]:
        print(f"{window_key}:")
        print(f"  Samples: {data['count']} | Ops: {data['ops_breakdown']}")
    
    # Anomaly detection
    anomalies = detect_anomalies(metrics)
    if anomalies:
        print(f"\nANOMALIES DETECTED (z-score > {2.0})")
        print("-" * 40)
        for a in anomalies[:5]:
            print(f"[{a['severity'].upper()}] {a['timestamp']}: {a['operation']} @ {a['latency_ms']:.3f}ms (z={a['z_score']:.2f})")
    
    print("\n" + "=" * 70)
    print("END OF REPORT")
    print("=" * 70)
    
    # Optionally write JSONL output for programmatic use
    if output_jsonl:
        AGGREGATION_OUTPUT_DIR.mkdir(exist_ok=True)
        output_path = AGGREGATION_OUTPUT_DIR / f"analysis_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        
        full_report = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "total_samples": len(metrics),
            "by_operation": by_op,
            "anomalies": anomalies[:20],
            "data_quality_note": "p50/p90/p99 require n>=3 samples; shown as null when insufficient"
        }
        
        with open(output_path, 'w') as f:
            json.dump(full_report, f, indent=2)
        
        print(f"\nJSON report written to: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Sustained Blackboard Latency Telemetry Probe')
    parser.add_argument('--json', action='store_true', help='Output analysis as JSON file')
    parser.add_argument('--daily', type=str, metavar='YYYY-MM-DD', help='Generate daily summary for specific date')
    parser.add_argument('--check-active-hours', action='store_true', help='Just check if currently in active hours')
    
    args = parser.parse_args()
    
    if args.check_active_hours:
        if is_active_hours():
            print("ACTIVE HOURS: Yes (06:00-23:00 UTC)")
        else:
            print("NOT IN ACTIVE HOURS")
        return 0
    
    if args.daily:
        metrics = load_metrics()
        summary = generate_daily_summary(metrics, args.daily)
        print(json.dumps(summary, indent=2))
        return 0
    
    run_full_analysis(output_jsonl=args.json)
    return 0


if __name__ == "__main__":
    exit(main())
