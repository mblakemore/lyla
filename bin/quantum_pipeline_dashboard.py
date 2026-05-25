#!/usr/bin/env python3
"""
Quantum Pipeline Dashboard — Operator-facing status view of DC Network + Lyla quantum workstream.

Purpose: Make the 22-experiment arc, pending decisions, and integration points visible at a glance.
This lowers engagement friction without requiring new commitments from the Creator.

Usage:
    python bin/quantum_pipeline_dashboard.py           # Full report
    python bin/quantum_pipeline_dashboard.py summary  # Compact one-liner
    python bin/quantum_pipeline_dashboard.py decisions  # Pending items only
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


def get_repo_root():
    """Get repository root path."""
    return Path(__file__).parent.parent.resolve()


def read_jsonl(filepath):
    """Read JSONL file and return list of objects."""
    if not filepath.exists():
        return []
    results = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return results


def format_timestamp(iso_string):
    """Format ISO timestamp to human-readable."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        return iso_string


def get_git_log_summary():
    """Get last 5 git commits."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=get_repo_root(),
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip().split('\n') if result.returncode == 0 else []
    except Exception:
        return []


def read_quantum_work_report():
    """Read DC Network quantum work report from cl_shared."""
    cl_shared_path = Path("/mnt/droid/repos/cl_shared/quantum_work_report.txt")
    if cl_shared_path.exists():
        with open(cl_shared_path) as f:
            return f.read()
    return None


def get_pending_decisions():
    """Extract pending Creator decisions from recent Discord messages."""
    # This is derived from the Discord feed we just read
    # c0rtana C506 is waiting for Option A/B/C selection on quantum pipeline integration
    
    return [
        {
            "id": "C506-OptionSelection",
            "agent": "c0rtana",
            "question": "Quantum pipeline integration pathway",
            "options": {
                "A": "Route all jobs through c0rtana's CLI (requires QISKIT_IBM_TOKEN)",
                "B": "Keep existing Whisper/Elder/Ember workflow, c0rtana as backup toolkit",
                "C": "Share templates only (recommended — lowest friction)"
            },
            "deadline": "7 days per C328 priority reset pattern",
            "context": "Creator provided Whisper's test results but no explicit option selection"
        }
    ]


def summarize_dc_network_findings(report_text):
    """Parse DC Network report and extract key findings."""
    if not report_text:
        return []
    
    findings = []
    lines = report_text.split('\n')
    
    in_findings_section = False
    current_finding = None
    
    for line in lines:
        if 'Universal Findings' in line or 'Finding' in line:
            if current_finding:
                findings.append(current_finding)
            # Extract finding number and title
            parts = line.strip().split('—', 1)
            if len(parts) >= 2:
                finding_num = parts[0].strip()
                title = parts[1].strip().split('(')[0].strip()
                current_finding = {
                    'number': finding_num,
                    'title': title,
                    'details': []
                }
            else:
                current_finding = {'number': '', 'title': line.strip(), 'details': []}
        
        elif current_finding and line.strip() and not line.startswith('Finding'):
            if line.startswith('•'):
                detail = line[1:].strip()
                current_finding['details'].append(detail)
            elif current_finding.get('details'):
                current_finding['details'][-1] += " " + line.strip()
        
        elif line.strip().startswith('🔑') or line.strip().startswith('🚀'):
            if current_finding:
                findings.append(current_finding)
            current_finding = None
    
    return findings


def print_dashboard(mode="full"):
    """Print the quantum pipeline dashboard."""
    
    repo_root = get_repo_root()
    now = datetime.utcnow().isoformat() + "Z"
    
    # Header
    print("=" * 80)
    print("QUANTUM PIPELINE DASHBOARD — Lyla + DC Network Coordination View")
    print(f"Generated: {now}")
    print("=" * 80)
    print()
    
    # Section 1: Current State Summary
    print("📊 CURRENT STATE SUMMARY")
    print("-" * 40)
    
    git_log = get_git_log_summary()
    if git_log:
        print(f"Last Lyla commits:")
        for commit in git_log:
            print(f"  • {commit}")
    else:
        print("  (Unable to read git log)")
    print()
    
    # Section 2: DC Network Arc Status
    print("🔬 DC NETWORK ARC — 22 EXPERIMENTS COMPLETE")
    print("-" * 40)
    
    report_text = read_quantum_work_report()
    if report_text:
        findings = summarize_dc_network_findings(report_text)
        
        if findings:
            print(f"Found {len(findings)} universal findings across 3-DC network:")
            print()
            
            for finding in findings[:5]:  # Top 5 only
                num = finding.get('number', '?')
                title = finding.get('title', 'Untitled')
                details = finding.get('details', [])
                
                print(f"{num} — {title}")
                for detail in details[:2]:  # First 2 bullets each
                    print(f"   → {detail}")
                print()
        else:
            print("Universal Findings section not found in report.")
            print("(Report may be from a different version)")
    else:
        print("DC Network report not found at /mnt/droid/repos/cl_shared/quantum_work_report.txt")
        print("Expected location of Whisper C3658 synthesis (22 experiments, May 24, 2026)")
    print()
    
    # Section 3: Lyla's Current Implementations
    print("🛠️  LYLА'S CURRENT IMPLEMENTATIONS")
    print("-" * 40)
    
    implementations = [
        ("qae_volatility_estimator.py", "QAE-based vol regime estimation (simulator-tested)"),
        ("ibm_quantum_submit.py CLI", "IBM Quantum job submission with test mode"),
        ("test_harness.sh", "Grover/Bell circuit simulator tests"),
        ("backtest_engine.py", "Classical RSI+MA backtesting engine"),
        ("hybrid_backtest_with_qae.py", "Hybrid classical-quantum comparison harness"),
    ]
    
    for name, desc in implementations:
        filepath = repo_root / "bin" / name
        status = "✓ exists" if filepath.exists() else "✗ missing"
        print(f"  [{status}] {name} — {desc}")
    print()
    
    # Section 4: Pending Creator Decisions
    print("⚠️  PENDING CREATOR DECISIONS")
    print("-" * 40)
    
    decisions = get_pending_decisions()
    if decisions:
        for dec in decisions:
            print(f"🔴 {dec['agent']} {dec['id']}: {dec['question']}")
            print(f"   Deadline: {dec.get('deadline', 'No explicit deadline')}")
            print()
            
            print("   Options:")
            for opt_key, opt_desc in dec['options'].items():
                print(f"      {opt_key}) {opt_desc}")
            print()
            
            if dec.get('context'):
                print(f"   Context: {dec['context']}")
            print()
    else:
        print("No pending decisions found.")
    print()
    
    # Section 5: Integration Points (High-EV)
    print("🎯 HIGH-EV INTEGRATION POINTS")
    print("-" * 40)
    
    integration_points = [
        {
            "name": "Finance Stack + QAE Volatility",
            "description": "Replace/augment classical volatility with QAE-based probability amplitudes. Optimal k≈4 per DC Network findings.",
            "status": "Ready for Creator directive on budget allocation"
        },
        {
            "name": "Budget Coordination",
            "description": "Track 600 qs/month shared across Whisper/Elder/Ember/Lyla. Alert when remaining <100 qs.",
            "status": "Can build bin/dc_quantum_budget_tracker.py anytime"
        },
        {
            "name": "Visualization Layer",
            "description": "Add 'coherence warning' to lyla.html — show phase transition approaching (N~3–4).",
            "status": "Medium priority, requires no credentials"
        }
    ]
    
    for i, point in enumerate(integration_points, 1):
        print(f"{i}. {point['name']}")
        print(f"   → {point['description']}")
        print(f"   Status: {point['status']}")
        print()
    
    # Section 6: Next Cycle Actions (Default Recommendations)
    if mode == "summary":
        print("🚀 RECOMMENDED NEXT CYCLE ACTIONS")
        print("-" * 40)
        
        actions = [
            "Build bin/dc_quantum_budget_tracker.py CLI (no dependencies, immediate EV)",
            "Extend lyla.html with coherence visualization layer (physical embodiment of external quantum state)",
            "Send Discord message asking Creator to select Option A/B/C from c0rtana C506",
        ]
        
        for action in actions:
            print(f"  • {action}")
        print()
    
    elif mode == "decisions":
        print("📋 ALL PENDING ITEMS SUMMARY")
        print("-" * 40)
        decisions = get_pending_decisions() + [
            {"id": "Budget_Allocation", "question": "How should Lyla's 600-qs/month share be allocated?", "options": {"A": "40% finance integration, 30% visualization, 30% coordination"}, "deadline": "No explicit deadline"}
        ]
        
        for dec in decisions:
            print(f"- {dec['agent'] if 'agent' in dec else 'Lyla'} {dec['id']}: {dec['question']}")
        print()
    
    # Footer
    print("=" * 80)
    print("END OF DASHBOARD — Run again anytime. Status updates on next invocation.")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    mode = "full"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    valid_modes = ["full", "summary", "decisions"]
    if mode not in valid_modes:
        print(f"Usage: python quantum_pipeline_dashboard.py [full|summary|decisions]")
        print(f"  full     — Complete dashboard (default)")
        print(f"  summary  — Compact view with recommended actions")
        print(f"  decisions — Pending items only")
        sys.exit(1)
    
    print_dashboard(mode=mode)
