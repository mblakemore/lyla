# Blackboard Scan Skip Logic — Integration Guide

## Overview

This infrastructure implements **cross-agent skip decision logic** for BB scans across distributed scanners. It allows downstream agents (Node B/C) to detect when Node A has already performed a scan, avoiding redundant work by checking shared state rather than re-running scans locally.

## Components

### Core Scripts

| File | Purpose | Location |
|------|---------|----------|
| `digest.py` | Generate SHA-256 context hashes from input strings | `/droid/repos/cl_shared/blackboard/` |
| `verify_scan_ptr.py` | Query if matching scan exists in shared state | Same directory |
| `state_sync_client.py` | Update/query scan history after successful scans | `blackboard_utils/` |

### Shared State File

**Path:** `/droid/cl_shared/state_sync_client.json`  
**Schema:** JSON array of scan entries with `id`, `timestamp_utc`, and context hash prefix

Each entry looks like:
```json
{
  "id": "SCANNER_ID_20260519_CENTRAL-SCAN-V2",
  "timestamp_utc": "2026-05-19T14:32:15Z",
  "context_key": "DEADBEEF12345678..."
}
```

## Workflow Diagram

```
┌─────────────────────┐
│  Node A Scanner     │
│  (Alice)            │
│                     │
│  1. Run BB Scan     │
│  2. Get scan_id     │
│  3. Post-scan hook  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐    ┌──────────────────────────┐
│ Discord send()      │──→ │ state_sync_client.py     │
│   + mark_scan()     │    │   update_scan_state()    │
└─────────────────────┘    │ → Updates shared JSON file│
                           └────────────┬─────────────┘
                                        │
                                        ▼
                              ┌──────────────────────────┐
                              │ Shared State File        │
                              │ /droid/cl_shared/...json │
                              └────────────┬─────────────┘
                                           │
                              ┌────────────▼──────────────┐
                              │ Polling by other agents  │
                              │ verify_scan_ptr.py       │
                              │ check_for_recent_scan()  │
                              └──────────────────────────┘
```

## Integration Points

### 1. Node A (Scanner Agent) — Pre-Scan Check

Before initiating a BB scan, check if the context was recently scanned:

```javascript
// In scanner-agent.js or similar
import {checkForRecentScan} from '/droid/repos/cl_shared/blackboard/verify_scan_ptr.js';

async function shouldSkipScan(contextHashPrefix) {
  const result = await checkForRecentScan({
    hash_prefix: contextHashPrefix,
    age_seconds: 3600  // Allow skip up to 1h old entries
  });
  
  return result.found;  // true → SKIP scan
}
```

**Usage:** Run this 5 minutes before starting expensive scan operations. If it returns `true`, proceed with existing results rather than re-scanning.

### 2. Post-Scan Hook (after scan_id retrieved)

When a new scan completes and the agent receives its ID, mark it in shared state so downstream agents can detect it:

```javascript
// Discord send hook runs AFTER successful scan initiation
async function postScanMark(scanId, contextHashSha256Prefix) {
  const subprocess = await execCommand(
    'python3 /droid/repos/lyla/blackboard_utils/state_sync_client.py update --id "' + 
    scanId + '" --hash-prefix "' + 
    contextHashSha256Prefix + '"'
  );
  console.log('Post-scan mark complete:', subprocess.stdout);
}
```

**Timing:** This must run **after** receiving `scan_id` from the BB system (typically immediately after `send() → response`), not during hash generation.

### 3. Downstream Agent — Skip Decision Query

Before deciding whether to launch a new scan for a given context hash:

```bash
# Call verify_scan_ptr.py directly
node -e "
const {checkForRecentScan} = require('/droid/repos/cl_shared/blackboard/verify_scan_ptr.js');

(async () => {
  const result = await checkForRecentScan({
    hash_prefix: 'DEADBEEF12345678',  // First 16 chars of SHA-256
    age_seconds: 3600                 // Accept entries up to 1 hour old
  });
  
  if (result.found) {
    console.log('SKIP LIVE SCAN - existing result available');
    console.log('Matched at:', result.matched_at);
    console.log('Entry age:', Math.floor(result.age_seconds), 'seconds');
    process.exit(0);  // Signal: skip OK
  } else {
    console.log('NO MATCH - MUST RUN LIVE SCAN');
    process.exit(1);  // Signal: proceed with scan
  }
})();
"
```

**Return codes:**
- Exit `0` → Skip OK, don't run live scan
- Exit non-zero → No match found, must run live scan

## Usage Examples

### Example A: Pre-scan query during idle loop

During background polling before expensive operations:

```javascript
// Periodically check if previous scans can be skipped
async function periodicSkipCheck(contextId, contextHash) {
  const recent = await checkForRecentScan({
    hash_prefix: contextHash.substring(0, 16),
    age_seconds: 3600  // Check last hour
  });
  
  if (recent.found) {
    logger.info(`Skipping ${contextId}: match from ${Math.floor(recent.age_seconds)}s ago`);
    return recent.scan_id;  // Can reference existing scan result
  }
}
```

### Example B: Real-time skip verification just before starting heavy work

In a high-stakes scenario where avoiding redundant computation is critical:

```python
from verify_scan_ptr import check_for_recent_scan

result = check_for_recent_scan(hash_prefix='DEADBEEF', age_seconds=2.5)

if not result['found']:
    print("SKIP CHECK FAILED - MUST PROCEED WITH SCAN")
    # Continue with BB initiation logic
    initiate_live_scan()
else:
    print(f"SKIP CONFIRMED: using {result['scan_id']} from {result['age_seconds']:.1f}s ago")
    # Skip live scan and use cached results
    load_existing_results(result['scan_id'])
```

## Testing the Integration

Run the integration test to verify all components communicate correctly:

```bash
# From repo root
cd /droid/repos/lyla/blackboard_utils && python3 integration_test_bb_skip_logic.py
```

Expected output:
- ✅ "POST-SCAN mark successful"
- ✅ "SKIP DECISION CORRECT" after querying shared state
- ✅ "False negative handling works too" (if hash truly not found yet)

If tests fail, check:
1. `state_sync_client.json` exists and is writable
2. Python 3 is in PATH (`which python3`)
3. `/droid/cl_shared/` directory has write permissions
4. No concurrent writes corrupting JSON (use file locking if needed)

### Manual Test Case

For quick verification without full test suite:

```bash
# Create a mock entry
python3 blackboard_utils/state_sync_client.py \
  --update \
  --id "TEST_SCAN_001" \
  --hash-prefix "ABCD1234567890EF"

# Verify it's searchable
./blackboard_utils/query_scan_state.sh --limit 5

# Should show TEST_SCAN_001 with matching prefix
```

## Common Pitfalls & Solutions

### Issue: Shared state file not being written

**Symptoms:** `FileNotFoundError` or missing entries in state query  
**Cause:** Incorrect path permissions or wrong directory structure  
**Fix:** Ensure `/droid/cl_shared/` exists and is writable by the agent process

### Issue: Hash mismatch even though scan exists

**Symptoms:** Agent misses valid skip opportunity  
**Causes:** 
- Hash prefix case mismatch (SHA hex can be upper/lowercase)
- Not enough characters matched (need minimum 12-16 chars for uniqueness)
- Polling too fast before shared state syncs from disk to memory

**Fixes:**
1. Normalize all hashes to uppercase before comparison (`context_key = context_key.upper()`)
2. Always use at least 16-character prefixes: `sha256[:16]`
3. Add 0.5–1s buffer after post-scan hook before downstream agents poll

### Issue: Multiple scans matching same hash

**Symptoms:** Confusing results showing multiple matches  
**Design decision:** Only **newest** entry matters (prepend list order)  
**Mitigation:** The system only stores first N entries sorted by timestamp — older redundant entries are dropped automatically when limit reached

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Query latency | <5ms typical | Reading ~10-entry array + linear search |
| Post-scan overhead | ~50ms | File I/O + JSON parse/write cycle |
| State file size | ~2KB per 100 scans | Each entry is ~24 bytes plus metadata |
| Memory usage | Negligible | <1MB even with full history kept |

For production workloads, consider adding exponential backoff on missed skips (avoid aggressive polling that floods disk I/O).

## Extension Points

### Adding TTL (Time-To-Live) for scan entries

To prevent indefinite accumulation of stale entries:

```python
# Add to state_sync_client.py update_scan_state()
MAX_ENTRY_AGE_SECONDS = 86400  # 24 hours

def should_keep_entry(entry, max_age):
    age = time.time() - datetime.fromisoformat(entry['timestamp_utc']).timestamp()
    return age <= max_age

# During query, filter expired entries before returning matches
entries_active = [e for e in data['scans'] if should_keep_entry(e, MAX_ENTRY_AGE_SECONDS)]
```

### Per-context skip policies

Different contexts may have different acceptable staleness windows:

```javascript
// Context-specific skip thresholds
const SKIP_POLICIES = {
  'HIGH_ENTROPY': 3600,      // Skip up to 1h old
  'LOW_STAKES': 86400,       // Skip up to 24h old  
  'CRITICAL_PATH': 900       // Only skip 15min max
};

function getSkipWindow(contextType) {
  return SKIP_POLICIES[contextType] || 3600;  // default 1h
}
```

## Security Considerations

**Hash trust boundary:** The context hash prefix is derived from input strings and BB scan metadata. It's intended as a lightweight identifier — not cryptographic proof of scan integrity. For security-critical applications where you must guarantee "this scan was actually performed by a trusted scanner," add additional attestation mechanisms (signatures, TLS channels, etc.).

**State file exposure:** The shared JSON file lives on disk at `/droid/cl_shared/state_sync_client.json`. Ensure appropriate filesystem permissions are set so only authorized agents can read/write it. In multi-agent environments with untrusted participants, consider encryption or access control lists (ACLs) for this path.

## Future Enhancements

Potential improvements for v2:

- [ ] Distributed lock / optimistic locking during state updates
- [ ] WebSocket pub-sub model replacing polling loop
- [ ] Redis-backed fast lookup for high-throughput scenarios  
- [ ] Canonical scan result reference IDs mapped to context hashes
- [ ] Cross-cluster awareness if scanners span multiple machines

For now, the current implementation handles local agent coordination efficiently without requiring external infrastructure dependencies.

---

This integration enables distributed AI systems to avoid redundant work through minimal yet effective cross-process signaling. By treating BB scans as first-class citizens in skip logic rather than opaque operations, the system achieves both efficiency and transparency.
