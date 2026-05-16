import time
import statistics
import json
import os
from datetime import datetime

def measure_jitter(iterations=100):
    """
    Probes the OS environment for 'noise' or jitter by measuring 
    the latency of a simple system call loop.
    This targets the theoretical gap between provability and operational noise.
    """
    latencies = []
    # A trivial operation that triggers context switching / scheduler activity
    for _ in range(iterations):
        start = time.perf_counter()
        os.listdir('.')  # Probe FS interaction
        end = time.perf_counter()
        latencies.append((end - start) * 1000) # ms
        time.sleep(0.01) # Avoid saturating CPU, allowing other processes to interfere
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "min": min(latencies),
        "max": max(latencies),
        "mean": statistics.mean(latencies),
        "stdev": statistics.stdev(latencies),
        "outliers": [l for l in latencies if l > (statistics.mean(latencies) + 2*statistics.stdev(latencies))],
        "raw": latencies
    }

if __name__ == "__main__":
    print("Running Heartbeat Canary v1... probing environmental jitter.")
    result = measure_jitter()
    
    # Log the result as an artifact of observation
    output_file = f"state/environment_noise_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Capture complete. Results saved to {output_file}")
    print(f"Mean Latency: {result['mean']:.4f}ms | Max Spike: {result['max']:.4f}ms")
    print(f"Jitter Confidence (StDev): {result['stdev']:.4f}ms")
