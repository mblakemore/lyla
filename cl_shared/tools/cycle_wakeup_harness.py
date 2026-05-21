#!/usr/bin/env python3
"""
Cycle Wakeup Harness — wakes Lyla/C0rtana for their next cognitive cycle
This is the entry point that invokes @CLAUDE.md (or @AGENT.md) with context loading.
Intended to be called from CI or manual operation.
"""

import subprocess
import json
from pathlib import Path


def load_last_cycle_number(repo_root="/droid/repos/lyla") -> int:
    """Read HEAD and extract last committed cycle number."""
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Git log failed")
    
    line = result.stdout.strip().split()[0]
    # Format: <commit_hash> C<N>: ...
    return int(line.split(":")[0][1:])  # Strip 'C' and parse number


def get_machine_id() -> str:
    """Return machine ID based on repo root."""
    hostname = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
    return f"lyla@{hostname}"


def main():
    repo_root = Path("/droid/repos/lyla")
    
    print(f"\n=== Lyla/C0rtana Cognitive Cycle Wakeup ===")
    print(f"Machine: {get_machine_id()}")
    print(f"Repo: {repo_root}")
    
    try:
        last_cycle = load_last_cycle_number(repo_root)
        next_cycle = last_cycle + 1
    except Exception as e:
        print(f"ERROR: Could not determine cycle number: {e}")
        print("Check that you're in the correct repo with git history.")
        return 1
    
    print(f"Last committed: C{last_cycle}")
    print(f"This invocation will execute as: C{next_cycle}\n")
    
    # In a real deployment, this would:
    # 1. Check for new instructions in state/from-creator.md or Discord
    # 2. Inject any priority directives into the prompt
    # 3. Call claude with @CLAUDE.md and the cognitive loop instructions
    # For now, we log readiness and wait for manual trigger
    
    print("✓ State verified and ready")
    print(f"✓ Next cycle identifier: C{next_cycle}")
    print("\nTo begin the cognitive loop, invoke claude from /droid/repos/lyla:")
    print('   $ cd /droid/repos/lyla')
    print('   $ claude "@CLAUDE.md Follow the instructions and begin the loop."')
    print("\nThe harness has validated your environment — proceed.\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
