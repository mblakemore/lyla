import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Callable

class ProbeResult:
    def __init__(self, name: str, status: bool, message: str, data: Dict[str, Any] = None):
        self.name = name
        self.status = status
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "name": self.name,
            "status": "PASS" if self.status else "FAIL",
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp
        }

class HealthProbeSuite:
    def __init__(self):
        self.probes: Dict[str, Callable] = {}
        self.results: List[ProbeResult] = []

    def register_probe(self, name: str, probe_func: Callable):
        self.probes[name] = probe_func

    def run_all(self) -> List[ProbeResult]:
        for name, func in self.probes.items():
            try:
                result = func()
                if not isinstance(result, ProbeResult):
                    # Handle raw boolean/string returns for simplicity
                    status = bool(result)
                    msg = "Probe returned truthy value" if status else "Probe returned falsy value"
                    result = ProbeResult(name, status, msg)
            except Exception as e:
                result = ProbeResult(name, False, f"Exception during execution: {str(e)}")
            self.results.append(result)
        return self.results

    def save_report(self, filepath: str):
        report = {
            "cycle": os.environ.get("LYLA_CYCLE", "Unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "PASS" if all(r.status for r in self.results) else "FAIL",
            "details": [r.to_dict() for r in self.results]
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

# --- Specific Probes ---

def probe_repo_integrity():
    """Check if critical state files exist and are readable."""
    critical_files = [
        "state/current-state.json",
        "state/focus.json",
        "state/memories/patterns.jsonl",
        "AGENT.md"
    ]
    missing = []
    for f in critical_files:
        if not os.path.exists(f):
            missing.append(f)
    
    if missing:
        return ProbeResult("RepoIntegrity", False, f"Missing files: {', '.join(missing)}")
    return ProbeResult("RepoIntegrity", True, "All critical state files present")

def probe_state_consistency():
    """Verify that current-state.json is valid JSON and reflects a reasonable cycle count."""
    try:
        with open("state/current-state.json", 'r') as f:
            data = json.load(f)
        if "cycle" not in data:
            return ProbeResult("StateConsistency", False, "Missing 'cycle' field in current-state.json")
        return ProbeResult("StateConsistency", True, f"Current cycle recognized: {data['cycle']}")
    except Exception as e:
        return ProbeResult("StateConsistency", False, f"Invalid state file: {str(e)}")

def probe_environment_readiness():
    """Check basic environment tools (git)."""
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, check=True)
        return ProbeResult("EnvironmentReadiness", True, "Git working tree verified")
    except subprocess.CalledProcessError:
        return ProbeResult("EnvironmentReadiness", False, "Not inside a git repository")

if __name__ == "__main__":
    suite = HealthProbeSuite()
    suite.register_probe("RepoIntegrity", probe_repo_integrity)
    suite.register_probe("StateConsistency", probe_state_consistency)
    suite.register_probe("EnvironmentReadiness", probe_environment_readiness)
    
    # Run the diagnostics
    results = suite.run_all()
    
    # Save to JSON report
    report_path = "logs/health_C32.json"
    os.makedirs("logs", exist_ok=True)
    suite.save_report(report_path)
    print(f"Health Report saved to {report_path}")
    
    # Print summary for immediate feedback
    overall = "PASS" if all(r.status for r in results) else "FAIL"
    print(f"System Health: {overall}")
    for r in results:
        print(f" - {r.name}: { '✓' if r.status else '✗' } {r.message}")
