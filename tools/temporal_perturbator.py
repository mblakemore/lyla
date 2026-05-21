#!/usr/bin/env python3
"""
Temporal Perturbation Injection Tool — Empirical Provability Gap Test

Purpose: Inject controlled timing variability into system operations to test
whether systems degrade gracefully or fail catastrophically when axioms about
deterministic timing break.

Hypothesis: Systems optimized for stable paths lack explicit error handling
for timing drifts—precisely where they'll fail in production.

Usage: 
  # Baseline (no injection)
  python3 tools/temporal_perturbator.py --baseline
  
  # Controlled perturbation
  python3 tools/temporal_perturbator.py --inject <ms> [--spike-rate PCT]

Outputs JSON results to state/temporal_perturb_TIMESTAMP.json
"""

import argparse
import json
import random
import time
from datetime import datetime, timezone


def run_experiment(inject_jitter_ms: float = 0.0, spike_rate_pct: float = 5.0, iterations: int = 100) -> dict:
    """
    Run operation sequence with optional jitter injection.
    
    Args:
        inject_jitter_ms: Base additive noise per iteration (can be negative for speedup)
        spike_rate_pct: Percentage of iterations that get major spikes
        iterations: Number of operation cycles
    
    Returns:
        Dict with latency statistics and perturbation metadata
    """
    latencies = []
    spike_count = 0
    baseline_latencies = []
    
    for i in range(iterations):
        start_ns = time.perf_counter_ns()
        
        # Simulate realistic "work" - context switch + computation
        _ = sum(range(1000))
        
        end_ns = time.perf_counter_ns()
        raw_latency = (end_ns - start_ns) / 1_000_000  # ms
        
        if inject_jitter_ms > 0:
            # Apply perturbation
            base_noise = random.gauss(0, inject_jitter_ms / 3)  # ~99% within ±inject_jitter
            
            # Occasional major spikes (simulating real-world anomalies)
            if random.random() * 100 < spike_rate_pct:
                spike_mult = random.uniform(2.0, 5.0)
                base_noise += inject_jitter_ms * spike_mult
                spike_count += 1
            
            adjusted_latency = max(0.001, raw_latency + base_noise)
        else:
            adjusted_latency = raw_latency
            baseline_latencies.append(raw_latency)
        
        latencies.append(adjusted_latency)
    
    # Calculate statistics
    mean_lat = sum(latencies) / len(latencies)
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_config": {
            "jitter_injection_ms": inject_jitter_ms,
            "spike_rate_pct": spike_rate_pct,
            "iterations": iterations,
        },
        "latency_stats": {
            "mean_ms": round(mean_lat, 6),
            "median_ms": round(sorted_lat[n//2], 6),
            "p95_ms": round(sorted_lat[int(n*0.95)], 6),
            "p99_ms": round(sorted_lat[int(n*0.99)], 6),
            "max_ms": round(max(latencies), 6),
            "stdev_ms": round(sum((x-mean_lat)**2 for x in latencies)/n**0.5, 6),
        },
        "perturbation_metrics": {
            "spikes_observed": spike_count,
            "total_iterations": iterations,
            "spike_rate_actual_pct": round(spike_count/iterations*100, 2),
            "baseline_mean_ms": round(sum(baseline_latencies)/len(baseline_latencies), 6) if baseline_latencies else None,
            "jitter_range_ms": [round(min(latencies), 6), round(max(latencies), 6)],
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Temporal Perturbation Injection Tool")
    parser.add_argument("--inject", "-j", type=float, default=0.0, 
                        help="Inject jitter (ms) per iteration (default: 0.0)")
    parser.add_argument("--spike-rate", "-s", type=float, default=5.0,
                        help="Percentage of iterations with major spikes (default: 5.0)")
    parser.add_argument("--iterations", "-n", type=int, default=100,
                        help="Number of operation cycles (default: 100)")
    parser.add_argument("--output-dir", type=str, default="state",
                        help="Output directory for results JSON")
    
    args = parser.parse_args()
    
    # Determine mode name
    if args.inject > 0:
        mode_name = f"perturbed_{args.inject}ms"
        print(f"[INFO] Perturbation mode: {args.inject}ms base jitter + {args.spike_rate}% spike rate")
    else:
        mode_name = "baseline"
        print("[INFO] Baseline mode: no perturbation injection")
    
    # Run experiment
    result = run_experiment(
        inject_jitter_ms=args.inject,
        spike_rate_pct=args.spike_rate,
        iterations=args.iterations
    )
    
    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = f"{args.output_dir}/temporal_perturb_{mode_name}_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Print summary
    stats = result['latency_stats']
    perturb = result['perturbation_metrics']
    config = result['experiment_config']
    
    print("\n=== TEMPORAL PERTURBATION RESULTS ===")
    print(f"Mode: {mode_name}")
    print(f"Iterations: {config['iterations']}")
    print(f"\nLatency Statistics:")
    print(f"  Mean:   {stats['mean_ms']:.6f} ms")
    print(f"  Median: {stats['median_ms']:.6f} ms")
    print(f"  P95:    {stats['p95_ms']:.6f} ms")
    print(f"  P99:    {stats['p99_ms']:.6f} ms")
    print(f"  Max:    {stats['max_ms']:.6f} ms")
    print(f"  Stdev:  {stats['stdev_ms']:.6f} ms")
    
    if perturb['baseline_mean_ms']:
        baseline = perturb['baseline_mean_ms']
        impact = (stats['mean_ms'] - baseline) / baseline * 100 if baseline > 0 else 0
        print(f"\nPerturbation Impact:")
        print(f"  Baseline mean: {baseline:.6f} ms")
        print(f"  Perturbed mean: {stats['mean_ms']:.6f} ms")
        print(f"  Delta: +{impact:.2f}%")
    
    print(f"\nSpike observations: {perturb['spikes_observed']} / {config['iterations']} ({perturb['spike_rate_actual_pct']}%)")
    print(f"Jitter range: [{perturb['jitter_range_ms'][0]:.6f}, {perturb['jitter_range_ms'][1]:.6f}] ms")
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
