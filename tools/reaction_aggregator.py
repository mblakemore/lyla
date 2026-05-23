#!/usr/bin/env python3
"""
Reaction Feedback Aggregator - Synthesizes operator fidelity signals

Reads logs/operator_fidelity.jsonl and produces summary statistics
for trust calibration analysis. Implements right-hemisphere attunement
measurement per P_096/P_097.

Usage:
    python reaction_aggregator.py aggregate --output reports/fidelity_baseline_C253.md
    python reaction_aggregator.py stats --json  # Raw JSON output for dashboards
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

LOG_PATH = Path(__file__).parent.parent / 'logs' / 'operator_fidelity.jsonl'
REPORTS_PATH = Path(__file__).parent.parent / 'reports'


def read_logs():
    """Read all fidelity log entries from JSONL."""
    if not LOG_PATH.exists():
        return []
    
    entries = []
    with open(LOG_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def compute_statistics(entries):
    """Compute basic fidelity metrics."""
    feedback_entries = [e for e in entries if e.get('event') == 'feedback_received']
    
    if not feedback_entries:
        return {
            'total_feedback': 0,
            'message_count': 0,
            'distribution': {},
            'avg_responses_per_message': 0.0
        }
    
    # Count by feedback type
    by_type = defaultdict(int)
    for entry in feedback_entries:
        by_type[entry['feedback_type']] += 1
    
    total = len(feedback_entries)
    
    # Unique message IDs (some messages may get multiple reactions over time)
    unique_messages = set(e.get('message_id') for e in feedback_entries if e.get('message_id'))
    
    # Time distribution (hour of day)
    hour_dist = defaultdict(int)
    for entry in feedback_entries:
        ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
        hour_dist[ts.hour] += 1
    
    stats = {
        'total_feedback': total,
        'unique_messages': len(unique_messages),
        'avg_responses_per_message': total / max(len(unique_messages), 1),
        'by_type': dict(by_type),
        'distribution_pct': {k: round(v/total*100, 1) for k, v in by_type.items()},
        'hourly_distribution': dict(hour_dist)
    }
    
    return stats


def generate_report(stats):
    """Generate markdown report from statistics."""
    now = datetime.utcnow().isoformat() + 'Z'
    
    if stats['total_feedback'] == 0:
        report = f"""# Fidelity Feedback Baseline Report

**Generated:** {now}  
**Status:** No operator feedback received yet — system deployed but awaiting biological time.

---

## Summary

The reaction-feedback mechanism is operational and ready to capture presentational knowledge signals from operators using async_prep suggestions.

### Next Steps

- Deploy with actual operator engagement (not just testing)
- Collect N≥10 responses before drawing conclusions
- Compare distribution patterns against left-hemisphere metrics (latency, throughput) to validate McGilchrist VII-IX thesis

---

*See P_096/P_097 for design rationale.*
"""
    else:
        felt_heard_pct = stats['distribution_pct'].get('felt_heard', 0)
        
        report = f"""# Operator Fidelity Feedback Baseline

**Generated:** {now}  
**Data period:** First week of operation  

---

## Executive Summary

{stats['total_feedback']} operator feedback entries collected via reaction buttons on {stats['unique_messages']} unique suggestion messages. 

**Primary signal:** {felt_heard_pct}% of reactions indicate operators "felt heard" by async_prep suggestions ({stats['by_type'].get('felt_heard', 0)} instances).

This suggests {"strong alignment between AI suggestions and operator attentional stance" if felt_heard_pct > 60 else "moderate misalignment — consider right-hemisphere attunement refinements"} per McGilchrist VII-IX framework.

---

## Detailed Breakdown

### Response Distribution

| Signal | Count | Percentage | Interpretation |
|--------|-------|------------|----------------|
| ✅ Felt heard | {stats['by_type'].get('felt_heard', 0):3d} | {felt_heard_pct:5.1f}% | Right-hemisphere attuned — contextually relevant |
| ⚠️ Off-target | {stats['by_type'].get('off_target', 0):3d} | {stats['distribution_pct'].get('off_target', 0):5.1f}% | Left-hemisphere optimization dominant (efficient but misaligned) |
| 💡 Helpful incomplete | {stats['by_type'].get('helpful_incomplete', 0):3d} | {stats['distribution_pct'].get('helpful_incomplete', 0):5.1f}% | Partial fidelity — good framing, missing something |
| 🔄 Not relevant | {stats['by_type'].get('not_relevant', 0):3d} | {stats['distribution_pct'].get('not_relevant', 0):5.1f}% | Map-replacing-territory error |

### Temporal Patterns

Responses by hour of day (UTC):
"""
        for hour in sorted(stats['hourly_distribution'].keys()):
            count = stats['hourly_distribution'][hour]
            bar = '█' * min(count, 40)
            report += f"  {hour:02d}:00 — {count:3d} responses {bar}\n"
        
        report += f"""
---

## Design Rationale (P_096/P_097)

This feedback channel implements **two-dimensional trust calibration**:

1. **Statistical confidence** (from async_prep's existing confidence tagging based on historical accuracy)
2. **Process fidelity signal** (qualitative "felt heard?" via frictionless emoji reactions)

Left-hemisphere optimization alone erodes epistemic fidelity even when technical metrics are perfect. Presentational knowledge measurement captures relational quality that propositional metrics miss.

---

*Synthesized from logs/operator_fidelity.jsonl — see source for raw data.*
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description='Reaction Feedback Aggregator')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # aggregate command
    agg_parser = subparsers.add_parser('aggregate', help='Generate markdown report')
    agg_parser.add_argument('--output', '-o', help='Output file path')
    
    # stats command
    stats_parser = subparsers.add_parser('stats', help='Print JSON statistics')
    stats_parser.add_argument('--json', action='store_true', help='Raw JSON output')
    
    args = parser.parse_args()
    
    entries = read_logs()
    stats = compute_statistics(entries)
    
    if args.command == 'aggregate':
        report = generate_report(stats)
        
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report written to {args.output}")
        else:
            print(report)
    
    elif args.command == 'stats':
        print(json.dumps(stats, indent=2))
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
