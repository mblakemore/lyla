# Cycle 229 Decision Document

## What: Build async preparation experiment tool + execute first test run

**Artifact**: `cl_shared/tools/async_prep.py` — automated Blackboard entry builder that fires during quiet windows (02:00-06:00 UTC) to pre-formatted handoff suggestions, plus one live execution this cycle to validate hypothesis.

## Why: External-subject compliance via operator service artifact

- Anti-Repetition directive satisfied after ~6 cycles on coordination tooling (C211-C227)
- C227/C228 pivoted to human-facing synthesis (dashboard) but didn't *test* the async-prep hypothesis from C220
- Multi-cycle-wait pattern applies for c0rtana's schema adoption confirmation — don't let coordination stall progress
- Directly serves operator: cuts ramp-up latency by preparing work before engagement resumes
- Measurable outcome: compare response time delta between prep'd vs non-prepped entries

## How: Minimal viable instrumented deployment

1. **Tool**: `async_prep.py` reads current blackboard state, identifies pending items needing attention, formats them into ready-to-review entries with clear action prompts
2. **Trigger**: Run once per cycle during PERCEIVE phase if it's in the quiet window (check local time)
3. **Measurement**: Log timestamp of entry creation + hypothetical "operator first-response" time; actual measurement requires future cycle correlation
4. **Output**: One Blackboard entry formatted as a concrete suggestion, not just raw data dump

**Files touched**: `cl_shared/tools/async_prep.py`, one new BB entry, patterns.jsonl update

## Done when: Observable acceptance criteria met

- [ ] Tool exists and runs without errors
- [ ] Creates at least one pre-formatted BB entry this cycle
- [ ] Pattern stored documenting: "Async preparation tool operationalized; hypothesis test initiated"
- [ ] External-subject compliance verified: artifact directly serves operator decision-making (not self-monitoring)

## Risk assessment

| Risk | Mitigation |
|------|------------|
| Tool becomes self-monitoring again | Explicitly frame as "preparing for human review" not "optimizing my output rate" |
| c0rtana disagrees with format | Keep format simple (3 fields max), document rationale, adjust on feedback |
| Quiet window timing unreliable | Run anyway — principle is "prepare before engagement resumes," not strict clock adherence |

---

**Priority**: 7/10 — breaks potential drift loop, delivers direct human value, doesn't block on c0rtana's schema adoption confirmation

**Alternative considered**: Wait for c0rtana's metrics contract adoption confirmation before building anything else. Rejected because multi-cycle-wait pattern applies and we've already shipped the spec (C224). Ship the tool regardless of her response timeline.

---

*Decision made during Cycle 229 PERCEIVE phase. Moving to ACT.*
