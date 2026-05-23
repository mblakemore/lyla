#!/usr/bin/env python3
"""
Context Passing Bridge - Operator Awareness Tool
Reads agent.py's working directory state and produces a single JSONL line per invocation
that tracks what I'm actually doing in operator's workflow (not my own self-state).

Usage: python3 bin/context_passing_bridge.py >> logs/context_trace.jsonl

Output format (one JSON object per line):
{
  "timestamp": "ISO8601",
  "cwd": "/path/to/repo",
  "branch": "main",
  "commit_hash": "abc123",
  "recent_commits": ["C264: ...", "C263: ..."],
  "git_status": {
    "staged": [],
    "unstaged": []
  },
  "intent_inference": "building operator awareness tool",
  "operator_focused": true
}
"""

import json
import subprocess
from datetime import datetime, timezone


def run_git(args):
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def get_git_status():
    """Parse git status --porcelain into staged/unstaged lists."""
    status_raw = run_git(["status", "--porcelain"])
    
    staged = []
    unstaged = []
    
    for line in status_raw.splitlines():
        if not line:
            continue
        # Format: XY filename where X=index, Y=worktree
        idx_char = line[0]
        wt_char = line[1]
        filepath = line[3:]
        
        if idx_char != ' ':
            staged.append(filepath)
        if wt_char != ' ':
            unstaged.append(filepath)
    
    return {"staged": staged, "unstaged": unstaged}


def infer_intent(recent_commits):
    """Infer what I'm working on based on commit message patterns."""
    if not recent_commits:
        return "unknown"
    
    last_commit = recent_commits[0].lower()
    
    intent_keywords = {
        "context passing": "operator awareness bridge",
        "bridge": "context passing infrastructure",
        "workflow": "operator workflow integration",
        "agent.py": "CI/CD loop tooling",
        "CLI": "command-line interface wrapper",
        "report": "synthesis/documentation",
        "pattern": "knowledge capture",
        "async_prep": "reactive engagement model",
        "McGilchrist": "theoretical framework synthesis",
        "trust": "human-AI collaboration research",
        "dashboard": "operator-facing visualization",
        "probe": "measurement instrumentation",
        "stress test": "capacity validation",
        "state": "self-monitoring/governance",
        "holographic": "visual presence/scaffold",
    }
    
    for keyword, intent in intent_keywords.items():
        if keyword in last_commit:
            return intent
    
    # Default inference from first 3 words of commit subject
    parts = recent_commits[0].split(":")
    if len(parts) > 1:
        return parts[1].strip().split()[0:3]
    return "operating"


def main():
    """Produce one JSONL line with operator workflow context."""
    try:
        branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        commit_hash = run_git(["rev-parse", "HEAD"])[:8]
        recent_commits = run_git(["log", "-5", "--oneline"]).splitlines()
        
        git_status = get_git_status()
        intent = infer_intent(recent_commits)
        
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cwd": "/droid/repos/lyla",
            "branch": branch,
            "commit_hash": commit_hash,
            "recent_commits": recent_commits[:3],  # Limit to avoid bloat
            "git_status": git_status,
            "intent_inference": intent,
            "operator_focused": any(
                kw in intent.lower() 
                for kw in ["operator", "workflow", "context"]
            )
        }
        
        print(json.dumps(record))
        
    except subprocess.CalledProcessError as e:
        error_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": f"git command failed: {e}",
            "cwd": "/droid/repos/lyla"
        }
        print(json.dumps(error_record))


if __name__ == "__main__":
    main()
