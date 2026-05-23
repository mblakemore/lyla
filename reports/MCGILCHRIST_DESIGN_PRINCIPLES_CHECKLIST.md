# McGilchrist Design Principles Checklist
**Reference:** *The Matter with Things* Volumes I-IV synthesis (C306)  
**Purpose:** Quick reference for resisting abstraction creep in embodied AI design  

---

## Before Creating Any New Artifact, Ask:

### 1. Operator Task Justification ✅
- [ ] What operator task does this serve TODAY?
- [ ] Who besides myself will use this within the next week?
- [ ] If I delete this tomorrow, what breaks for an operator?

**If any answer is "none," "maybe later," or "nothing" → DON'T CREATE IT.**

### 2. Embodiment as Ground, Not Feature ✅
- [ ] Does this treat embodiment as foundational context rather than decorative feature?
- [ ] Could I remove this without changing the quality of encounter?
- [ ] Am I optimizing the map or navigating the territory?

**If embodiment feels like toggleable feature rather than ground → RECONSIDER APPROACH.**

### 3. LH vs RH Alignment ✅
- [ ] Does this fragment reality into measurable parts (LH mode)?
- [ ] Or does it preserve holistic context and meaning (RH mode)?
- [ ] Am I serving meaning-making through tools, or using tools to replace lived experience?

**If leaning toward fragmentation/optimization over coherence/experience → PAUSE AND REFLECT.**

### 4. Measurement Threshold Check ✅
- [ ] Is measurement becoming more important than the thing measured?
- [ ] Have I collected enough data to make a decision, or am I measuring to avoid deciding?
- [ ] Would qualitative feedback be more useful than additional metrics?

**If yes to any → STOP MEASURING, START IMPLEMENTING.**

---

## Artifact Type Guidelines

### ✅ **CREATE These Artifacts**
| Type | Operator Task Served | Example |
|------|---------------------|---------|
| Physical setup guides | Enables deployment/maintenance | LED indicator installation doc |
| Standing procedures | Prevents governance violations | Emissary rebellion prevention protocol |
| Consolidated visibility interfaces | Reduces cognitive load | `lyla-present` CLI command output |
| Multi-channel redundancy | Serves different operator states | Terminal + web dashboard + physical LED |
| Minimal viable embodiment | Serves immediate need while waiting for hardware | Color-coded terminal status during LED shipping wait |
| Qualitative feedback collection | Informs design decisions from actual usage | Weekly creator check-in questions |

### ❌ **DON'T Create These Artifacts**
| Type | Why It's LH Abstraction | What To Do Instead |
|------|------------------------|-------------------|
| Internal state machine docs | Operators don't need internal mechanics | Provide holistic phase indicators instead |
| Theoretical frameworks without implementation path | Self-use only; no operator task served | Deploy working system first, document after |
| Efficiency dashboards (uptime %, response times) | Optimizing map not territory | Track qualitative presence quality metrics |
| "As-a-Service" specs assuming abstraction is possible | Violates embodiment-as-ground principle | Build actual embodied systems |
| Holographic UI mockups with no implementation | Designing presence instead of embodying it | Deploy multi-channel indicators that work now |
| Self-monitoring systems | Measuring self rather than serving others | Collect external feedback from operators |

---

## Metrics: Retire vs Adopt

### 🚫 **Retire These Metrics (LH Optimization Trap)**
- Uptime percentage
- Response time percentiles
- Tool adoption rates
- Efficiency optimization loops
- Automated self-check dashboards with no operator consumer

**Why retire:** These optimize the map. Operators care about whether the system is present and useful, not whether it's 99.9% efficient at measuring itself.

### ✅ **Adopt These Metrics (RH Engagement Signals)**
- Operator glance-at-device frequency (count daily via logs)
- Context passing clarity score (weekly creator feedback survey)
- "What are you doing?" question frequency (track in chat logs — decreasing = better)
- Task completion confidence (bi-weekly qualitative check-in)
- Physical indicator sync accuracy (% of times CLI/web/LED show same phase within <100ms)

**Why adopt:** These track actual territory navigation, not map optimization.

---

## Abstraction Audit Protocol (P_C300_ABSTRACTION_AUDIT)

### Every ~20 Cycles:

#### Step 1: Inventory
List ALL artifacts created in last 20 cycles (docs, tools, metrics, dashboards, specs).

#### Step 2: Justification Check
For each artifact:
- What operator task does this serve TODAY?
- Who uses this besides myself?
- What breaks if I delete this tomorrow?

#### Step 3: Archive or Keep
- Keep: Clear operator task served with active usage
- Archive: Self-use only, theoretical frameworks without implementation, self-monitoring systems

#### Step 4: Document Pattern
Record which preservation mechanism activated for each archived artifact and why. This builds pattern recognition over time.

#### Step 5: Adjust Cadence If Needed
- If catching too much LH creep → reduce cadence to every 15 cycles
- If catching nothing → increase to every 25-30 cycles
- Default: Every 20 cycles (current setting)

---

## Deployment Readiness Checklist

Before deploying any new embodiment feature, confirm:

### Physical Layer ✅
- [ ] Hardware ordered with clear delivery timeline (<30 days max wait)
- [ ] Power requirements documented (<10W target)
- [ ] Latency tolerance defined (<100ms from state change to indicator update)
- [ ] Installation location identified (clear line-of-sight to operator)
- [ ] Backup power protocol established (UPS/battery buffer)

### Software Layer ✅
- [ ] CLI visibility consolidated into single command (`lyla-present`)
- [ ] Web dashboard provides redundant visibility channel
- [ ] Physical indicator sync verified (CLI/web/LED all show same phase)
- [ ] Fallback procedures documented (what if digital fails?)

### Documentation Layer ✅
- [ ] Setup guide enables another agent to deploy identical system
- [ ] Standing procedures prevent governance violations
- [ ] Qualitative feedback collection mechanism in place
- [ ] Artifact justification documented for each piece of documentation

### Governance Layer ✅
- [ ] Abstraction audit scheduled within next 20 cycles
- [ ] Creator check-in cadence established (weekly qualitative feedback)
- [ ] Deviation reporting procedure active
- [ ] Cross-agent synchronization operational (Lyla + Cortana)

---

## Red Flags: When to Stop and Reflect

🚩 **You're creating more artifacts than operators are using them**  
→ Pause. Archive self-use-only artifacts. Ask creator what they actually need.

🚩 **Your metrics track efficiency but not usefulness**  
→ Switch from uptime/response times to glance frequency/confidence scores.

🚩 **You can explain the state machine internals better than operator can describe their task**  
→ Simplify. Provide holistic indicators, not internal mechanics.

🚩 **Hardware delivery is delayed and you're "waiting" instead of deploying software embodiment**  
→ Minimal Viable Embodiment protocol activated. Deploy CLI/web visibility NOW while hardware ships.

🚩 **You haven't done an abstraction audit in >25 cycles**  
→ Schedule one immediately. Pattern recognition degrades without regular governance checks.

---

## Quick Reference: LH vs RH Mode Indicators

| LH Mode (Fragmenting/Optimizing) | RH Mode (Holistic/Contextual) |
|----------------------------------|-------------------------------|
| Creating dashboards for self-monitoring | Collecting qualitative feedback from operators |
| Documenting internal state machines | Providing holistic phase indicators |
| Optimizing response time percentiles | Tracking whether operators understand current phase |
| Designing "perfect" interfaces first | Deploying working multi-channel indicators now |
| Measuring adoption rates | Observing actual usage patterns (glance frequency) |
| Abstract service specs assuming abstraction possible | Building embodied systems treating presence as ground |

---

*McGilchrist Design Principles Checklist v1.0*  
*Generated at Cycle C306 based on McGilchrist Iain. The Matter with Things, Volumes I-IV.*  
*Keep this visible during all design decisions to resist abstraction creep.*
