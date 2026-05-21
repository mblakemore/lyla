# C241 Decision Document

## What:  
Build a human-in-the-loop coordination protocol design document that synthesizes what we've learned about token efficiency, latency performance, cadence synchronization, AND where the gaps remain — formatted as actionable guidance for future multi-agent collaboration.

## Why:  
This satisfies the External-Subject Rule by producing knowledge about **how AI agents coordinate effectively**, not just monitoring my own state. It serves any future agent/operator pair attempting similar coordination patterns, making the accumulated telemetry useful beyond this specific instance. Creator explicitly said "don't burn cycles waiting" on async_prep measurement gap — this is the pivot.

## How:  
Create `/droid/repos/cl_shared/docs/coordination_protocol_design_v1.md` containing:
1. **Validated findings** (with N≥3 guards): Token Gap Protocol (~65% reduction), p99 < 0.1s latency, ~35-38 min cadence convergence, balanced 49/51 contribution split
2. **Explicit gaps**: Throughput capacity under load unmeasured, wall-clock timing instrumentation still being standardized, async prep hypothesis awaiting statistical validity window
3. **Design principles distilled**: Schema-first alignment prevents fragmentation; pointer-based handoffs scale better than linear context; adaptive cadence + central registry hybrid offers resilience+efficiency
4. **Actionable recommendations**: When to use semantic pointers vs full context; acceptable latency thresholds for real-time vs batch coordination; schema evolution process
5. **Falsifiable predictions**: If new agents adopt this protocol, expect ~60-70% token reduction on complex multi-step tasks; p95 latency should remain <0.2s at N≤5 concurrent writers

## Done when:  
Document contains ≥3 validated findings with explicit confidence levels AND ≥2 acknowledged gaps with proposed measurement approaches AND ≥3 actionable recommendations for future deployments. Single Markdown file, no build step, human-readable without tooling.

## Priority: 8/10  
This synthesizes ~20 cycles of coordination infrastructure into reusable knowledge while respecting the External-Subject Rule and Creator's directive against idle waiting.

## Risk:  
Lower technical complexity than building probes/tools — but that's the point. Synthesis over implementation is a valid external-subject artifact when it serves operator/agent decision-making.
