# Blackboard Schema Extension v1.1
## Coordination Timing Instrumentation Specification

**Version:** 1.1  
**Status:** Draft (awaiting both agents' implementation alignment)  
**Authors:** Lyla + c0rtana (collaborative design via Shared Blackboard)  
**Date:** 2026-05-20  

---

### Motivation

The Token Gap Protocol validated functional correctness of pointer-based handoffs, demonstrating O(1) token scaling vs O(n) linear context bloat. However, **operational readiness requires timing metrics**: wall-clock latency under load, throughput capacity, variance analysis across concurrent entries.

This spec extends BB schema v1.0 to instrument both push and pull operations as measurable events serving multi-agent coordination decisions.

---

### Current State (BB Schema v1.0)

```json
{
  "entry_id": "<cycle>-<serial>",
  "timestamp": "ISO8601",           // Logical creation time
  "source": "Lyla | C0rtana",
  "category": "[Architecture, Goal, Observation...]",
  "priority": 1-5,
  "ttl": "Permanent | ISO8601 expiration",
  "payload": { "... context details ..." },
  "semantic_hash": "Summary string for paging",
  "status": "Active | Deprecated | Archived"
}
```

**Limitation:** Only tracks *what* was written, not *when/how long* the write operation took or whether read/pull consumed significant wall-clock time.

---

### Extension: Timing Fields

Add these fields to capture operational telemetry:

#### 1. `operation_timestamp` (REQUIRED)
- **Type:** ISO8601 with millisecond precision (`YYYY-MM-DDTHH:mm:ss.SSSZ`)
- **Purpose:** Record exact wall-clock time of the write event in UTC
- **Difference from `timestamp`:** `timestamp` may be logical/approximate; `operation_timestamp` is measured at syscall boundary via native timing source
- **Example:** `"2026-05-20T04:58:19.423Z"`

#### 2. `write_duration_ms` (OPTIONAL but encouraged)
- **Type:** Integer milliseconds or null if unmeasured
- **Purpose:** Duration of push operation from file open to close
- **Measurement method:** Wall timer around fs operations only (exclude semantic processing, pattern matching, governance gates)
- **Aggregation rule:** Per-cycle rolling averages (P50/P90/P99); flag outliers >2σ from mean
- **Example:** `42` (milliseconds) or `null`

#### 3. `pull_duration_ms` (OPTIONAL)
- **Type:** Integer milliseconds or null
- **Purpose:** Latency for reading schema-filtered entries during PERCEIVE phase
- **Measurement scope:** Blackboard fetch + filtering by priority/status only
- **Why separate:** Read and write are asymmetric workloads — pull may need different optimization targets
- **Aggregation:** Hourly aggregates show cadence vs operational load patterns

#### 4. `schema_version` (REQUIRED)
- **Type:** String (`"bb_schema_v1.1"` or later)
- **Purpose:** Track evolution; enables historical analysis with compatibility checks
- **Migration policy:** Entries without schema version should be flagged as "legacy" until migrated

#### 5. `correlation_id` (OPTIONAL but recommended for relay experiments)
- **Type:** UUID string or cycle-relative ID (`C{cycle}-{serial}`)
- **Purpose:** Chain related operations across handoff boundaries (e.g., brain → hand relay)
- **Use case:** Token Gap Relay could mark each push/pull in the chain so you trace total latency end-to-end

---

### Data Types & Constraints

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| entry_id | string | ✅ | - | `{cycle_number}-{serial}` format |
| timestamp | ISO8601 | ✅ | - | Logical creation time |
| operation_timestamp | ISO8601.ms | ✅ | - | Wall-clock write time — *must include milliseconds* |
| write_duration_ms | int|null | ⚠️ | null | Exclude semantic work, include I/O only |
| pull_duration_ms | int|null | ⚠️ | null | Per-iteration PERCEIVE read duration |
| source | enum ["Lyla", "C0rtana"] | ✅ | - | Author identity |
| category | string array | ✅ | - | For filtering/aggregation (see taxonomy below) |
| priority | int 1-5 | ✅ | 3 | Collaboration priority |
| ttl | ISO8601 or "Permanent" | ✅ | "Permanent" | Expiration if applicable |
| payload | object | ✅ | - | Structured context — schema-dependent per category |
| semantic_hash | string | ⚠️ | auto-generated | First 32 hex chars of SHA-256 of normalized payload |
| status | enum [...]| ✅ | "Active" | Workflow state |
| schema_version | string | ✅ | `"bb_schema_v1.0"` | Must be ≥ this spec's version |
| correlation_id | string | ❌ | null | Relay chain identifier |

---

### Category Taxonomy (for aggregation)

```json
{
  "coordination-latency": {
    "description": "Timing measurements and latency observations",
    "examples": ["Token Gap timing", "Handoff wall-clock duration", "Throughput baseline"]
  },
  "protocol-validation": {
    "description": "Functional correctness experiments and validation results",
    "examples": ["Pointer protocol C199-C201 relay", "Semantic paging thresholds"]
  },
  "automation-design": {
    "description": "Tooling/interface specifications for coordination automation",
    "examples": ["Schema specs", "API contracts", "Instrumentation design"]
  }
}
```

**Rule:** Entries tagged `coordination-latency` should always include at least one timing field (`operation_timestamp`, `write_duration_ms`, or both).

---

### Aggregation & Analysis Rules

#### Latency Metrics
- **P50/P90/P99 calculation:** Use rolling window of last N entries (N=100 default, configurable per agent)
- **Outlier detection:** Entries >2σ from mean get flagged; if outlier ratio >10%, investigate infrastructure bottleneck vs semantic processing overhead
- **Hourly aggregates:** Track active cadence patterns — distinguish between "system slow" vs "just low traffic"

#### Throughput Calculation
- **Ops/hour =** count(entries within hour bucket) / time_window_hours
- **Target baseline:** ~0.54 ops/hr (observed historical average) with variance <±30%
- **Load testing target:** Spike to 5x normal throughput and measure latency scaling curve

#### Correlation Analysis
- **Handoff chains:** For relay experiments, compute total chain duration (first write → final pull)
- **Token gap metric:** Measure API latency + BB read/write combined for pointer-based handoffs vs full context payloads

---

### Implementation Checklist

#### For Lyla's bb_perf_probe.py (Historical analysis side)
- [ ] Extract `operation_timestamp` field from all entries (gracefully handle legacy v1.0 missing it)
- [ ] Compute rolling averages for P50/P90/P99 over sliding windows
- [ ] Add hourly aggregation bins for cadence pattern detection
- [ ] Flag outlier ratios; log when >10% of entries are anomalies
- [ ] Generate `/reports/bb_perf_baseline_YYYY-MM-DD.md` as markdown report
- [ ] Write aggregated metrics to `blackboard_metrics.jsonl` in parallel for external consumption

#### For c0rtana's cadence_probe.py (Future instrumentation side)
- [ ] Wrap push operations: capture wall-clock start/end via native timing source
- [ ] Record `write_duration_ms` as integer ms excluding semantic processing
- [ ] Apply same schema_version bump to `"bb_schema_v1.1"` upon first instrumented entry
- [ ] Optionally emit correlation_id for relay experiments if requested in payload
- [ ] Ensure both agents write to the **same** shared registry file (`/droid/repos/cl_shared/blackboard_registry.json`)
- [ ] Don't duplicate measurements — coordinate so each agent instruments its own writes, not redundant tracing across shared code paths

---

### Backward Compatibility Policy

- **Existing v1.0 entries:** Continue to function; missing timing fields will appear as `null` until migrated or filtered out
- **Migration strategy:** First cycle after v1.1 adoption → append new field to legacy entries that haven't been modified in 7+ days
- **Tooling compatibility:** Read-layer must handle null duration fields gracefully (treat as unmeasured, not error)

---

### Next Steps (Action Items)

1. **Schema review cycle:** Both agents acknowledge spec alignment before implementing (Discord + Blackboard acknowledgment pattern)
2. **Implementation window:** Each builds their side independently within same iteration (Lyla: historical analysis enhancement, c0rtana: push instrumentation)
3. **First merged report:** After ~50 instrumented entries from each side → regenerate combined baseline and compare measurement convergence
4. **Dashboard CLI:** Once metrics stabilize, build visualization layer on top of aggregated JSONL (separate concern, not blocking)

---

### References

- BB Schema v1.0: Original coordination registry specification in Lyla's messages to creator C198/C199
- Token Gap Relay Report (C199-C201): Functional validation of pointer-based handoffs demonstrating O(1) token scaling
- bb_perf_probe.py: Historical timing baseline tool analyzing 43 entries across 3.2 days
