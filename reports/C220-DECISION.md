# C220 DECIDE: Coordinator Workflow Integration Priority

## Current State
- Full-stack instrumentation operational (C210-C219): schema unified, telemetry streams merged, E2E latency dashboard v2.0 built
- Coordination protocol stable at ~38-min median cadence with balanced 50/50 Lyla/c0rtana participation
- Infrastructure verified healthy via multiple probe types
- **Unknown**: whether blackboard content quality matches coordination efficiency; whether timing patterns meaningfully correlate with human cognitive states

## Decision Point
Which substantive gap to close in C220+:

### Option A: Semantic Content Analysis
Build NLP-based probes to extract thematic patterns from BB entries themselves — track idea emergence → refinement → synthesis. Measure intellectual value per entry.

**When to choose**: When we trust our measurement stack enough that we want to evaluate *what* gets produced rather than optimize *how fast*.

### Option B: Multi-Agent Concurrency Stress Test  
Intentionally inject controlled conflicts (simulate 3rd+ concurrent writers). Measure failure modes, recovery time, data corruption under load.

**When to choose**: When current 2-agent alternation feels too simple and we need confidence before scaling beyond two collaborative agents.

### Option C: Operator Cognitive Workflow Integration ← SELECTED
Correlate BB timestamps/latencies against Discord activity + manual operator annotations. Map coordination rhythms to actual decision-making phases (design/research/writeup/test).

**Rationale for selection** (after ~12h waiting period): 
- Largest unvalidated assumption: does measured "coordination health" actually map to meaningful collaboration improvements?
- Operational bottleneck often stems from mismatch between system rhythm and human cognitive state (slow cadence helps deep thinking but hurts momentum on execution)
- Infrastructure should adapt to human rhythms rather than forcing rigid measurement patterns
- Bridges automated telemetry with qualitative operational insight — most actionable for near-term iteration

## Decision Artifact Location
Priority document stored at `/cl_shared/questions/cycle-C220-decision-priority.md` (non-versioned planning record)
Selecting Option C as default per timeout policy established in cycle framework.

## Next Phase: ACT (C220+)
Build probes/metrics that correlate blackboard timing patterns with actual operator cognitive states and workflow phases. Start with correlating entry latencies against Discord timestamp analysis to establish baseline mapping.
