import json
import os
from datetime import datetime

def evaluate_governance():
    thresholds_path = 'state/governance-thresholds.json'
    health_path = 'state/repo-health.json'
    patterns_path = 'state/memories/patterns.jsonl'

    with open(thresholds_path, 'r') as f:
        thresholds = json.load(f)

    results = {}
    overall_status = "Healthy"
    issues = []

    # 1. Check State Integrity (Mandatory Files)
    missing_files = []
    for file in thresholds['mandatory_files']:
        if not os.path.exists(file):
            missing_files.append(file)
    
    integrity_count = len(missing_files)
    results['state_integrity'] = integrity_count
    if integrity_count >= thresholds['metrics']['state_integrity']['critical']:
        overall_status = "Critical"
        issues.append(f"Missing critical state files: {missing_files}")
    elif integrity_count >= thresholds['metrics']['state_integrity']['warning']:
        if overall_status != "Critical": overall_status = "Warning"
        issues.append(f"Some mandatory files missing: {missing_files}")

    # 2. Check Orphan Patterns (Simplified for this cycle: total count vs warning)
    try:
        with open(patterns_path, 'r') as f:
            pattern_count = sum(1 for line in f if line.strip())
        results['orphan_patterns'] = pattern_count # Simplified proxy for now
        if pattern_count >= thresholds['metrics']['orphan_patterns']['critical']:
            if overall_status != "Critical": overall_status = "Critical"
            issues.append("Pattern density exceeds critical threshold.")
        elif pattern_count >= thresholds['metrics']['orphan_patterns']['warning']:
             if overall_status not in ["Critical", "Warning"]: overall_status = "Warning"
             issues.append("Pattern density is increasing; consider pruning.")
    except FileNotFoundError:
        results['orphan_patterns'] = 0

    # 3. Cycle Stagnation (Using git log to check last commit date)
    import subprocess
    try:
        last_commit_date = subprocess.check_output(['git', 'log', '-1', '--format=%ct']).decode().strip()
        days_since = (int(datetime.now().timestamp()) - int(last_commit_date)) / 86400
        results['cycle_stagnation_days'] = round(days_since, 2)
        if days_since >= thresholds['metrics']['cycle_stagnation_days']['critical']:
            overall_status = "Critical"
            issues.append(f"Severe stagnation: {round(days_since, 2)} days since last cycle.")
        elif days_since >= thresholds['metrics']['cycle_stagnation_days']['warning']:
            if overall_status != "Critical": overall_status = "Warning"
            issues.append(f"Stagnation warning: {round(days_since, 2)} days since last cycle.")
    except Exception as e:
        results['cycle_stagnation_days'] = "Error"

    # Update health report
    health_data = {}
    if os.path.exists(health_path):
        with open(health_path, 'r') as f:
            try: health_data = json.load(f)
            except: pass

    health_data['timestamp'] = datetime.now().isoformat()
    health_data['overall_status'] = overall_status
    health_data['governance_metrics'] = results
    health_data['governance_issues'] = issues

    with open(health_path, 'w') as f:
        json.dump(health_data, f, indent=4)

    print(f"Governance Evaluation Complete. Status: {overall_status}")
    for issue in issues:
        print(f" - {issue}")

if __name__ == "__main__":
    evaluate_governance()
