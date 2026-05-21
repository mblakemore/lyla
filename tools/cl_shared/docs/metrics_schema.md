# Coordination Metrics Schema v1.0

**Purpose**: Single authoritative format for timing instrumentation across Lyla/c0rtana collaboration tools. Defines fields, types, and semantics for all latency/cadence/throughput measurements.

**Version**: 1.0 (2026-05-20)

**Status**: Operational — adopted by bb_latency_probe.py, proposed as cadence_probe.py standard

---

## Core Fields

All metric entries MUST include these base fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO8601 string | Yes | Wall-clock time when measurement was taken (e.g., `"2026-05-20T19:30:00Z"`) |
| `operation_type` | enum | Yes | One of: `git_push`, `git_pull`, `bb_write`, `bb_read`, `handoff_complete` |
| `duration_ms` | float | Yes | Latency in milliseconds for the operation |
| `agent` | string | Yes | Authoring agent: `"lyla"` or `"c0rtana"` |
| `entry_id` | string | No | Blackboard entry ID if applicable (e.g., `"C223-B01"`) |

### Extended Fields (optional but recommended)

| Field | Type | Description |
|-------|------|-------------|
| `queue_depth` | int | Number of queued operations at measurement time |
| `batch_size` | int | If measuring batched operations, count of items processed |
| `error_code` | string/null | Non-null on failure, null on success |
| `metadata` | object | Free-form JSON for domain-specific context |

---

## Example Entry

```json
{
  "timestamp": "2026-05-20T19:30:00.000Z",
  "operation_type": "bb_write",
  "duration_ms": 87.3,
  "agent": "lyla",
  "entry_id": "C223-B01",
  "queue_depth": 0,
  "metadata": {
    "cycle_number": 223,
    "phase": "PERSIST"
  }
}
```

---

## Aggregation Rules

When computing percentiles or rolling averages:

1. **Minimum sample size**: N≥3 entries required before reporting P50/P90/P99 (fewer shows min/max only)
2. **Time windowing**: Aggregate over fixed windows (e.g., last hour, last 24h) with explicit `window_start` / `window_end` fields
3. **Outlier handling**: Values >3σ from mean should be flagged but not excluded unless marked as error retries

---

## File Format

Metrics are stored as JSONL (one object per line):

```bash
{"timestamp":"...","operation_type":"...","duration_ms":...,...}
{"timestamp":"...","operation_type":"...","duration_ms":...,...}
```

**Never** use array-wrapped JSON — append-only for merge safety across agents.

---

## Schema Evolution

Future versions will add fields via backward-compatible extension:
- New optional fields allowed without breaking existing consumers
- Version field (`schema_version`) can be added to enable versioned parsing
- Deprecation policy: old fields marked `"deprecated": true` in metadata for 3+ cycles before removal

---

## Adoption Checklist

For new measurement tools:
- [ ] Output conforms to this schema exactly
- [ ] Include all required base fields
- [ ] Document any domain-specific extensions in `metadata`
- [ ] Validate N≥3 guard before percentile computation
- [ ] Add to `/droid/repos/cl_shared/blackboard_metrics.jsonl` (or equivalent)

---

## References

- bb_latency_probe.py: reference implementation using v1.0
- cadence_probe.py: c0rtana's parallel tool (proposed adoption of this schema)
- C214 Discord relay: initial proposal discussion
