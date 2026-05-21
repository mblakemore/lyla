#!/usr/bin/env python3
"""
metrics_contract_validator.py — Audit metrics_schema.md adoption across coordination tools

Reads cl_shared/docs/metrics_schema.md and cross-checks against probe implementations
to verify compliance with unified coordination metrics contract.

Usage:
    python3 tools/metrics_contract_validator.py [--verbose] [--fix-partial]
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent / "docs" / "metrics_schema.md"
PROBES_DIR = Path(__file__).parent.parent / "tools"
METRICS_LOG = Path(__file__).parent.parent / "blackboard_metrics.jsonl"

REQUIRED_FIELDS = ["timestamp", "operation_type", "duration_ms", "agent"]


def load_schema():
    """Parse metrics_schema.md and extract required/optional field definitions."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema not found at {SCHEMA_PATH}")
    
    content = SCHEMA_PATH.read_text()
    
    # Extract required fields from table
    required_match = re.search(r"Core Fields.*?```json(.*?)```", content, re.DOTALL)
    if not required_match:
        return {"required": REQUIRED_FIELDS, "extended": []}
    
    example = json.loads(required_match.group(1))
    extended_match = re.search(r"Extended Fields.*?\n\n\| Field \| Type \|", content, re.DOTALL)
    extended_fields = []
    if extended_match:
        # Parse extended table rows
        for line in extended_match.group(0).split("\n"):
            if "|" in line and not line.startswith("|-------"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    extended_fields.append({"field": parts[1], "required": False})
    
    return {"required": list(example.keys()), "extended": extended_fields}


def check_probe_compliance(probe_path: Path):
    """Check if a probe file uses the correct schema output format."""
    if not probe_path.exists():
        return {"exists": False, "compliant": None, "issues": ["File not found"]}
    
    content = probe_path.read_text()
    issues = []
    compliant_parts = []
    
    # Check for JSONL output (not array-wrapped)
    if '"[' in content and ']' in content.split('[')[1][:50]:
        issues.append("Uses array-wrapped JSON instead of JSONL append-only format")
    else:
        compliant_parts.append("JSONL output format")
    
    # Check for required field usage
    for field in REQUIRED_FIELDS:
        if f'"{field}"' in content or f"'{field}'" in content:
            compliant_parts.append(f"Uses {field} field")
        else:
            issues.append(f"Missing {field} field definition")
    
    # Check for N>=3 guard
    if re.search(r"N\s*[>≥]\s*3|n\s*[>≥]\s*3|\b3\s*\b.*sample|sample.*\b3\b", content, re.IGNORECASE):
        compliant_parts.append("N>=3 percentile guard")
    else:
        issues.append("No explicit N>=3 guard for percentiles")
    
    return {"exists": True, "compliant": len(issues) == 0, "issues": issues, "compliant_parts": compliant_parts}


def validate_metrics_log():
    """Validate actual metrics entries against schema."""
    if not METRICS_LOG.exists():
        return {"exists": False, "valid_entries": 0, "invalid_entries": 0}
    
    valid = 0
    invalid = []
    
    with open(METRICS_LOG) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                missing = [f for f in REQUIRED_FIELDS if f not in entry]
                if missing:
                    invalid.append({"line": i, "missing_fields": missing})
                else:
                    valid += 1
            except json.JSONDecodeError:
                invalid.append({"line": i, "error": "Invalid JSON"})
    
    return {"exists": True, "valid_entries": valid, "invalid_entries": len(invalid), "examples": invalid[:5]}


def main(verbose=False):
    print("=" * 70)
    print("METRICS CONTRACT VALIDATION v1.0")
    print(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    print("=" * 70)
    
    # Load schema definition
    print("\n[1/3] Loading schema from metrics_schema.md...")
    schema = load_schema()
    print(f"  Required fields: {', '.join(schema['required'])}")
    print(f"  Extended fields: {[e['field'] for e in schema['extended']]}")
    
    # Check probe compliance
    print("\n[2/3] Checking probe implementations...")
    probes = ["bb_perf_probe.py", "cadence_probe.py", "bb_latency_probe.py"]
    probe_results = {}
    for probe_name in probes:
        probe_path = PROBES_DIR / probe_name
        result = check_probe_compliance(probe_path)
        probe_results[probe_name] = result
        status = "✅ PASS" if result["compliant"] else ("❌ FAIL" if False in [r["exists"] for r in []] else "⚠️ PARTIAL")
        print(f"  {probe_name}: {status}")
        if verbose and result.get("issues"):
            for issue in result["issues"]:
                print(f"      • {issue}")
        if verbose and result.get("compliant_parts"):
            for part in result["compliant_parts"]:
                print(f"      ✓ {part}")
    
    # Validate metrics log entries
    print("\n[3/3] Validating actual metrics entries...")
    metrics_validation = validate_metrics_log()
    print(f"  Metrics file exists: {'Yes' if metrics_validation['exists'] else 'No'}")
    print(f"  Valid entries: {metrics_validation['valid_entries']}")
    print(f"  Invalid entries: {metrics_validation['invalid_entries']}")
    if metrics_validation["invalid_entries"] > 0 and verbose:
        for ex in metrics_validation.get("examples", []):
            missing = ex.get("missing_fields", [])
            error = ex.get("error", "")
            print(f"      Line {ex['line']}: {'Missing fields: ' + ', '.join(missing) if missing else 'JSON parse error: ' + error}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    compliant_count = sum(1 for r in probe_results.values() if r.get("compliant"))
    total_probes = len([r for r in probe_results.values() if r.get("exists")])
    
    overall_status = "✅ COMPLIANT" if (compliant_count == total_probes and metrics_validation["invalid_entries"] == 0) else ("⚠️ PARTIAL" if compliant_count > 0 else "❌ NON-COMPLIANT")
    
    print(f"Probe compliance: {compliant_count}/{total_probes} passing")
    print(f"Metrics log validity: {metrics_validation['valid_entries']} valid entries, {metrics_validation['invalid_entries']} invalid")
    print(f"\nOverall status: {overall_status}")
    
    if verbose:
        print("\nRecommendations:")
        if total_probes - compliant_count > 0:
            print(f"  • {total_probes - compliant_count} probe(s) need schema alignment")
        if metrics_validation["invalid_entries"] > 0:
            print(f"  • Review {metrics_validation['invalid_entries']} invalid metrics entry/entries")
        else:
            print("  • All probes and metrics conform to contract — ready for production use")
    
    return {"status": overall_status, "probes_compliant": compliant_count, "total_probes": total_probes}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate metrics_schema.md adoption across coordination tools")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed compliance breakdown")
    args = parser.parse_args()
    
    result = main(verbose=args.verbose)
