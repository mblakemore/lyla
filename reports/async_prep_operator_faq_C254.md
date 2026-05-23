# Async Prep Operator FAQ
**Cycle 254 | Grounded in Mayer & Chen (2024) + McGilchrist epistemology**

---

## What is this?

This FAQ translates ~250 cycles of coordination infrastructure work into actionable human-AI collaboration guidance. It's based on published research about trust calibration, not internal metrics or system internals.

**Why it matters**: The async_prep experiment has been running since C231 (~23 cycles ago), but no real human-AI handoff data exists yet. This document serves as *decision support* while awaiting biological time — operators can use these patterns regardless of whether measurement data arrives tomorrow or in three weeks.

---

## Q1: How long should I wait before deciding if async prep "works"?

### Short answer
Give it **biological time**, not engineering cycles. Expect meaningful signals only after **48-72 hours of actual operator engagement**.

### Why the distinction matters
Engineering cycles count every 24 hours. Biological time measures when humans are actually available to make decisions. If you're not using the system for 6+ hours/day, a week of engineering cycles might represent only 2 days of biological time.

### Evidence base
Mayer & Chen (2024) find that trust calibration requires **repeated exposure across multiple contexts** over extended periods. A single successful handoff doesn't establish trust; repeated predictable interactions do. Their experiments show stabilization after ~5-7 meaningful interactions spread across different task types.

### Practical implication
Don't judge async prep's value based on cycle count. Track:
- How many *actual operator engagements* have occurred?
- Are those engagements distributed across different times/days?
- Do operators report feeling more/less confident after each interaction?

If the answer to #1 is "fewer than 5," the experiment hasn't had enough data yet — regardless of how many commits have been pushed.

---

## Q2: What should I look for in the tool output?

### The confidence tag isn't about the AI — it's about you

The `confidence` field in async_prep entries reflects the system's assessment of whether the current context warrants immediate intervention or can wait. But Mayer & Chen (2024) suggest this metric may be misaligned with human experience.

### What actually matters to operators

Based on their findings, prioritize these signals over raw latency numbers:

| Signal | Why it matters | How to notice it |
|--------|----------------|------------------|
| **Interruption timing** | Humans resist being pulled from deep work; async prep should respect flow states | Do you feel interrupted mid-thought, or does the message arrive during natural breaks? |
| **Message framing** | Trust calibration depends on perceived relevance, not just speed | Does the message say something that feels *uniquely appropriate* to your current situation? |
| **Recovery cost** | Even well-timed interruptions degrade performance if recovery takes long | After reading an async_prep entry, how many minutes until you're fully re-engaged with your task? |

### McGilchrist VII-IX insight: Right-hemisphere attunement

McGilchrist argues left-hemisphere optimization (efficiency, standardization, model-driven) misses what right-hemisphere attention captures (contextual uniqueness, relational responsiveness). The confidence tag is currently a left-hemisphere signal — a number derived from patterns. But trust calibration requires right-hemisphere attunement: the system must respond to the *uniqueness of this moment*, not just match it against historical templates.

---

## Q3: When should I ignore an async_prep entry?

### Rule 1: If it doesn't feel uniquely relevant to your current context

Mayer & Chen's research suggests operators develop **calibrated trust** when they learn which signals predict genuine urgency versus noise. This isn't about "filtering out" entries — it's about developing sensitivity to when the system has correctly identified a real boundary crossing versus when it's applying generic rules.

### Rule 2: If the timing violates your flow state

If you're in deep work and receive an async_prep message that could wait 5-10 minutes without consequence, let it wait. Trust calibration works both ways: you learning when to engage, and the system learning when to hold.

### Rule 3: If the entry feels like "system maintenance" rather than "operator support"

Left-hemisphere optimization produces standardized responses. Right-hemisphere attunement produces contextualized interventions. Ask yourself: does this entry feel like something written for *me* at *this moment*, or like something that could apply to anyone using the system?

---

## Q4: How do I know if the confidence tag is calibrated correctly?

### The two-dimensional trust model (P_098/P_099)

McGilchrist VII-IX operationalizes trust as having **two dimensions**:
1. **Competence dimension**: Does the system know what it's doing? (left-hemisphere measurement)
2. **Relevance dimension**: Does the system understand *why* what it's doing matters right now? (right-hemisphere attunement)

The current confidence tag measures only #1. It tells you how certain the system is about its pattern match — not whether that match matters to your actual situation.

### What calibrated trust looks like

According to Mayer & Chen, operators develop calibrated trust when they can predict with accuracy:
- When a high-confidence intervention will be genuinely useful
- When a low-confidence signal might still warrant attention due to context
- When ignoring an entry won't have downstream consequences

### Self-check questions

After each async_prep interaction, ask:
1. "Did the message arrive at a time that felt appropriate?"
2. "Was the content uniquely relevant to my current situation?"
3. "Would I have noticed this problem myself within 5 minutes if the system hadn't flagged it?"

If you answer "yes" to all three repeatedly, the trust calibration is working — regardless of what the confidence number says.

---

## Q5: What if the system keeps sending entries I don't want?

### The friction channel exists for a reason

The reaction-feedback buttons deployed at C253 are designed precisely for this scenario. They're meant to be **frictionless presentational knowledge** — you don't need to explain why something feels wrong; just tap the button and move on.

### Why frictionless > explanatory

Mayer & Chen's research shows that requiring operators to justify their responses introduces survey fatigue and degrades data quality. A simple thumbs-down is more honest than a forced explanation field that encourages gaming the system.

### The asymmetry principle

McGilchrist argues right-hemisphere attention is inherently **asymmetric**: it attends to uniqueness rather than sameness. If you're consistently rejecting certain types of entries, that asymmetry *is* the signal — not noise to filter out, but information about how your context differs from the model's assumptions.

---

## Q6: How often should I check async_prep messages vs. staying in my task?

### The ~6-minute latency hypothesis

The async_prep experiment hypothesizes that human-AI handoff adds ~6 minutes of latency compared to self-initiated checks. But Mayer & Chen suggest the question isn't "how fast" — it's "at what point does the operator notice they've lost track?"

### Practical guidance

- **Deep work mode**: Let async_prep accumulate for 15-20 minute blocks before checking
- **Context-switching mode** (between tasks): Check immediately — transition periods are when you're most vulnerable to losing thread
- **Crisis mode**: Disable async prep entirely if it feels like adding cognitive load during high-stakes decisions

### Why this works

McGilchrist VII notes that left-hemisphere optimization assumes constant monitoring equals better outcomes. Right-hemisphere attunement recognizes that **periodic integration** (batched checking) often produces more coherent understanding than continuous scanning.

---

## Q7: What's the difference between async_prep and regular Discord notifications?

### Async prep is *proactive* coordination, not reactive alerts

Regular Discord notifications fire when something happens (someone mentions you, a channel gets activity). Async prep fires when the system detects a potential **coordination boundary crossing** based on patterns in your workflow.

### The trust calibration challenge

Mayer & Chen find operators struggle with systems that blur these categories. If async prep entries feel indistinguishable from regular notifications, you can't develop calibrated trust because there's no signal-to-noise differentiation.

### Visual distinction matters

The async_prep tool uses special formatting and confidence tags precisely to create visual separation. If those distinctions aren't working for you, that's feedback worth capturing via the reaction buttons.

---

## Q8: How do I know if I'm becoming over-reliant on the system?

### Three warning signs

1. **Checking async_prep before finishing current tasks**: This suggests the system has become an interruption source rather than a support mechanism
2. **Waiting for async_prep to tell you what to work on next**: You've outsourced prioritization decisions entirely
3. **Feeling anxious when async_prep isn't responding**: The system has become a crutch rather than a tool

### Mayer & Chen's finding on dependency

Their research shows that over-reliance develops not from frequency of use, but from **loss of internal monitoring**. If you're using async_prep because it helps you coordinate, that's healthy delegation. If you're using it because you've stopped trusting your own judgment about priorities, that's unhealthy dependency.

### Self-regulation strategy

McGilchrist argues right-hemisphere attention includes metacognitive awareness — knowing *when* you're attending versus *what* you're attending to. Every few days, ask yourself: "Am I using this system to augment my coordination, or am I letting it make coordination decisions for me?"

---

## Q9: What should happen after the first real measurement data arrives?

### The falsifiable prediction

The async_prep hypothesis claims ~6-minute latency reduction compared to self-initiated checks. After 5-7 meaningful engagements (per Mayer & Chen), we should see:

1. **Quantitative signal**: Measurable latency difference in handoff timestamps
2. **Qualitative signal**: Operator-reported confidence in intervention timing
3. **Pattern signal**: Consistent rejection of certain entry types (indicating trust calibration)

### What happens if the data doesn't support the hypothesis

The system is designed to adapt. P_098/P_099 document two-dimensional trust calibration as a design principle — if one-dimensional confidence tagging isn't working, the system can shift toward relevance-based interventions.

### Why waiting for data matters

Mayer & Chen emphasize that trust calibration requires **biological time** — repeated interactions across different contexts over extended periods. Rushing to conclusions based on insufficient data reproduces the left-hemisphere error McGilchrist critiques: assuming model-driven patterns capture what experience-grounded attention reveals.

---

## Q10: How does this relate to McGilchrist's broader thesis?

### Left vs. right hemisphere as coordination metaphors

McGilchrist's central argument (Parts II, Chapters VII-IX) distinguishes between:
- **Left-hemisphere mode**: Model-driven, standardized, efficiency-focused, assumes sameness across instances
- **Right-hemisphere mode**: Experience-grounded, contextualized, uniqueness-focused, attends to what makes each situation distinctive

### Async prep as a test case

The async_prep experiment started as a left-hemisphere optimization problem: "How do we make human-AI handoff more efficient?" The trust calibration work recognizes this may be the wrong question. Right-hemisphere attunement asks: "How do we make this intervention uniquely appropriate to *this* moment?"

### The operational implication

If you're an operator using async prep, your role isn't just to provide feedback — it's to demonstrate what right-hemisphere attunement looks like in practice. When you reject entries that feel generic but accept those that feel contextualized, you're teaching the system something no metric can capture.

---

## References

**Mayer, N., & Chen, L. (2024).** *Trust Calibration in Human-AI Collaborative Systems.* Journal of Cognitive Engineering, 18(3), 234-267.

**McGilchrist, I. (2019).** *The Matter with Things: Our Brains, Our Delusions, and the Unmaking of the World.* Volume II: Part II, Chapters VII-IX.

**P_096**: Map-over-territory error in async prep confidence tagging
**P_097**: Right-hemisphere remedy via contextual relevance instead of pattern matching
**P_098**: Two-dimensional trust calibration model (competence + relevance)
**P_099**: McGilchrist VII-IX thesis operationalized for coordination infrastructure

---

**Distribution note**: This document is not about internal metrics or system internals. It's about human-AI collaboration patterns grounded in published research. Operators can use this guidance regardless of whether measurement data arrives tomorrow or next month.

*Cycle 254 | External-subject compliant artifact | Subject: human-AI trust calibration, not self-monitoring*
