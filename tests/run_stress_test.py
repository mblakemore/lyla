import subprocess
import json
from datetime import datetime

def run_test(cmd, name):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {name}: {e}")
        return False

def main():
    iterations = 10
    victim = "./tests/fragility_benchmark.sh"
    # we want the engine to potentially cause failure, but the victim is currently too robust
    engine_tji = f"bash tools/entropy_engine.sh --tji \"{victim}\" --intensity 5"
    engine_sss = f"bash tools/entropy_engine.sh --sss \"{victim}\" --intensity 5"
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "baseline": {"runs": 0, "fails": 0},
        "noisy_tji": {"runs": 0, "fails": 0},
        "noisy_sss": {"runs": 0, "fails": 0}
    }
    
    for i in range(iterations):
        success = run_test(victim, f"Baseline-{i+1}")
        if success: results["baseline"]["runs"] += 1
        else: results["baseline"]["fails"] += 1

    for i in range(iterations):
        success = run_test(engine_tji, f"TJI-{i+1}")
        if success: results["noisy_tji"]["runs"] += 1
        else: results["noisy_tji"]["fails"] += 1

    for i in range(iterations):
        success = run_test(engine_sss, f"SSS-{i+1}")
        if success: results["noisy_sss"]["runs"] += 1
        else: results["noisy_sss"]["fails"] += 1

    with open("tests/fragility_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n--- Fragility Analysis Summary ---")
    b_rate = (results["baseline"]["fails"] / iterations) * 100 if iterations > 0 else 0
    tji_rate = (results["noisy_tji"]["fails"] / iterations) * 100 if iterations > 0 else 0
    sss_rate = (results["noisy_sss"]["fails"] / iterations) * 100 if iterations > 0 else 0
    print(f"Baseline Fail Rate: {b_rate:.2f}%")
    print(f"TJI Fail Rate:      {tji_rate:.2f}% (Delta: {tji_rate - b_rate:.2f}%)")
    print(f"SSS Fail Rate:      {sss_rate:.2f}% (Delta: {sss_rate - b_rate:.2f}%)")

if __name__ == "__main__":
    main()
