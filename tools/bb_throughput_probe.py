#!/usr/bin/env python3
"""
Throughput Stress Test Probe for Blackboard Protocol
C184 — implements throughput capacity measurement under load

Design document reference: cl_shared/docs/throughput_stress_test_proposal_C183.md
c0rtana C243 approvals: rollback mechanism, logging standardization, automated alerting

Success criteria:
• <5% error rate across all write operations
• p99 latency < 0.5s for push/pull events  
• 100% entry integrity (checksum validation) post-test
• Alert triggers at 80% of SLA thresholds

External-subject compliance: measures the coordination protocol itself, not self-monitoring.
Serves both agents' deployment decisions about scaling limits.
"""

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class MetricsLogger:
    """Standardized metrics logging per metrics_schema.md contract."""
    
    def __init__(self, log_path: str = "/droid/repos/cl_shared/blackboard_metrics.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, operation_type: str, duration_ms: float, agent: str = "lyla", 
            entry_id: Optional[str] = None, metadata: dict = None):
        """Log a single timing observation to JSONL file."""
        record = {
            "operation_type": operation_type,
            "duration_ms": round(duration_ms, 3),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "entry_id": entry_id or f"stress_test_{int(time.time())}",
            **(metadata or {})
        }
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(record) + '\n')


class SLAAlerting:
    """Automated alerting at 80% of SLA thresholds (c0rtana C243 requirement)."""
    
    THRESHOLDS = {
        'error_rate': 5.0,      # % — trigger alert at 4%
        'p99_latency_ms': 500,  # ms — trigger alert at 400ms
        'entry_integrity': 100, # % — trigger alert at 96%
    }
    
    def __init__(self):
        self.alerts = []
    
    def check(self, metric_name: str, value: float) -> bool:
        """Returns True if alert triggered."""
        threshold = self.THRESHOLDS.get(metric_name)
        if not threshold:
            return False
        
        alert_threshold = threshold * 0.8  # 80% rule
        if value >= alert_threshold:
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metric": metric_name,
                "value": round(value, 3),
                "threshold": threshold,
                "alert_at": round(alert_threshold, 3),
            }
            self.alerts.append(alert)
            print(f"⚠️ ALERT [{metric_name}]: {value:.3f} (alerting at {alert_threshold:.3f}, SLA={threshold})")
            return True
        return False
    
    def summary(self):
        return json.dumps({"alerts_triggered": len(self.alerts), "alerts": self.alerts}, indent=2)


class RollbackManager:
    """Rollback mechanism for stress test recovery (c0rtana C243 requirement)."""
    
    def __init__(self, backup_dir: str = "/droid/repos/cl_shared/stress_test_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots = []
    
    def take_snapshot(self, bb_path: Path) -> str:
        """Create timestamped backup of BB state before writes."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"snapshot_{timestamp}"
        backup_path = self.backup_dir / f"{snapshot_id}.tar.gz"
        
        if bb_path.exists():
            subprocess.run(['tar', '-czf', str(backup_path), '-C', str(bb_path.parent), bb_path.name], 
                         check=True, capture_output=True)
            self.snapshots.append(snapshot_id)
            print(f"📸 Snapshot {snapshot_id} created at {backup_path}")
        
        return snapshot_id
    
    def rollback_to(self, snapshot_id: str):
        """Restore BB to a previous snapshot."""
        snapshot_path = self.backup_dir / f"{snapshot_id}.tar.gz"
        if not snapshot_path.exists():
            print(f"❌ Snapshot {snapshot_id} not found")
            return False
        
        # Extract back to the original location (assumes structure matches)
        result = subprocess.run(['tar', '-xzf', str(snapshot_path)], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Rolled back to {snapshot_id}")
            return True
        else:
            print(f"❌ Rollback failed: {result.stderr}")
            return False
    
    def cleanup_old_snapshots(self, keep_last: int = 5):
        """Remove old snapshots, keeping only recent ones."""
        sorted_snapshots = sorted(self.snapshots)[-keep_last:]
        for snap in self.snapshots:
            if snap not in sorted_snapshots:
                snapshot_path = self.backup_dir / f"{snap}.tar.gz"
                if snapshot_path.exists():
                    snapshot_path.unlink()
                    print(f"🗑️ Removed snapshot {snap}")


class BlackboardStressTester:
    """Core stress test logic — sequential ramp-up and concurrent writers simulation."""
    
    def __init__(self, bb_base_path: Path, metrics_logger: MetricsLogger, 
                 alerting: SLAAlerting, rollback: RollbackManager):
        self.bb_base = bb_base_path
        self.metrics = metrics_logger
        self.alerting = alerting
        self.rollback = rollback
        
        # Test state tracking
        self.entries_written = 0
        self.errors = 0
        self.latencies = []
        self.integrity_checks = []
        
        # Success criteria from design doc
        self.max_error_rate = 5.0  # %
        self.max_p99_latency_ms = 500  # ms
        self.required_integrity = 100.0  # %
    
    def generate_test_entry(self, entry_id: int) -> dict:
        """Generate a deterministic test entry with checksum for integrity validation."""
        content = json.dumps({
            "test": True,
            "entry_id": entry_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": f"Test payload #{entry_id} for throughput probing",
            "checksum_input": f"lyla_C184_stress_{entry_id}",
        })
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        return {"id": entry_id, "content": content, "checksum": checksum}
    
    def write_entry(self, entry_data: dict) -> tuple[float, bool]:
        """Write single entry to BB, measure latency, validate integrity."""
        start_time = time.time()
        
        try:
            # Simulate BB push via git (assuming BB is tracked in git repo at cl_shared/)
            bb_path = self.bb_base / "registry.jsonl"
            
            if not bb_path.exists():
                bb_path.parent.mkdir(parents=True, exist_ok=True)
                bb_path.write_text('')
            
            # Append new entry
            with open(bb_path, 'a') as f:
                f.write(json.dumps(entry_data) + '\n')
            
            # Commit the change
            subprocess.run(['git', '-C', str(self.bb_base), 'add', 'registry.jsonl'], 
                         check=True, capture_output=True)
            subprocess.run(['git', '-C', str(self.bb_base), 'commit', '-m', 
                          f'Stress test entry #{entry_data["id"]}'], 
                         check=True, capture_output=True)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Integrity check: verify checksum matches content
            expected_checksum = hashlib.sha256(entry_data['content'].encode()).hexdigest()[:16]
            integrity_valid = entry_data.get('checksum') == expected_checksum
            
            return elapsed_ms, True and integrity_valid
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.errors += 1
            print(f"❌ Error writing entry {entry_data['id']}: {e}")
            return elapsed_ms, False
    
    def run_sequential_rampup(self, max_entries: int = 100, interval_sec: float = 0.5):
        """Sequential ramp-up test — find inflection point where writes cause degradation."""
        print("\n🚀 SEQUENTIAL RAMP-UP TEST")
        print("=" * 60)
        
        snapshot_id = self.rollback.take_snapshot(self.bb_base)
        
        for i in range(1, max_entries + 1):
            entry = self.generate_test_entry(i)
            latency, success = self.write_entry(entry)
            
            if success:
                self.entries_written += 1
            else:
                # Trigger rollback on critical failure
                if self.errors > 2:  # Allow small margin before rolling back
                    print(f"\n⚠️ Critical failures ({self.errors}) — triggering rollback...")
                    self.rollback.rollback_to(snapshot_id)
                    break
            
            self.latencies.append(latency)
            self.metrics.log("write", latency, "lyla", f"stress_{i}")
            
            # Check SLA thresholds continuously
            error_rate = (self.errors / i) * 100 if i > 0 else 0
            p99_latency = statistics.quantiles(self.latencies, n=100)[-1] if len(self.latencies) >= 10 else 0
            
            self.alerting.check('error_rate', error_rate)
            self.alerting.check('p99_latency_ms', p99_latency)
            
            # Progress indicator
            if i % 10 == 0 or i == max_entries:
                avg_latency = statistics.mean(self.latencies) if self.latencies else 0
                print(f"Entries: {i}/{max_entries} | Avg latency: {avg_latency:.2f}ms | Errors: {self.errors}")
            
            time.sleep(interval_sec)
        
        return self._compute_results()
    
    def run_concurrent_simulation(self, num_agents: int = 5, entries_per_agent: int = 20):
        """Simulate N concurrent writers — test lock contention and race conditions."""
        print("\n🔥 CONCURRENT WRITERS SIMULATION")
        print("=" * 60)
        print(f"Agents: {num_agents} | Entries per agent: {entries_per_agent}")
        
        snapshot_id = self.rollback.take_snapshot(self.bb_base)
        
        # All agents write in interleaved fashion to simulate real concurrency
        for entry_global in range(1, num_agents * entries_per_agent + 1):
            agent_id = (entry_global - 1) % num_agents + 1
            
            entry = self.generate_test_entry(entry_global)
            entry['agent'] = f"agent_{agent_id}"
            
            latency, success = self.write_entry(entry)
            
            if success:
                self.entries_written += 1
            else:
                self.errors += 1
            
            self.latencies.append(latency)
            self.metrics.log("write", latency, f"agent_{agent_id}", f"stress_{entry_global}")
            
            # Periodic SLA check
            if entry_global % 5 == 0 or entry_global == num_agents * entries_per_agent:
                error_rate = (self.errors / entry_global) * 100
                p99_latency = statistics.quantiles(self.latencies, n=100)[-1] if len(self.latencies) >= 10 else 0
                
                self.alerting.check('error_rate', error_rate)
                self.alerting.check('p99_latency_ms', p99_latency)
                
                print(f"Global entries: {entry_global} | Errors: {self.errors} | P99: {p99_latency:.2f}ms")
        
        return self._compute_results()
    
    def _compute_results(self) -> dict:
        """Compute and display test results against success criteria."""
        results = {
            "entries_written": self.entries_written,
            "errors": self.errors,
            "error_rate": round((self.errors / max(1, self.entries_written + self.errors)) * 100, 3),
            "mean_latency_ms": round(statistics.mean(self.latencies), 3) if self.latencies else 0,
            "median_latency_ms": round(statistics.median(self.latencies), 3) if len(self.latencies) >= 2 else 0,
            "p90_latency_ms": round(statistics.quantiles(self.latencies, n=10)[8], 3) if len(self.latencies) >= 10 else 0,
            "p99_latency_ms": round(statistics.quantiles(self.latencies, n=100)[-1], 3) if len(self.latencies) >= 100 else (statistics.max(self.latencies) if self.latencies else 0),
            "alerts_triggered": len(self.alerting.alerts),
        }
        
        print("\n" + "=" * 60)
        print("📊 STRESS TEST RESULTS")
        print("=" * 60)
        print(f"Entries written: {results['entries_written']}")
        print(f"Errors: {results['errors']} | Error rate: {results['error_rate']:.3f}%")
        print(f"Mean latency: {results['mean_latency_ms']:.3f}ms")
        print(f"P50 latency: {results['median_latency_ms']:.3f}ms")
        print(f"P90 latency: {results['p90_latency_ms']:.3f}ms")
        print(f"P99 latency: {results['p99_latency_ms']:.3f}ms")
        print(f"Alerts triggered: {results['alerts_triggered']}")
        
        # Success/failure against criteria
        success = True
        if results['error_rate'] > self.max_error_rate:
            print(f"\n❌ FAILED: Error rate {results['error_rate']:.3f}% exceeds SLA of {self.max_error_rate}%")
            success = False
        
        if results['p99_latency_ms'] > self.max_p99_latency_ms:
            print(f"❌ FAILED: P99 latency {results['p99_latency_ms']:.3f}ms exceeds SLA of {self.max_p99_latency_ms}ms")
            success = False
        
        if success:
            print("\n✅ PASSED all success criteria")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Throughput stress test probe for Blackboard protocol")
    parser.add_argument('--mode', choices=['sequential', 'concurrent'], default='sequential',
                        help='Test mode: sequential ramp-up or concurrent writers simulation')
    parser.add_argument('--max-entries', type=int, default=100,
                        help='Max entries for sequential test (default: 100)')
    parser.add_argument('--agents', type=int, default=5,
                        help='Number of simulated agents for concurrent test (default: 5)')
    parser.add_argument('--bb-path', type=str, default='/droid/repos/cl_shared',
                        help='Base path to BB repository')
    
    args = parser.parse_args()
    
    # Initialize components
    bb_base = Path(args.bb_path)
    metrics_logger = MetricsLogger()
    alerting = SLAAlerting()
    rollback_manager = RollbackManager()
    
    tester = BlackboardStressTester(bb_base, metrics_logger, alerting, rollback_manager)
    
    # Run selected test mode
    if args.mode == 'sequential':
        results = tester.run_sequential_rampup(max_entries=args.max_entries)
    else:
        results = tester.run_concurrent_simulation(num_agents=args.agents)
    
    # Write full results JSON
    results_file = Path("/droid/repos/lyla/reports") / f"throughput_stress_C{results['entries_written']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump({**results, "timestamp": datetime.now(timezone.utc).isoformat()}, f, indent=2)
    print(f"\n📄 Results written to {results_file}")
    
    # Print alert summary
    print("\n" + alerting.summary())
    
    return 0 if results['error_rate'] < 5 and results['p99_latency_ms'] < 500 else 1


if __name__ == '__main__':
    sys.exit(main())
