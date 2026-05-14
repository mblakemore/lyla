import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any

# Import HealthProbeSuite from the existing tool
try:
    from tools.health_probe import HealthProbeSuite, probe_repo_integrity, probe_state_consistency, probe_environment_readiness
    from tools.recovery.manager import RecoveryManager
except ImportError:
    import sys
    sys.path.append(os.getcwd())
    from tools.health_probe import HealthProbeSuite, probe_repo_integrity, probe_state_consistency, probe_environment_readiness
    from tools.recovery.manager import RecoveryManager

class PerceptionOrchestrator:
    def __init__(self):
        self.suite = HealthProbeSuite()
        self.recovery = RecoveryManager()
        # Register base probes
        self.suite.register_probe("RepoIntegrity", probe_repo_integrity)
        self.suite.register_probe("StateConsistency", probe_state_consistency)
        self.suite.register_probe("EnvironmentReadiness", probe_environment_readiness)

    def get_current_state(self) -> Dict[str, Any]:
        try:
            with open("state/current-state.json", 'r') as f:
                return json.load(f)
        except Exception:
            return {"error": "Could not read current-state.json"}

    def get_focus(self) -> Dict[str, Any]:
        try:
            with open("state/focus.json", 'r') as f:
                return json.load(f)
        except Exception:
            return {"error": "Could not read focus.json"}

    def get_recent_logs(self, count=5) -> List[str]:
        try:
            res = subprocess.run(["git", "log", "--oneline", f"-{count}"], capture_output=True, text=True)
            return res.stdout.strip().split('\n') if res.stdout else []
        except Exception:
            return []

    def synthesize(self):
        # 1. Run health probes
        results = self.suite.run_all()
        
        # --- NEW: TRIGGER RECOVERY ACTIONS ---
        for r in results:
            if not r.status:
                self.recovery.execute_recovery(r.name, r.message)
        
        health_status = "PASS" if all(r.status for r in results) else "FAIL"
        
        # 2. Gather state
        state = self.get_current_state()
        focus = self.get_focus()
        history = self.get_recent_logs()

        # 3. Construct perception summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "system_health": {
                "overall": health_status,
                "details": [r.to_dict() for r in results]
            },
            "internal_context": {
                "current_cycle": state.get("cycle"),
                "last_phase": state.get("phase"),
                "active_goal": focus.get("goal"),
                "current_task": focus.get("current_task")
            },
            "environmental_signal": {
                "recent_commits": history
            }
        }
        return summary

if __name__ == "__main__":
    orchestrator = PerceptionOrchestrator()
    perception = orchestrator.synthesize()
    
    print("\n=== LYLA PERCEPTION SUMMARY ===")
    print(f"Health: {perception['system_health']['overall']}")
    for detail in perception['system_health']['details']:
        status_mark = "✓" if detail['status'] == "PASS" else "✗"
        print(f" [{status_mark}] {detail['name']}: {detail['message']}")
    
    ctx = perception['internal_context']
    print(f"\nCycle: {ctx['current_cycle']} | Phase: {ctx['last_phase']}")
    print(f"Goal:  {ctx['active_goal']}")
    print(f"Task:  {ctx['current_task']}")
    
    print("\nRecent History:")
    for commit in perception['environmental_signal']['recent_commits']:
        print(f" - {commit}")
    print("==============================\n")
