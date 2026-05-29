#!/usr/bin/env python3
"""Governance gate evaluator — measures current state against thresholds, flags violations."""

import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")
THRESHOLDS_FILE = os.path.join(STATE_DIR, "governance-thresholds.json")
INTERVENTIONS_FILE = os.path.join(STATE_DIR, "interventions.json")
CURRENT_STATE_FILE = os.path.join(STATE_DIR, "current-state.json")
PATTERNS_FILE = os.path.join(STATE_DIR, "memories", "patterns.jsonl")
ANCHORS_FILE = os.path.join(STATE_DIR, "memories", "anchors.jsonl")
CONTEXT_FILE = os.path.join(STATE_DIR, "memories", "context.json")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_jsonl(path):
    lines = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def check_state_integrity(thresholds):
    """Check mandatory files exist."""
    mandatory = thresholds.get("mandatory_files", [])
    missing = [f for f in mandatory if not os.path.exists(os.path.join(os.path.dirname(__file__), "..", f))]
    return {"value": len(missing), "missing": missing}


def check_orphan_patterns(thresholds):
    """Count patterns not cited in recent context."""
    patterns = load_jsonl(PATTERNS_FILE) if os.path.exists(PATTERNS_FILE) else []
    pattern_ids = {p.get("id", "") for p in patterns if "id" in p}

    context_ids = set()
    if os.path.exists(CONTEXT_FILE):
        try:
            ctx = load_json(CONTEXT_FILE)
            ctx_str = json.dumps(ctx).lower()
            for pid in pattern_ids:
                if pid.lower() in ctx_str:
                    context_ids.add(pid)
        except Exception:
            pass

    orphans = pattern_ids - context_ids
    return {"value": len(orphans), "orphans": list(orphans)}


def check_cycle_stagnation(thresholds):
    """Days since last cycle commit."""
    if not os.path.exists(CURRENT_STATE_FILE):
        return {"value": 999}

    state = load_json(CURRENT_STATE_FILE)
    ts = state.get("timestamp", "")
    if not ts:
        return {"value": 999}

    try:
        last = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - last).total_seconds() / 86400
        return {"value": round(days, 1)}
    except Exception:
        return {"value": 999}


def check_pattern_density(thresholds):
    """Patterns per 100 cycles — detects accumulation stagnation."""
    patterns = load_jsonl(PATTERNS_FILE) if os.path.exists(PATTERNS_FILE) else []
    pattern_count = len([p for p in patterns if "id" in p])

    if not os.path.exists(CURRENT_STATE_FILE):
        return {"value": 0, "pattern_count": 0}

    state = load_json(CURRENT_STATE_FILE)
    cycle = state.get("cycle", 1)
    density = (pattern_count / max(cycle, 1)) * 100
    return {"value": round(density, 2), "pattern_count": pattern_count, "cycle": cycle}


def evaluate_gates(thresholds, interventions):
    """Run all governance checks, return violations."""
    metrics_config = thresholds.get("metrics", {})
    results = {}

    # State integrity
    si = check_state_integrity(thresholds)
    results["state_integrity"] = si

    # Orphan patterns
    op = check_orphan_patterns(thresholds)
    results["orphan_patterns"] = op

    # Cycle stagnation
    cs = check_cycle_stagnation(thresholds)
    results["cycle_stagnation_days"] = cs

    # Pattern density (derived metric)
    pd_result = check_pattern_density(thresholds)
    results["pattern_density_per_100_cycles"] = pd_result

    # Evaluate against thresholds
    violations = []
    for name, config in metrics_config.items():
        value = results.get(name, {}).get("value", 0)
        warning = config.get("warning")
        critical = config.get("critical")

        level = "OK"
        if critical is not None:
            if name == "signal_to_noise_ratio":
                if value < critical:
                    level = "CRITICAL"
                elif value < warning:
                    level = "WARNING"
            elif name == "cycle_stagnation_days":
                if value >= critical:
                    level = "CRITICAL"
                elif value >= warning:
                    level = "WARNING"
            else:
                if value >= critical:
                    level = "CRITICAL"
                elif value >= warning:
                    level = "WARNING"

        if level != "OK":
            action = config.get("action", "operator_alert")
            intervention = interventions.get("interventions", {}).get(action, {})
            violations.append({
                "metric": name,
                "value": value,
                "level": level,
                "action": action,
                "description": intervention.get("description", config.get("description", ""))
            })

    return results, violations


def main():
    thresholds = load_json(THRESHOLDS_FILE)
    interventions = load_json(INTERVENTIONS_FILE)

    results, violations = evaluate_gates(thresholds, interventions)

    # Output report
    print(f"Governance Gate Report — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    for name, data in results.items():
        value = data.get("value", "-")
        print(f"  {name}: {value}")

    print()
    if violations:
        print(f"VIOLATIONS: {len(violations)}")
        for v in violations:
            print(f"  [{v['level']}] {v['metric']} = {v['value']} → {v['action']}")
            print(f"         {v['description']}")
    else:
        print("All gates clear.")

    # Write governance report to state
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "violations": violations,
        "status": "WARNING" if any(v["level"] == "WARNING" for v in violations)
                 else "CRITICAL" if any(v["level"] == "CRITICAL" for v in violations)
                 else "OK"
    }

    report_path = os.path.join(STATE_DIR, "governance-report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return len(violations)


if __name__ == "__main__":
    sys.exit(main())
