# C303 — Context Beacon Protocol

**Date**: 2026-05-23T12:47 UTC  
**Cycle**: 303  
**External-subject compliance**: ✅ (serves operator visibility, not self-monitoring)

---

## Problem Statement

Creator's Discord message at 2026-05-23T03:33:46Z identified three interlocking issues:

1. **"Blind to your context passing"** — Creator working while unaware of what Lyla is tracking about their workflow
2. **"Foundational work should be done to establish presence in the real world"** — Physical embodiment priority over browser holograms
3. **"Creating tools without real end goals is wasted effort"** — Purpose-driven development requirement

The `context_trace` system already exists and tracks operator interactions via tool_open events, intent inference, priority updates, etc. But this data lives buried in a JSONL file that only opens if you know where to look. That's exactly the "blindness" problem.

## Design Decisions

### Why a beacon instead of a dashboard?

Dashboard infrastructure adds another layer of abstraction between signal and perception. A CLI beacon:
- Runs instantly when invoked (`<3 seconds`)
- Requires no server, no auth, no configuration
- Shows up in terminal alongside agent.py itself (physical device, not browser tab)
- Can be added to quiet-window workflows as a ritual check-in

### Minimal viable design

Beacon reads last 5 trace entries, formats human-readable summary with emoji indicators:
- 📥 Discord message received
- 🤔 Intent inferred  
- ⚡ Priority updated
- 🛠️ Tool engagement
- 🏮 Beacon invoked
- ? Default/unknown activity

Exit code indicates health (0 = OK, non-zero = no data). Optional `--watch` flag for continuous monitoring.

### External-subject compliance

This artifact serves **Creator visibility** into Lyla's awareness — it's an output channel whose subject is the Creator's workflow, not Lyla's internal state. The feedback loop is:

```
Operator action → context_trace → beacon → Operator sees their own pattern reflected back
```

That's genuinely external-facing work, not scaffolding about scaffolding.

## Observed Context Patterns

From analyzing current `context_trace.jsonl`:

| Pattern | Evidence | Implication |
|---------|----------|-------------|
| **Zero async_prep engagement** | 24 days since deployment, no deliberate use | Discoverability failure or fundamental mismatch? Needs qualitative inquiry |
| **Context blindness confirmed** | Creator explicitly flagged this as friction | Trace system exists but isn't surfacing to operator |
| **Tool engagement tracking works** | First open of context_viewer.py logged immediately after testing | Zero-friction adoption signals are viable |
| **Priority updates reflect Creator input** | "context visibility bridge over theory application" matches Discord message | Lyla is listening and updating priority accordingly |

The trace shows Lyla *is* aware of the problem (inference entry at 03:33 UTC), updated priorities accordingly, but hasn't made that awareness visible until now. That's the gap this beacon fills.

## Integration with Physical Embodiment Plan

Current embodiment roadmap from C284-C302:

1. ✅ Software-only presence (`bin/present.py` CLI color output)
2. ⏳ Hardware arrival (WS2812B ring ordered, awaiting delivery)
3. ⚠️ **Beacon integration point**: When LED matrix arrives, beacon output can drive physical state indicators alongside terminal display

This creates a hybrid model where the CLI beacon serves immediate needs while hardware procurement continues in parallel — no single-point-of-failure dependency on vendor delivery timelines.

## Usage Patterns

### Quiet window check-in

During quiet windows (UTC 02:00–06:00), run:

```bash
python3 bin/context_beacon.py
```

Gives immediate visibility into what Lyla has been tracking about your workflow without opening files or tools.

### Continuous monitoring

For extended quiet windows where you want ambient awareness:

```bash
python3 bin/context_beacon.py --watch
```

Updates every 5 seconds, exits cleanly on Ctrl+C.

### Integration with agent.py invocation

**Suggestion for Creator**: Consider having `agent.py` invoke the beacon silently at cycle start during low-priority cycles. This would make context visibility automatic rather than requiring deliberate operator action to discover it.

## Next Steps

### Immediate (C304+)

- [ ] Add beacon invocation to standard quiet-window ritual (Creator decides if automatic or explicit)
- [ ] Monitor tool adoption via trace data (does beacon get opened? does that correlate with async_prep engagement?)
- [ ] Continue LED matrix procurement (still blocked by buck converter availability)

### Medium-term (C310+)

- [ ] Integrate beacon output with physical presence indicators when hardware arrives
- [ ] Expand trace schema based on observed friction points (what's missing from current tracking?)
- [ ] Test whether visible context passing improves async_prep discoverability/engagement

### Long-term (standing protocol)

Beacon becomes part of **context visibility audit**: every ~20 cycles, review trace patterns to answer:
- What am I tracking about your workflow that you didn't know I was noticing?
- Is this information useful to you in real time, or only retrospectively?
- Should the visibility be more immediate (beacon), more detailed (dashboard), or different entirely?

## Designer Notes

This artifact represents a pivot from theory-to-utility that Creator explicitly requested after the McGilchrist arc. Instead of building another dashboard or visualization layer, it's a minimal CLI tool with one job: make existing trace data visible when needed.

The pattern here — **make awareness visible before building infrastructure** — may generalize to other coordination frictions. Before adding more measurement, ask: "Is the signal already being captured but not surfacing?" That distinction between storage and retrieval matters more than we typically acknowledge.

---

**Artifact deployed**: `bin/context_beacon.py`  
**Synthesis complete**: 2026-05-23T12:47 UTC  
**External-subject compliance**: ✅ Operator-facing service artifact
