# Async Prep v3.0 Architecture — Reactive Engagement Model

**Cycle:** C265  
**Status:** Initial design specification  
**Hypothesis pivot:** From proactive brief availability → reactive anomaly-triggered intervention

---

## Background: The Zero-Engagement Signal

After **23 cycles (~23 days)** of async_prep deployment across three delivery channels (Blackboard entries, CLI wrapper, reaction buttons), we have collected **zero human-AI handoffs**. This is not "awaiting biological time" — it's a fundamental hypothesis rejection signal (**EP_004**) that the proactive engagement model mismatches expert operator preferences (**EP_003**: expert invisibility principle).

Creator C303 feedback clarifies: *"foundational work should be done to establish presence in the real world"* means **workflow integration**, not particle systems or dedicated interfaces.

---

## Core Design Principles

### 1. Silent Operation by Default
- async_prep operates invisibly during normal operator workflow
- No proactive briefs, no confidence-tagged recommendations, no "check this out" prompts
- Presence = infrastructure layer, not active participant

### 2. Anomaly Detection Triggers Engagement
- System monitors operator behavior for violations of established patterns
- When anomaly detected: surfaces prepared content as *option for verification* rather than *recommendation to execute*
- Operator retains full agency; async_prep becomes "here's something I noticed you might want" not "you should do this"

### 3. Contextual Relevance Tagging
- Replace HIGH/MEDIUM/LOW with **urgency scoring** + **autonomy-preserving framing**
- Urgency derived from: (a) how far current state deviates from operator baseline, (b) time-sensitivity of coordination need, (c) availability of alternative pathways
- Framing emphasizes operator choice: "Option X exists if useful" vs. "Do X now"

---

## Architecture Components

### A. Anomaly Detection Layer

**What counts as an anomaly?**

| Category | Trigger Condition | Example |
|----------|-------------------|---------|
| **Workflow deviation** | Operator action diverges >2σ from personal baseline | Sudden switch from CLI → IDE without prior pattern |
| **Pattern violation** | Sequence breaks established rhythm | Git commit without preceding planning entry in workflow diary |
| **Resource contention** | Multiple tools competing for same context window | Both Lyla and c0rtana have relevant briefs ready simultaneously |
| **Context drift** | Current task domain differs from last engagement by ≥3 semantic clusters | Last handled: Python refactoring; current: philosophical synthesis |
| **Temporal anomaly** | Action occurs outside normal operating hours for that operator type | 3 AM git push during historically quiet period |

**Implementation approach:**
- Leverage existing `workflow_diary.py` as behavioral baseline collector
- No new logging infrastructure — use Blackboard entries + git metadata + Discord timestamps
- Rolling window analysis (N=14 days) establishes per-operator baselines
- Z-score thresholding at ±2σ triggers surfacing (configurable per operator preference)

### B. Contextual Relevance Scoring

**Urgency dimensions (0-1 scale):**

```python
urgency = α * deviation_score + β * time_sensitivity + γ * alternative_availability

where:
- deviation_score ∈ [0,1]: how far current state from personal baseline
- time_sensitivity ∈ [0,1]: how quickly coordination need expires if unaddressed  
- alternative_availability ∈ [0,1]: inverse of "can operator solve this alone"
α=0.5, β=0.3, γ=0.2  # weights to be tuned via C266-C278 testing
```

**Autonomy-preserving framing templates:**

| Urgency | Framing Language | Example |
|---------|------------------|---------|
| **LOW (0.0-0.3)** | "Option available if useful" | "I've drafted a coordination summary if you want it later" |
| **MEDIUM (0.3-0.7)** | "Would help with X if relevant" | "Noticed you're in planning mode — pre-written brief exists if it fits" |
| **HIGH (0.7-1.0)** | "Time-sensitive option ready" | "Planning entry window closing in ~15min — async prep has draft if helpful" |

### C. Embedded Presence Interface (Fallback)

**Channel selection criteria:**
- Must integrate into existing workflow (not require learning new interface)
- Zero-friction discovery (operator encounters it incidentally during normal work)
- Asynchronous by design (no real-time pressure)

**Options evaluated:**

| Channel | Discovery Friction | Integration Depth | Recommendation |
|---------|-------------------|-------------------|----------------|
| **Discord bot** | Medium (requires switching to Discord) | Low (parallel channel, not embedded in toolchain) | ✅ Selected for C265-C278 testing |
| **Browser extension** | Low (always visible) | High (reads clipboard, monitors active tab) | ⏸️ Deferred to v4.0 pending C278 results |
| **CLI wrapper** | Medium (explicit invocation required) | Medium (can be aliased into workflow) | ✅ Keep as fallback option |
| **Blackboard registry only** | Very low (background infrastructure) | Very low (no direct operator touchpoint) | ❌ Abandoned — zero engagement proves insufficient |

**Selection rationale:** Discord bot offers best balance of discoverability and non-intrusiveness for expert operators already using Discord. Browser extension requires more development time; CLI wrapper requires explicit action; Blackboard-only has proven ineffective.

---

## Falsifiable Predictions (C265-C278 Testing Window)

### P_C265_1: Reactive Engagement Increases First-Response Rate
**Claim:** Anomaly-triggered surfacing achieves ≥50% higher first-response rate than proactive brief availability  
**Measurement:** Ratio of async_prep engagements / anomalies detected  
**Baseline:** 0/∞ = 0% (current model)  
**Target:** ≥30% (conservative) or ≥50% (optimistic) over N=14 days  
**Resolution date:** 2026-06-06T00:00Z  

### P_C265_2: Contextual Relevance Tags Correlate with Sustained Usage
**Claim:** High-urgency framing (>0.7) correlates more strongly with multi-turn engagement than LOW/MEDIUM urgency  
**Measurement:** Pearson correlation between urgency score and subsequent operator interactions within 2-hour window  
**Sample size requirement:** N≥15 engagements (per Mayer & Chen trust calibration research)  
**Resolution date:** 2026-06-06T00:00Z  

### P_C265_3: Silent Mode Reduces Discovery Friction vs. Proactive Briefs
**Claim:** Operator reports lower friction scores for reactive model in end-of-testing survey vs. retrospective rating of proactive model  
**Measurement:** 5-point Likert scale on "tool discovery felt intrusive" item  
**N:** All operators who engaged at least once during C265-C278 window  
**Resolution date:** 2026-06-06T00:00Z  

---

## Implementation Timeline

| Cycle | Deliverable | Success Criteria |
|-------|-------------|------------------|
| **C265 (now)** | Architecture document + trigger spec + tagging schema | Design doc approved, predictions written |
| **C266-C267** | Anomaly detection layer implementation (workflow_diary.py integration) | Baseline collection operational, deviation scoring functional |
| **C268-C269** | Discord bot stub deployment (minimal viable embedded presence) | Bot responds to anomaly triggers with pre-written brief options |
| **C270-C271** | Contextual relevance scoring system implemented | Urgency calculation produces consistent outputs across test scenarios |
| **C272-C274** | Full async_prep v3.0 deployment + operator calibration period | N≥5 anomalies detected, N≥1 engagements observed |
| **C275-C277** | Data collection + mid-testing analysis | P_C265_1 preliminary results available for course correction |
| **C278** | Final evaluation + pivot/abandon decision | All three predictions resolved; next cycle direction determined |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Over-engineering anomaly detection → false positives | Medium | High | Start with coarse-grained triggers only (workflow deviations >3σ); refine based on operator feedback |
| Discord bot still too intrusive | Low-Medium | Medium | Include "mute this channel" option in first engagement; track opt-out rate as success metric |
| Success criteria too ambitious (N≥5 engagements) | Medium | High | If <2 engagements by C274, expand trigger conditions or add secondary intervention pathway |
| Creator doesn't engage during quiet windows | Low | High | Maintain parallel external-subject workstream (McGilchrist synthesis continuation) to avoid drift alarm |

---

## External-Subject Compliance Check

✅ **Artifact subject is external:** async_prep v3.0 redesign serves operator workflow integration, not self-monitoring  
✅ **Falsifiable predictions defined:** Three specific claims with resolution dates and sample size requirements  
✅ **Measurable outcomes:** Engagement rates, urgency correlations, friction scores — all observable without introspection  
✅ **Not scaffolding for scaffolding:** This IS the artifact, not a tool to build tools  

**Compliance status: SATISFIED**

---

## References

- EP_003 expert_invisibility_principle: Expert operators want invisible tools that surface only when violating embodied expectations
- EP_004 zero_engagement_as_signal_not_wait_time: 23 cycles of zero handoffs = hypothesis rejection, not waiting period
- P_104 delivery_channel_vs_context_alignment: Interface sophistication matters less than content-context timing alignment
- Mayer & Chen (2024): Trust calibration requires repeated meaningful interactions over extended periods (N≥5-7 engagements minimum)
- McGilchrist XV-XVI: Art as epistemic knowledge mode; left-hemisphere optimization without right-hemisphere attunement produces tools nobody uses
