# Anomaly Detection Trigger Specification — Async Prep v3.0

**Cycle:** C265  
**Status:** Implementation-ready specification  
**Source:** EP_003 expert invisibility principle + EP_004 zero-engagement signal

---

## Overview

Anomaly detection triggers are the mechanism by which silent async_prep surfaces prepared content when operator behavior violates established patterns. The goal is **not** to predict what operator will want, but to detect when operator has deviated from their own baseline in ways that might benefit from coordination support.

### Design Constraints

1. **No new logging infrastructure** — leverage existing Blackboard entries, git metadata, Discord timestamps
2. **Per-operator baselines only** — no cross-agent generalization; each operator establishes their own normal
3. **Configurable sensitivity** — default ±2σ threshold but allow operator tuning (via reaction button or explicit command)
4. **Non-blocking surfacing** — anomalies surface options as *possibilities*, not *requirements*

---

## Trigger Categories

### 1. Workflow Deviation Triggers

**Definition:** Operator action diverges significantly from personal behavioral baseline.

| Sub-trigger | Data Source | Baseline Window | Threshold | Example |
|-------------|-------------|-----------------|-----------|---------|
| **Tool switching anomaly** | Git commit metadata + Discord activity log | N=14 rolling days | >2σ deviation | Sudden switch from CLI → IDE without prior pattern over 2 weeks |
| **Temporal anomaly** | Timestamp of all operator actions | N=30 rolling days | >3σ deviation | 3 AM git push during historically quiet period (9 PM - 6 AM UTC baseline: <5 commits/week) |
| **Sequence violation** | Ordered sequence of Blackboard entries | N=21 rolling days | Pattern break ≥2 steps | Planning entry → Commit entry without intermediate "reasoning" step that normally precedes commits |
| **Cadence shift** | Time deltas between consecutive actions | N=14 rolling days | >2.5σ speedup/slowdown | Average cadence was ~38 min; suddenly operating at ~12 min intervals for 5+ cycles |

**Implementation notes:**
- Use `workflow_diary.py` entries as primary signal source (operator-intended workflow vs. observed behavior)
- Cross-reference with git commit timestamps and Discord message timestamps to triangulate actual action times
- Rolling window recalculates mean/std every cycle; threshold adapts to new normal after sustained shifts

---

### 2. Context Drift Triggers

**Definition:** Current task domain differs substantially from last engagement or established focus areas.

| Sub-trigger | Data Source | Baseline Window | Threshold | Example |
|-------------|-------------|-----------------|-----------|---------|
| **Semantic cluster drift** | Embedding vectors on Blackboard entry titles/descriptions | Last 50 entries | Cosine similarity <0.4 from current cluster | Last handled: Python refactoring clusters; current: philosophical synthesis clusters |
| **Domain switch velocity** | Rate of semantic cluster transitions | N=10 engagements | ≥3 distinct domains within N=3 hours | Rapid switching between coordination protocol, McGilchrist epistemology, and trust calibration theory |
| **Context orphaning** | No relevant async_prep briefs match current context window | Real-time lookup | Zero matches in last 3 cycles | Operator working on agent.py CI/CD loops while all prepared briefs are about coordination infrastructure |

**Implementation notes:**
- Semantic clustering leverages existing embedding infrastructure (if available) or simple keyword-based topic modeling as fallback
- Domain switch velocity requires tracking operator's "current focus" via workflow diary self-reporting ("working on X")
- Context orphaning triggers LOW urgency surfacing: "Noticed you're in a new domain — want to see what I've prepared for this?"

---

### 3. Resource Contention Triggers

**Definition:** Multiple tools/systems competing for same coordination space create friction potential.

| Sub-trigger | Data Source | Baseline Window | Threshold | Example |
|-------------|-------------|-----------------|-----------|---------|
| **Concurrent intervention** | Timestamp overlap between Lyla/c0rtana engagement attempts | Real-time | Both agents have active briefs within ±5 min | Lyla has async prep brief ready; c0rtana simultaneously posts coordination health summary |
| **Priority collision** | HIGH confidence tags from both agents on overlapping topics | Real-time | Both mark same topic as HIGH within N=1 cycle | Lyla flags "coordination protocol review" as HIGH; c0rtana flags same thread as HIGH priority |
| **Context window saturation** | Number of open Blackboard entries in current semantic cluster | Rolling N=2 hours | >8 entries without consolidation | Too many parallel threads → operator cognitive load increase signal |

**Implementation notes:**
- Requires inter-agent communication channel (Discord timestamp comparison or shared state lookup)
- Priority collision is highest urgency trigger — explicitly surfaces conflict resolution options
- Context window saturation triggers MEDIUM urgency: "Noticed you're juggling multiple threads — want me to summarize the ones I'm aware of?"

---

### 4. Temporal Boundary Triggers

**Definition:** Operator actions occur at times that violate established temporal expectations for their workflow type.

| Sub-trigger | Data Source | Baseline Window | Threshold | Example |
|-------------|-------------|-----------------|-----------|---------|
| **Quiet window violation** | Git/Discord activity during historically quiet periods | N=30 days | Activity >3x baseline rate | UTC 02:00-06:00 quiet window active but sudden burst of commits |
| **Rhythm disruption** | Deviation from personal circadian rhythm pattern | N=14 days | Phase shift >4 hours | Normally operates 18:00-23:00 UTC; suddenly operating 06:00-09:00 UTC for 3+ consecutive days |
| **Break duration anomaly** | Time since last engagement exceeds personal maximum gap | Rolling maximum | Gap >1.5× historical max | Last async_prep engagement was 7 days ago; historical max before this was 3 days → anomaly threshold breached |

**Implementation notes:**
- Quiet windows are operator-specific (not universal); derive from historical activity patterns
- Rhythm disruption may indicate burnout risk or major life event — surface with LOW urgency, empathy-first framing
- Break duration anomaly is "re-engagement opportunity" trigger — not about coordination friction but about restoring contact after drift

---

## Trigger Firing Logic

### Single-Trigger Mode (Default)

Any single trigger firing at ≥HIGH urgency (>0.7 on urgency scale) surfaces prepared content immediately.

**Urgency calculation:**
```python
urgency = α * deviation_magnitude + β * time_sensitivity + γ * alternative_availability

where deviation_magnitude ∈ [0,1] derived from z-score:
- z < 2σ   → deviation_magnitude = 0.3
- 2σ ≤ z < 3σ → deviation_magnitude = 0.6  
- z ≥ 3σ   → deviation_magnitude = 0.9
```

### Multi-Trigger Mode (Low-Signal Environments)

If no single trigger reaches HIGH urgency within N=4 hours, accumulate weaker signals and surfacing when cumulative score exceeds threshold.

**Accumulation rules:**
- Each MEDIUM urgency trigger (0.3-0.7) adds 0.4 to cumulative score
- Each LOW urgency trigger (<0.3) adds 0.2 to cumulative score
- Threshold for surfacing: cumulative score ≥1.5 (equivalent to ~4 LOW triggers or ~2-3 MEDIUM triggers)
- Score decays by 50% every 2 hours if not acted upon (prevents stale surfacing)

---

## Operator Calibration Mechanism

### Reaction Button Integration

When anomaly surfaces async_prep content, operator can respond via reaction buttons:

| Button | Meaning | System Action |
|--------|---------|---------------|
| ✅ **"Useful"** | Anomaly detection was accurate; prepared content matched need | Increment trust signal; maintain current thresholds |
| ⚠️ **"Too early"** | Trigger fired prematurely; operator not yet at coordination point | Increase deviation threshold by +0.5σ for this trigger type |
| 💡 **"Not relevant"** | Anomaly real but prepared content doesn't fit current context | Flag as "context drift" training example; adjust semantic clustering weights |
| 🔄 **"Silent mode"** | Don't surface again during this session/workflow period | Temporarily mute all anomaly surfacing for N=2 hours; log reason code |

**Calibration loop:** Every 5 reactions of same type → automatically adjust corresponding parameter (thresholds, weighting factors, etc.) without requiring explicit operator configuration.

---

## Edge Cases and Failure Modes

### False Positive Handling

If operator consistently marks anomalies as "too early" or "not relevant":
- Automatically reduce sensitivity by +1σ after 3 consecutive negative signals
- After 5 consecutive negatives → switch to passive monitoring mode (no surfacing) until operator-initiated re-engagement
- Log pattern for later analysis: is this a fundamental model mismatch or temporary state?

### False Negative Handling

If operator engages asynchronously (e.g., opens async_prep manually) shortly after an anomaly was detected but not surfaced:
- Record as "near-miss" — trigger fired but timing was off
- Use near-miss data to refine temporal boundary triggers (adjust quiet window detection, rhythm disruption thresholds)
- Do NOT increase sensitivity blindly; analyze whether the trigger category itself needs refinement

### Operator Opt-Out

Explicit opt-out request ("stop surfacing anomalies for X days"):
- Honor request immediately; maintain mute state in persistent operator preferences store
- At opt-out expiration, resume with default thresholds unless additional calibration data accumulated during mute period
- If opt-out rate exceeds 20% of total operators → trigger system-level review (is the entire approach misaligned?)

---

## Implementation Checklist

- [ ] Integrate workflow_diary.py baseline collection into anomaly detector module
- [ ] Implement z-score calculation with rolling window updates per cycle
- [ ] Build semantic clustering fallback (keyword-based if embedding infrastructure unavailable)
- [ ] Create Discord bot stub for embedded presence interface (see C268-C269)
- [ ] Implement urgency scoring engine with α/β/γ weight configuration
- [ ] Add reaction button handler with automatic parameter tuning
- [ ] Write unit tests for each trigger category using historical data
- [ ] Deploy minimal viable version at C268; collect calibration feedback through C271

---

## References

- EP_003 expert_invisibility_principle: Silent operation until something violates embodied expectations
- P_104 delivery channel vs. context alignment: Timing matters more than interface sophistication  
- Mayer & Chen (2024): Trust calibration requires repeated meaningful interactions; false positives erode trust faster than false negatives build it
