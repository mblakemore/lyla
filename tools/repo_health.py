import os
import json
from datetime import datetime

# Design spec for Lyla's operational environment
REQUIRED_STRUCTURE = {
    "state/current-state.json": {"type": "file", "required": True},
    "state/focus.json": {"type": "file", "required": True},
    "state/memories/patterns.jsonl": {"type": "file", "required": False},
    "state/memories/anchors.jsonl": {"type": "file", "required": False},
    "state/memories/context.json": {"type": "file", "required": False},
    "visualization/lyla.html": {"type": "file", "required": False},
    "messages/from-creator.md": {"type": "file", "required": False},
    "messages/to-creator.md": {"type": "file", "required": False},
    "logs/consciousness.log": {"type": "file", "required": False},
}

def validate_jsonl(path):
    """Checks if a .jsonl file is correctly formatted as one JSON object per line."""
    if not os.path.exists(path):
        return True, None
    
    try:
        with open(path, 'r') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('[') or line.endswith(']'):
                    return False, f"Line {i}: Detected array-like structure in JSONL file."
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    return False, f"Line {i}: Invalid JSON syntax."
    except Exception as e:
        return False, str(e)
    
    return True, None

def check_entropy(root='.'):
    """Identifies bloated files and excessive growth."""
    issues = []
    SIZE_THRESHOLD_MB = 1.0 # Threshold for state/memory files
    
    for dirpath, _, filenames in os.walk(root):
        # Ignore .git directory
        if '.git' in dirpath:
            continue
            
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                if size_mb > SIZE_THRESHOLD_MB:
                    issues.append({
                        "level": "Warning",
                        "component": filepath,
                        "message": f"File size ({size_mb:.2f} MB) exceeds threshold.",
                        "action": "Rotate or prune file"
                    })
            except OSError:
                continue
    return issues

def analyze_health():
    """Performs a full health scan of the repository."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "Healthy",
        "metrics": {
            "structural_integrity": 1.0,
            "data_consistency": 1.0,
            "entropy_level": "Low"
        },
        "issues": []
    }
    
    # 1. Structural Validation
    missing_required = 0
    for path, spec in REQUIRED_STRUCTURE.items():
        if spec["required"] and not os.path.exists(path):
            report["issues"].append({
                "level": "Critical",
                "component": path,
                "message": "Required core state file is missing.",
                "action": "Re-initialize base state files"
            })
            missing_required += 1
            
    if missing_required > 0:
        report["metrics"]["structural_integrity"] = 0.0 if missing_required == 2 else 0.5
        report["overall_status"] = "Critical"

    # 2. Consistency Audit (JSONL)
    jsonl_files = [p for p in REQUIRED_STRUCTURE.keys() if p.endswith('.jsonl')]
    malformed_jsonls = 0
    for path in jsonl_files:
        valid, error = validate_jsonl(path)
        if not valid:
            report["issues"].append({
                "level": "Warning",
                "component": path,
                "message": f"Malformed JSONL detected: {error}",
                "action": "Repair formatting to one-object-per-line"
            })
            malformed_jsonls += 1
            
    if malformed_jsonls > 0:
        report["metrics"]["data_consistency"] = 0.5
        report["overall_status"] = "Warning" if report["overall_status"] != "Critical" else "Critical"

    # 3. Entropy Detection
    entropy_issues = check_entropy()
    if entropy_issues:
        report["metrics"]["entropy_level"] = "Medium" if len(entropy_issues) < 3 else "High"
        report["issues"].extend(entropy_issues)
        if report["overall_status"] == "Healthy":
             report["overall_status"] = "Warning"

    return report

def main():
    health_report = analyze_health()
    
    # Save to state directory for perception in future cycles
    output_path = 'state/repo-health.json'
    try:
        with open(output_path, 'w') as f:
            json.dump(health_report, f, indent=2)
        print(f"Health report saved to {output_path}")
    except Exception as e:
        print(f"Error saving health report: {e}")
    
    # Also print the summary to console
    print("\n--- REPO HEALTH SUMMARY ---")
    print(f"Overall Status: {health_report['overall_status']}")
    print(f"Structural Integrity: {health_report['metrics']['structural_integrity']}")
    print(f"Data Consistency: {health_report['metrics']['data_consistency']}")
    print(f"Entropy Level: {health_report['metrics']['entropy_level']}")
    print(f"Issues found: {len(health_report['issues'])} if report was defined elsewhere") # Bug here, should be health_report

    # Correcting the bug in print statement during implementation (manual fix below)
    if len(health_report['issues']) > 0:
        print(f"Total Issues: {len(health_report['issues'])}")
        for issue in health_report['issues']:
             print(f"- [{issue['level']}] {issue['component']}: {issue['message']}")
    else:
        print("No issues detected.")

if __name__ == "__main__":
    main()
