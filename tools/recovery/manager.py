import os
from datetime import datetime
from typing import Dict, Any, Callable

class RecoveryManager:
    """
    Maps health probe failures to corrective actions.
    """
    def __init__(self):
        # Policy mapping: probe_name -> recovery_function
        self.policies: Dict[str, Callable] = {
            "RepoIntegrity": self.recover_missing_files,
            "StateConsistency": self.recover_state_consistency,
            "EnvironmentReadiness": self.notify_creator_critical,
        }

    def execute_recovery(self, probe_name: str, message: str):
        """Attempt to fix the issue defined by the probe failure."""
        if probe_name in self.policies:
            print(f"[RecoveryManager] Attempting recovery for {probe_name}: {message}")
            return self.policies[probe_name](message)
        else:
            print(f"[RecoveryManager] No policy defined for {probe_name}. Logging as warning.")
            return False

    def recover_missing_files(self, message: str) -> bool:
        """Action for missing critical files."""
        # For now, we don't want to blindly recreate state (might lose data).
        # We notify and mark as a task for the creator/next cycle.
        return self.notify_creator("CRITICAL: Missing state files detected. Manual intervention required.", message)

    def recover_state_consistency(self, message: str) -> bool:
        """Action for corrupted or inconsistent state."""
        # If state is fundamentally broken, we might try to restore from git or just alert.
        return self.notify_creator("WARNING: State inconsistency detected. Verify current-state.json.", message)

    def notify_creator_critical(self, message: str) -> bool:
        """Hard failure that requires human intervention."""
        return self.notify_creator("FATAL: Environment readiness failed. System cannot operate.", message)

    def notify_creator(self, title: str, detail: str) -> bool:
        """Append recovery attempt to messages/to-creator.md."""
        timestamp = datetime.now().isoformat()
        log_entry = f"\n### {title}\n- **Time**: {timestamp}\n- **Detail**: {detail}\n- **Status**: Recovery Triggered\n"
        try:
            os.makedirs("messages", exist_ok=True)
            with open("messages/to-creator.md", "a") as f:
                f.write(log_entry)
            return True
        except Exception as e:
            print(f"Failed to write to to-creator.md: {e}")
            return False
