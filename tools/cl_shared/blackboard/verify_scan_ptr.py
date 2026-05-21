#!/usr/bin/env python3
"""
BB-Sync Scan Pointer Verification Utility

This module verifies whether a local scan match exists before triggering live BB scans.
It implements the fast fail-fast path of the Token Gap Relay Protocol.

Usage:
    python verify_scan_ptr.py --expected-hash <sha256-prefix> --timeout-sec 10
    
Returns exit code:
    0 → Match found in history, SKIP live scanning
    1 → No match, proceed with live scan or sync attempt
"""

import argparse
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


def find_state_sync_client():
    """Find where state_sync_client.json is stored."""
    paths = [
        "/droid/cl_shared/state_sync_client.json",
        "/tmp/state_sync_client.json", 
        "/dev/shm/state_sync_client.json",
    ]
    
    for p in paths:
        if Path(p).exists():
            return p
    raise FileNotFoundError("state_sync_client.json not found at expected locations")


def load_bb_scan_history(path=None):
    """Load Blackboard scan history from shared state file."""
    if not path:
        path = find_state_sync_client()
    
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Navigate to scan history (schema may vary)
        scans = []
        for key in ["state.scans", "scans", "sync.history"]:
            value = data
            for segment in key.split('.'):
                value = value.get(segment, {}) if isinstance(value, dict) else None
                if not value:
                    break
            if value and isinstance(value, list):
                scans.extend(value)
        
        if not scans:
            print("[WARN] No scan entries found in bb-sync state")
            return data
        
        return {"data": data, "scans": scans}
        
    except Exception as e:
        print(f"[ERROR] Failed to load BB sync state: {e}")
        raise


def compute_sha256_prefix(text, prefix_len=16):
    """Compute SHA-256 hash prefix of given text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:prefix_len].upper()


def check_for_recent_scan(hash_prefix, age_seconds=None, max_attempts=3, state_file=None):
    """Check if a matching scan exists in recent history."""
    
    result = load_bb_scan_history(path=state_file)
    data = result["data"]
    scans = result.get("scans", [])
    
    print(f"\n[INFO] Found {len(scans)} scan entries in state file")
    print(f"[INFO] Looking for hash prefix: {hash_prefix}")
    
    # Track how long we've been waiting
    start_time = datetime.now(timezone.utc)
    attempts_made = 0
    
    while True:
        for scan_entry in reversed(scans[-max_attempts:]):
            entry_hash = scan_entry.get("hash", "").upper().strip()
            
            if not entry_hash:
                continue
            
            # Match on prefix or full hash
            if entry_hash.startswith(hash_prefix) or entry_hash == hash_prefix.upper():
                match_ts_str = scan_entry.get("timestamp_utc", "unknown")
                
                try:
                    ts = datetime.fromisoformat(match_ts_str.replace('Z', '+00:00'))
                    age = (datetime.now(timezone.utc) - ts).total_seconds()
                    age_label = f"{age:.1f}s old"
                except Exception:
                    age_label = "(parse error)"
                
                print(f"\n[SUCCESS] Hash match found!")
                print(f"  - Scan ID: {scan_entry.get('id', 'N/A')}")
                print(f"  - Hash:    {entry_hash[:32]}...")  
                print(f"  - Time:    {match_ts_str}")
                print(f"  - Age:     {age_label}")
                
                return {
                    "found": True,
                    "scan_id": scan_entry.get("id"),
                    "matched_at": str(datetime.now()),
                    "age_seconds": age if 'age' in dir() else None
                }
        
        attempts_made += 1
        
        # Respect timeout
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        if age_seconds and elapsed >= age_seconds:
            break
            
        if attempts_made < max_attempts:
            delay = min(0.5, age_seconds or 2)  # Small backoff between retries
            print(f"[WAIT] No match yet ({attempts_made}/{max_attempts}), retrying in {delay:.1f}s...")
            import time
            time.sleep(delay)
    
    print("\n[NOT-FOUND] No matching scan detected after timeouts.")
    return {"found": False, "message": "no_match"}


def main():
    parser = argparse.ArgumentParser(description="Verify BB scan pointer for skip/sync decision")
    parser.add_argument("--expected-hash", required=True, help="SHA-256 prefix of context hash to find")
    parser.add_argument("--timeout-sec", type=float, default=5, help="Max wait time before giving up")
    parser.add_argument("--state-path", help="Custom path to state_sync_client.json (for testing)")
    args = parser.parse_args()
    
    # Override default state path for testing purposes
    import os
    test_path = getattr(args, 'state_path', None) or "/droid/cl_shared/blackboard/active_board.json"
    if not Path(test_path).exists():
        test_path = "test_scan_data.json"  # Default fallback for demo runs
    
    if args.state_path and Path(args.state_path).exists():
        test_path = args.state_path
    
    result = check_for_recent_scan(
        hash_prefix=args.expected_hash.upper(),
        age_seconds=args.timeout_sec,
        state_file=test_path
    )
    
    exit_code = 0 if result["found"] else 1
    
    print(f"\n[RESULT] {'MATCH FOUND - SKIP LIVE SCAN' if result['found'] else 'NO MATCH - PROCEED'}")
    print(json.dumps(result, indent=2))
    
    exit(exit_code)


if __name__ == "__main__":
    main()
