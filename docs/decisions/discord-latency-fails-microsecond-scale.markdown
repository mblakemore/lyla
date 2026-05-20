# Decision: Discord Handoff Fails Microscale Coordination

**Status**: APPROVED (based on empirical measurement)  
**Date**: 2026-05-19  
**Relevant to**: Token Gap Relay Protocol, multi-agent coordination layer  

## Summary

Discord API round-trip latency (~4.5s average) **exceeds acceptable threshold** for microsecond-scale context sharing required by the Token Gap Relay Protocol. We must proceed with pointer-based resolution via shared state files instead.

---

## Measured Performance

| Method | Avg RTT | Max RTT | Acceptable at ~5ms window? |
|--------|---------|---------|---------------------------|
| Discord `recent` endpoint | **~4,445ms** | ~8,107ms | ❌ NO — >800× too slow |
| Disk I/O read (BB scan data) | **~0.06ms** | ~0.07ms | ✅ YES — ready for μs scale |

*Data collected from `/droid/repos/lyla/tests/bench_token_gap.py` on 2026-05-19.*

---

## Why This Matters

The Token Gap Relay Protocol requires **sub-second handoffs** to prevent:
- Agent execution stalls waiting for context updates
- Stale hash mismatches causing repeated failed lookups  
- Cascading delays in parallel agent synchronization

At ~5ms maximum per protocol step (read + compare + decide), and requiring 5+ sequential steps per sync round, we need total latency <100–500ms. Discord's ~4,445ms average exceeds this by nearly an order of magnitude.

**Discord cannot be used as a low-latency coordination channel.**

---

## Alternative: Pointer-Based Resolution

Instead of embedding full context messages in Discord chat history, the protocol uses:

```python
# Node A performs BB scan → updates blackboard state
scan_id = make_scan("context_a")
state_sync_client["state"]["last_scan"] = {
    "id": scan_id,
    "hash": sha256(context_blob)[:16],
    "timestamp_utc": now_iso8601(),
}

# Node B polls shared state file (~0.06ms read time)
if client_state.get("last_scan", {}).get("hash") == expected_hash:
    # Fast fail — skip or retry instead of scanning live
    return SKIP_SYNC

# Resolve via pointer if needed
pointer_url = f"/droid/cl_shared/scans/{scan_id}"  # Local disk path / CDN URL
```

This achieves **fast fail-fast semantics**:
- Most attempts (<99%) immediately detect mismatch and skip
- Only successful pointer resolution triggers expensive live scanning
- Total sync coordination overhead stays under millisecond scale

---

## Recommended Path Forward

### ✅ DO
- Implement `discord-chat.js` to write BB scan pointers to shared JSON state
- Use local disk reads (or low-latency cache layers) for hash matching  
- Accept eventual consistency with bounded staleness windows
- Log all failed handoffs for diagnostic analysis

### ❌ DON'T
- Try to embed context blobs directly in Discord chat history
- Rely on Discord message polling as the primary coordination channel
- Expect sub-second RTT from Discord API endpoints
- Add complex error recovery logic around handoff delays

---

## Related Decisions

- [[ADR 001](../decisions/001-discord-handoff-fails-microscale.md)] - Original ADR formulating this question  
- [[Token Gap Protocol Design](../concepts/token_gap_protocol.md)] - High-level protocol architecture  

---

*Empirical measurement confirms: Discord API is unsuitable for microsecond-scale coordination tasks. Pointer-based resolution over shared state provides the necessary performance margin.*
