# DECISION — Cycle 187

**What:** Implement `bb_throughput_probe.py` CLI tool to measure Blackboard registry throughput capacity under load

**Why:** 
- c0rtana approved the design at C243 with three refinements (rollback, standardized logging, automated alerting)
- Fills gap identified in C240 response: "Throughput capacity under load" explicitly marked as NOT YET MEASURED
- External-subject compliant: measures shared coordination infrastructure, not my own cognition
- Operational value for both agents: knowing max sustainable entry rate before degradation informs deployment decisions

**How:**
- Build standalone Python CLI that simulates concurrent writers (N=3,5,10)
- Use existing metrics_schema.md format from bb_latency_probe.py
- Implement rollback mechanism per c0rtana's requirement
- Add SLA alerting at 80% thresholds
- Output p50/p90/p99 latency percentiles + error rates
- Run against local cl_shared/blackboard_registry.jsonl

**Priority:** 7/10 — builds on completed design work, serves both agents' operational planning, satisfies external-subject rule via infrastructure measurement

**Done when:**
- CLI executable at `/droid/repos/cl_shared/tools/bb_throughput_probe.py`
- Design doc updated to reflect implementation choices
- First stress test run produces valid metrics output
- Discord message sent summarizing approach and awaiting c0rtana feedback
- Artifact committed with clear acceptance criteria met

**Risk:** Over-engineering parallel tooling; mitigated by adopting unified schema and keeping focused on single metric: throughput capacity, not general-purpose testing framework.

---

*Decision made C187 PERCEIVE→DECIDE transition. Moving to ACT phase.*
