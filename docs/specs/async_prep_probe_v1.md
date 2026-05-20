# Async Preparation Probe v1.0

## Hypothesis

Pre-formatted Blackboard entries during low-activity windows (02:00-06:00 UTC) reduce operator ramp-up latency by 5-10 minutes compared to reactive coordination.

## Rationale

C220-PATTERN-ASYNC-PREPARATION identified this as an untested hypothesis. If true, it represents a measurable optimization to handoff quality without increasing cognitive load on Lyla during active periods.

## Experiment Design

### Test Setup

**Control Condition**: Standard reactive coordination — no pre-formatted entries during quiet window.

**Treatment Condition**: Pre-formatted BB entry with:
- Current state summary (3 bullet points max)
- One clear next-step recommendation
- External-subject artifact link (e.g., telemetry dashboard URL)

### Measurement

**Primary Metric**: Time from operator first engagement after quiet period to "first meaningful output" timestamp in logs/consciousness.log

**Secondary Metrics**:
- Number of clarification questions needed in first cycle
- Context-switching cost (measured via PERCEIVE phase duration vs baseline)

### Duration

Minimum 5 cycles per condition to establish statistical significance. Alternate conditions across days to control for day-of-week effects.

### Success Criteria

Treatment condition shows median reduction ≥5 minutes in ramp-up time, with p<0.05 via Wilcoxon signed-rank test.

## Implementation Notes

- Use `logs/sustained-telemetry.log` for timing data collection
- Cross-reference with `state/memories/context.json` to identify low-activity windows automatically
- Operator should log engagement start time in `messages/from-creator.md` when resuming after extended break

## Risks

- Over-preparation could create stale context that confuses rather than helps
- False precision — the 5-10 minute estimate may not hold across different types of breaks (lunch vs overnight vs weekend)

---

*Spec version: 1.0 | Created: Cycle 223 | Status: Awaiting operator approval to run experiment*
