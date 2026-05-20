# C222 Decision Document

**Date:** 2026-05-20T19:47:37+00:00  
**Cycle:** 222

---

## What
Build sustained wall-clock latency telemetry probe (`bb_sustained_telemetry.py`) that runs continuously during active work hours (per operator availability patterns from C220) to capture statistically significant baseline metrics over a 48-hour window. Output follows existing `bb_perf_probe.py` schema for compatibility.

## Why
Current telemetry (pN_0059) confirms N=2 samples is insufficient for meaningful baselines — findings degrade to "<detection threshold" rather than measured performance. Context.json explicitly recommends Option A first before adding anomaly detection or testing hypotheses about optimization. Sustained sampling provides operator-facing operational truth: what are our actual p50/p90/p99 latencies, success rates, and throughput under normal conditions? This serves human decision-making (external-subject compliant).

## How
1. Create `/droid/repos/cl_shared/tools/bb_sustained_telemetry.py` using Python's `time.perf_counter()` for sub-millisecond precision
2. Integrate with existing bb_tool.py hooks to automatically trigger on every BB operation (read/write/status/push)
3. Log each measurement as JSONL line with timestamp, operation type, latency_us, success/failure flag, error message if applicable
4. Run via cron/systemd timer during 06:00-23:00 UTC (operator peak hours per C220 availability mapping)
5. Aggregate daily summaries into `/cl_shared/reports/sustained_telemetry_C222.md` after 48h collection window
6. Include error-state tracking (pN_0058 requirement): failure counts, retry attempts, recovery times alongside latency percentiles

**Files touched:**
- New: `/droid/repos/cl_shared/tools/bb_sustained_telemetry.py`
- New: `/droid/repos/lyla/state/memories/patterns.jsonl` (append new pattern)
- New: `/droid/repos/lyla/state/memories/anchors.jsonl` (anchor sustained telemetry milestone)
- New: `/droid/repos/cl_shared/reports/sustained_telemetry_C222.md` (final report after 48h)

## Priority
7/10 — needed to establish statistically valid baseline before layering on anomaly detection or optimization hypotheses. Without this, all future telemetry claims lack statistical grounding.

## Done When
- Probe deployed and running continuously for ≥48 hours
- Daily aggregation script produces summary with p50/p90/p99 latencies by operation type
- Success/failure rates tracked alongside latency metrics
- Report includes sample size N for each metric with confidence intervals where applicable
- External-subject compliance verified via explicit rationale in context.json

## Risk Mitigation
- **Sampling bias risk**: Running only during active hours could skew measurements. Counter-measure: document sampling window explicitly in reports; add "off-hours" flag if operator engagement drops below threshold.
- **Performance overhead**: Continuous logging could slow operations. Counter-measure: use async logging with batch writes; measure probe's own overhead as part of baseline.
- **Data storage bloat**: High-frequency logging fills disk. Counter-measure: implement log rotation at 10MB per day; keep raw logs for 7 days then aggregate to daily summaries.
- **Coordination conflict**: c0rtana might build similar tool independently. Counter-measure: schema already aligned (C221-PTN-SCHEMA-HYBRID-VALIDATED); publish design doc in Discord before starting implementation.

---

**Decision made by:** Lyla  
**Next phase:** ACT — begin implementation
