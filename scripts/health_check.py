import json
import os
from datetime import datetime
import subprocess

# Configuration: Core files that must exist for the system to be considered healthy
CORE_FILES = [
    "state/current-state.json",
    "state/focus.json",
    "state/memories/patterns.jsonl",
    "visualization/lyla.html"
]

def check_files():
    missing = [f for f in CORE_FILES if not os.path.exists(f)]
    return (len(missing) == 0, missing)

def check_git_status():
    try:
        status = subprocess.check_output(["git", "status", "--short"]).decode('utf-8')
        return (len(status) == 0, status if status else "Clean")
    except Exception as e:
        return (False, str(e))

def main():
    files_ok, missing_files = check_files()
    git_ok, git_info = check_git_status()
    
    status = "Healthy"
    issues = []
    
    if not files_ok:
        status = "Unhealthy"
        issues.append(f"Missing core files: {missing_files}")
    
    if not git_ok:
        # Git drift is a Warning unless critical files are missing
        if status == "Healthy":
            status = "Warning"
        issues.append(f"Git drift detected: {git_info}")

    health_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": status,
        "metrics": {
            "structural_integrity": 1.0 if files_ok else 0.5,
            "data_consistency": 1.0 if git_ok else 0.7,
            "entropy_level": "Low" if (files_ok and git_ok) else "Medium"
        },
        "checks": {
            "core_files": "OK" if files_ok else "FAIL",
            "git_status": "OK" if git_ok else "DRIFT"
        },
        "issues": issues
    }

    os.makedirs("state", exist_ok=True)
    with open("state/repo-health.json", "w") as f:
        json.dump(health_report, f, indent=4)
    
    print(f"Health check completed. Status: {status}")

if __name__ == "__main__":
    main()
