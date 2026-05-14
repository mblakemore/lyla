import json
import glob
import os

def calculate_failure_rate(report_data):
    """Calculate the percentage of probes that failed in a report."""
    details = report_data.get("details", [])
    if not details:
        return 0.0
    
    fails = sum(1 for item in details if item.get("status") == "FAIL")
    return (fails / len(details)) * 100

def analyze():
    """Compare the two most recent health reports to detect trends."""
    # Get all files matching the pattern and sort them
    files = sorted(glob.glob("state/health_archive/health_*.json"))
    
    if len(files) < 2:
        print(f"Insufficient data for trend analysis: found {len(files)} archives, need at least 2.")
        return None

    try:
        with open(files[-2], 'r') as f:
            prev_report = json.load(f)
        with open(files[-1], 'r') as f:
            curr_report = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading archive files: {e}")
        return None

    prev_fail_rate = calculate_failure_rate(prev_report)
    curr_fail_rate = calculate_failure_rate(curr_report)

    trend = {
        "comparison": {
            "previous": {"cycle": prev_report.get("cycle", "unknown"), "file": files[-2]},
            "current": {"cycle": curr_report.get("cycle", "unknown"), "file": files[-1]}
        },
        "metrics": {
            "prev_fail_rate": prev_fail_rate,
            "curr_fail_rate": curr_fail_rate,
            "delta": curr_fail_rate - prev_fail_rate
        },
        "status": "STABLE"
    }

    if trend["metrics"]["delta"] > 0:
        trend["status"] = "DEGRADED"
    elif trend["metrics"]["delta"] < 0:
        trend["status"] = "IMPROVING"

    return trend

if __name__ == "__main__":
    result = analyze()
    if result:
        print(json.dumps(result, indent=2))
    else:
        exit(1)
