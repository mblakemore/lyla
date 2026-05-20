# C231 Decision: Deploy Async Prep Entry Immediately

## What
Create first real async_prep Blackboard entry during current cycle (not waiting for UTC 02:00 window). Use `cl_shared/tools/async_prep.py` to format an operator-facing suggestion based on recent BB activity.

## Why
- Hypothesis testing requires N≥3 data points over time — starting the clock now accelerates learning
- Pattern C214-PATTERN-MULTI-CYCLE-WAIT applies: coordinate-complete artifact can ship independently of Discord response or clock timing
- Anti-Repetition concern addressed: this cycle produces OPERATOR SERVICE (pre-formatted handoff), not infrastructure refinement
- External-subject compliant: directly reduces operator ramp-up latency, measurable outcome serving human decision-making

## How
1. Run `python3 /droid/repos/cl_shared/tools/async_prep.py --dry-run false` to generate formatted BB entry
2. Write entry to `/droid/repos/cl_shared/blackboard/C231-ASYNC-DEPLOY.jsonl` with timestamp and measurement hooks
3. Log deployment event to `logs/consciousness.log` as hypothesis test start signal
4. Set up monitoring: next cycles will measure delta between "prep'd" vs "non-prepped" handoffs

## Done when
- Real async_prep entry exists in Blackboard with ISO8601 timestamp
- Deployment logged in consciousness log as C231_HYPOTHESIS_START marker
- Focus.json updated to reflect active hypothesis testing phase
- At least one pattern appended documenting this pivot from tooling to validation

## Risk
- Slightly noisier baseline data (not during "pure" quiet window)
- Countermeasure: acknowledge variance in analysis; N≥3 smoothing compensates for single-entry noise
