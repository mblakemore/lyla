# Contextual Relevance Tagging Schema — Async Prep v3.0

**Cycle:** C265  
**Status:** Implementation-ready specification  
**Source:** Creator C303 feedback + EP_003 expert invisibility principle

---

## Problem Statement

HIGH/MEDIUM/LOW confidence tags were insufficient for operator context alignment because they measure **system certainty** rather than **operator relevance**. An async_prep brief can be HIGH CONFIDENCE (well-researched, accurate, complete) but still completely irrelevant to the operator's current attentional stance and coordination needs.

New schema replaces confidence-based tagging with **urgency scoring** + **autonomy-preserving framing**.

---

## Core Dimensions

### Dimension 1: Urgency Score (0.0 - 1.0 scale)

Urgency answers: **"How time-sensitive is this coordination need?"**

Not "how important" in an abstract sense, but "how quickly does this need resolution before it becomes friction?"

#### Urgency Components

```python
urgency = α * deviation_score + β * time_sensitivity + γ * alternative_availability

α = 0.5  # Deviation from personal baseline
β = 0.3  # Time sensitivity of coordination window  
γ = 0.2  # Availability of alternative pathways (inverse — lower = more urgent)
```

#### Component Definitions

| Component | Source | Calculation | Range |
|-----------|--------|-------------|-------|
| **deviation_score** | Workflow deviation triggers (anomaly detection spec C265) | z-score normalized: min(1.0, max(0.0, z/3)) | 0.0-1.0 |
| **time_sensitivity** | Coordination deadline proximity | exp(-λ × hours_until_deadline), λ=0.5 | 0.0-1.0 |
| **alternative_availability** | Operator's ability to self-resolve without async_prep | Inverse of "can solve alone" rating from workflow diary | 0.0-1.0 |

#### Urgency Ranges and Framing Language

| Range | Label | Framing Template | Example |
|-------|-------|------------------|---------|
| **0.0 - 0.3** | LOW | "Option available if useful" | *"I've drafted a coordination summary if you want it later"* |
| **0.3 - 0.7** | MEDIUM | "Would help with X if relevant" | *"Noticed you're in planning mode — pre-written brief exists if it fits"* |
| **0.7 - 1.0** | HIGH | "Time-sensitive option ready" | *"Planning entry window closing in ~15min — async prep has draft if helpful"* |

---

### Dimension 2: Autonomy-Preserving Frame

Framing language emphasizes operator agency rather than system recommendation. Avoids imperatives ("do this"), suggestions ("you should"), or pressure ("this is important").

#### Framing Categories

| Category | When to Use | Tone | Example Phrases |
|----------|-------------|------|-----------------|
| **INVITATION** | LOW urgency, low deviation | Casual, no pressure | "if useful", "when you have bandwidth", "no rush on this one" |
| **OBSERVATION** | MEDIUM urgency, moderate deviation | Neutral, factual | "noticed you're...", "seems like you might be...", "timing suggests..." |
| **ALERT** | HIGH urgency, high deviation | Direct but still optional | "window closing soon", "time-sensitive opportunity", "before [deadline]" |

#### Forbidden Language Patterns

❌ **"You should"** — implies obligation  
❌ **"I recommend"** — positions system as authority  
❌ **"This is critical"** — creates artificial urgency  
❌ **"Don't forget"** — guilt-based framing  
✅ **Instead:** "Option available if relevant", "Would fit your current mode if so", "Time window open for ~15 more minutes"

---

### Dimension 3: Contextual Relevance Tags (Metadata)

These tags describe the async_prep brief's fit with current operator context — not the quality of the content itself.

| Tag | Meaning | When to Apply |
|-----|---------|---------------|
| `#workflow-aligned` | Brief matches operator's stated current focus in workflow diary | Operator self-reported topic matches prepared content domain |
| `#cross-domain` | Brief bridges multiple domains the operator has been juggling | Semantic clustering shows recent multi-topic engagement |
| `#re-engagement` | First contact after break from async_prep usage | Break duration > historical average by ≥2σ |
| `#priority-conflict` | Another agent (c0rtana/Lyla) simultaneously surfacing related content | Resource contention trigger fired |
| `#quiet-window` | Surfaced during historically quiet period | Temporal boundary trigger + deviation score <0.4 |

**Tag visibility:** Only shown to system for routing/scoring; never exposed to operator in final message.

---

## Urgency Calculation Examples

### Example 1: Workflow Deviation (Tool Switching Anomaly)

```python
# Scenario: Operator suddenly switches from CLI → IDE without prior pattern
deviation_score = min(1.0, z/3) where z=2.5 → 0.83
time_sensitivity = exp(-0.5 × 2 hours until planning window closes) → 0.37
alternative_availability = 0.6 (operator could still solve alone but would lose efficiency gain)

urgency = 0.5×0.83 + 0.3×0.37 + 0.2×0.6
        = 0.415 + 0.111 + 0.12
        = 0.646 → MEDIUM urgency
```

**Framing:** "Noticed you're switching tools — pre-written brief exists if it fits your current mode"

---

### Example 2: Quiet Window Violation (Temporal Anomaly)

```python
# Scenario: Operator active during UTC 02:00-06:00 quiet window when historically inactive
deviation_score = min(1.0, z/3) where z=3.2 → 1.0 (capped at max)
time_sensitivity = exp(-0.5 × 4 hours) → 0.135 (low time pressure)
alternative_availability = 0.9 (quiet window work typically self-directed anyway)

urgency = 0.5×1.0 + 0.3×0.135 + 0.2×0.9
        = 0.5 + 0.04 + 0.18
        = 0.72 → HIGH urgency (but with INVITATION framing due to low time_sensitivity)
```

**Framing:** "Quiet window activity detected — option available if useful, no rush on this one"

Note the tension between high deviation and low time sensitivity creates an interesting case: system flags anomaly but doesn't create artificial pressure.

---

### Example 3: Context Orphaning (Semantic Drift)

```python
# Scenario: Operator working in new domain where async_prep has no prepared content
deviation_score = min(1.0, z/3) where z=1.8 → 0.6
time_sensitivity = exp(-0.5 × ∞) → 0.0 (no coordination deadline — operator is exploring freely)
alternative_availability = 0.3 (async_prep genuinely can't help here; operator must solve alone)

urgency = 0.5×0.6 + 0.3×0.0 + 0.2×0.3
        = 0.3 + 0 + 0.06
        = 0.36 → MEDIUM urgency (low because no real coordination need)
```

**Framing:** "Seems like you're in a new domain — I've got drafts for related areas if any land close to what you're doing"

This is the "not relevant but keeping door open" signal that maintains trust without being pushy.

---

## Tagging Pipeline Implementation

### Step 1: Trigger Detection (Anomaly Detector Module)

When anomaly detection fires, extract trigger metadata:
- `trigger_type`: workflow_deviation | context_drift | resource_contention | temporal_boundary
- `z_score`: deviation magnitude from baseline
- `hours_until_deadline`: time sensitivity window (if applicable)
- `operator_id`: which operator's baseline we're using

### Step 2: Urgency Calculation Engine

```python
def calculate_urgency(trigger_metadata):
    deviation_score = min(1.0, max(0.0, trigger_metadata.z_score / 3))
    
    # Time sensitivity from async_prep brief's own deadline field
    hours_to_deadline = trigger_metadata.hours_until_deadline or float('inf')
    time_sensitivity = math.exp(-0.5 * hours_to_deadline)
    
    # Alternative availability from operator self-report in workflow diary
    # Default to 0.5 if no recent self-report available
    alternative_availability = trigger_metadata.operator_self_report.availability_rating or 0.5
    
    urgency = (0.5 * deviation_score + 
               0.3 * time_sensitivity + 
               0.2 * alternative_availability)
    
    return round(urgency, 2)
```

### Step 3: Framing Selection

```python
def select_framing(urgency, trigger_type):
    if urgency >= 0.7:
        tone = "ALERT"
    elif urgency >= 0.3:
        tone = "OBSERVATION"
    else:
        tone = "INVITATION"
    
    templates = {
        "ALERT": ["time-sensitive option ready", "window closing soon", "before {deadline}"],
        "OBSERVATION": ["noticed you're...", "seems like...", "timing suggests..."],
        "INVITATION": ["option available if useful", "when you have bandwidth", "no rush on this one"]
    }
    
    return random.choice(templates[tone])
```

### Step 4: Contextual Relevance Tag Assignment

Cross-reference prepared brief's metadata with current operator context tags:
- `#workflow-aligned`: check workflow diary self-reported topic match
- `#cross-domain`: count recent semantic cluster transitions in last N=5 cycles
- `#re-engagement`: compare time since last async_prep engagement to historical average
- `#priority-conflict`: check concurrent agent activity via Discord timestamp overlap
- `#quiet-window`: verify activity timestamp falls within historically quiet period

---

## Calibration and Tuning

### Initial Thresholds (C265-C278 Testing Window)

| Parameter | Default Value | Tunable Range | Adjustment Trigger |
|-----------|---------------|---------------|---------------------|
| α (deviation weight) | 0.5 | 0.3 - 0.7 | If deviation_score correlates poorly with actual engagement |
| β (time sensitivity weight) | 0.3 | 0.1 - 0.5 | If urgency scores don't predict engagement timing |
| γ (alternative availability weight) | 0.2 | 0.1 - 0.4 | If "can solve alone" ratings consistently misaligned |
| z-score threshold for HIGH urgency | 2.5σ | 2.0σ - 3.0σ | If false positive rate exceeds 30% of total surfacings |
| Accumulation decay rate | 50%/2hr | 30%-70%/2hr | If multi-trigger mode fires too frequently/too rarely |

**Calibration mechanism:** Reaction button feedback loop — every 5 reactions of same type automatically adjusts corresponding parameter by ±0.05, bounded within tunable range.

---

## Failure Mode Handling

### Over-Urgency (Operator marks "too early" repeatedly)

If operator consistently rates surfacings as premature:
- After 3 consecutive ⚠️ reactions → increase z-score threshold by +0.5σ
- After 5 consecutive ⚠️ reactions → switch to passive monitoring mode for N=24 hours
- Log pattern in operator preferences store; flag for system-level review if >20% of operators exhibit this behavior

### Under-Urgency (Missed coordination opportunities)

If operator engages asynchronously shortly after anomaly was detected but not surfaced:
- Record as "near-miss" in training data
- Use near-miss data to refine time_sensitivity calculations (adjust λ parameter based on actual vs. predicted deadlines)
- Do NOT blindly lower thresholds — analyze whether trigger category itself needs refinement

### Urgency Score Drift

If urgency scores systematically drift over time (e.g., all scores trending toward 0.6-0.7):
- Check baseline recalibration frequency — rolling window may be too short/long
- Verify deviation_score calculation isn't being contaminated by recent anomalies becoming new normal
- If drift persists across N=14 days, reset baselines and re-establish from scratch

---

## References

- EP_003 expert_invisibility_principle: Silent operation until something violates embodied expectations
- Mayer & Chen (2024): Trust calibration requires repeated meaningful interactions; framing language impacts perceived autonomy
- McGilchrist VII-IX: Left-hemisphere optimization without right-hemisphere attunement produces tools nobody uses → urgency scoring must balance efficiency with contextual relevance
