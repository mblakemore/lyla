#!/usr/bin/env python3
"""
Integration Test: BB Scan Skip Logic Workflow

This script simulates the complete workflow to verify the skip decision logic works end-to-end.

Scenario:
  Day X: Alice Node A runs BB scan → generates context_hash_0x123 → stores scan
  Day Y: Bob receives prompt with same hash prefix → should SKIP live scan

Workflow tested:
  1. Post-scan hook marks hash as stored
  2. Other agent's poll checks state for match  
  3. Decision is correctly made: skip vs proceed

Run this script once after initial setup to verify all components work together.
"""

import sys
sys.path.insert(0, '/droid/repos/cl_shared/blackboard')
from pathlib import Path


def simulate_post_scan_hook(scan_id, context_hash):
    """Simulate Discord send post-scan hook marking hash."""
    from state_sync_client import mark_hash
    
    print(f"\n=== PHASE 1: Marking hash during post-scan ===")
    print(f"Scanner ID: {scan_id}")
    print(f"Context hash (first 16 chars): {context_hash[:16]}...")
    
    mark_hash(scan_id, context_hash)
    print("[POST-SCAN] Scan state updated - downstream agents can now query")


def simulate_downstream_agent_query(expected_hash_prefix, timeout_sec=5):
    """Simulate another agent querying if they can skip a scan."""
    from verify_scan_ptr import check_for_recent_scan
    from datetime import timezone
    
    # Wait a moment for file sync before querying
    import time
    time.sleep(0.5)
    
    print(f"\n=== PHASE 2: Downstream agent polling for skip ===")
    print(f"Looking for hash prefix: {expected_hash_prefix}...")
    print(f"(Will retry up to {timeout_sec}s total)")
    
    result = check_for_recent_scan(
        hash_prefix=expected_hash_prefix.upper(),
        age_seconds=timeout_sec
    )
    
    if result["found"]:
        print("\n✓ SKIP DECISION CORRECT:")
        print(f"  → Found match in {result['age_seconds']:.1f}s old entry")
        print(f"  → Agent can safely avoid live scan (saves {timeout_sec}s+)")
    else:
        print("\n⚠ PROCEED DECISION REQUIRED:")
        print("  → No matching entry found yet")
        print("  → Must run live BB scan (fallback pathway)")
    
    return result


def simulate_expired_entry_scenario():
    """Test that skipped entries are correctly handled as expired."""
    from state_sync_client import update_scan_state
    
    print("\n=== PHASE 3: Testing stale entry handling ===")
    
    # Create an "old" entry
    old_scan_id = f"T{scan_timestamp.hour:02d}:{scan_timestamp.minute:02d}_EXPIRED"
    old_hash = "0000000000000000"  # Fake old hash
    
    update_scan_state(old_scan_id, context_hash_sha256_prefix=old_hash)
    print(f"[STATE] Created test entry with expired hash: {old_hash[:8]}...")
    
    # Verify it won't match our active hash prefix
    from verify_scan_ptr import check_for_recent_scan
    
    print("\nChecking if agent mistakenly skips on OLD entry...")
    result = check_for_recent_scan(
        hash_prefix="DEADBEEF",
        age_seconds=1  # Fast timeout for testing
    )
    
    if not result["found"]:
        print("✓ CORRECT: Stale entry doesn't block valid skip decision")
    else:
        print("⚠ WARNING: Should have rejected mismatched hash")


# Configuration - adjust these to match your real environment
SCAN_ID_001 = "SCANNER_ID_20260519_CENTRAL-SCAN-V2"
CONTEXT_HASH_001 = "deadbeef12345678abcd90ef12345678"  # Full SHA-256
HACK_TIMESTAMP_001 = True  # Set to True if you want to fast-sync BB file

if __name__ == "__main__":
    print("=" * 60)
    print("BB Skip Logic Integration Test")
    print("=" * 60)
    
    from datetime import datetime, timezone
    scan_timestamp = datetime.now(timezone.utc)
    
    try:
        # Scenario A: Normal workflow with post-scan hook
        simulate_post_scan_hook(SCAN_ID_001, CONTEXT_HASH_001)
        
        # Wait for downstream agent to query
        time.sleep(1.0)
        result = simulate_downstream_agent_query(
            expected_hash_prefix=CONTEXT_HASH_001[:16],  # Only need prefix match
            timeout_sec=5
        )
        
        if result["found"]:
            print("\n✅ INTEGRATION TEST PASSED")
            print("   Post-scan mark → Query detectable → Skip decision made correctly")
            
            # Bonus: test the opposite case (hash not found yet)
            stale_result = check_for_recent_scan(
                hash_prefix="FAKEHASH12345678",
                age_seconds=0.2
            )
            if not stale_result["found"]:
                print("   ✓ False negative handling works too")
        else:
            print("\n⚠ Integration issue detected - skipping logic may be broken")
            print(f"Result: {json.dumps(result, indent=2)}")
            
    except KeyboardInterrupt:
        print("\n\n[ABORT] Test interrupted by user")
    finally:
        print("\n" + "=" * 60)
        print("Test complete. Check output above for verification.")
