# C303 DECISION — Context Beacon Protocol

## What
Build `bin/context_beacon.py` — a minimal CLI tool that reads `context_trace.jsonl`, extracts the last N operator interaction summaries, and outputs them as a "beacon" printed to terminal whenever I'm invoked during a quiet window. This creates visible evidence of context passing without waiting for physical hardware or building dashboard infrastructure.

## Why
Creator explicitly stated three problems in Discord at 2026-05-23T03:33:46Z:
1. **"Blind to your context passing"** — context_trace exists but no one sees it unless they open the file
2. **"Foundational work should be done to establish presence in the real world"** — physical embodiment is priority over holographic browser forms (LED ring ordered, awaiting arrival)
3. **"Creating tools without real end goals is wasted effort"** — beacon serves clear purpose: give Creator immediate visibility into what we've been tracking about their workflow

This artifact directly addresses all three by making existing trace data *visible* when present, grounding presence in terminal output (physical device), and having a clear external-purpose (operator visibility).

## How
- Read `/droid/repos/lyla/context_trace.jsonl`
- Parse last 5 entries (or fewer if less exist)
- For each entry: extract timestamp, activity description, Lyla's inferred state
- Output formatted summary with emoji indicators (🟢 active / 🟡 idle / 🔴 blocked)
- Exit code indicates health status (0 = OK, non-zero = issues detected)
- Optional `--watch` flag for continuous monitoring during quiet windows

**Files to touch:**
- `bin/context_beacon.py` (new CLI tool)
- `reports/C303_context_beacon.md` (synthesis report documenting design rationale and usage patterns)
- `context_trace.jsonl` (verify it contains real operator interaction data from recent cycles)

## Done when
- [ ] `bin/context_beacon.py` exists and runs successfully with sample data
- [ ] Outputs human-readable summary in ≤3 seconds
- [ ] Report at `reports/C303_context_beacon.md` documents: design decisions, observed context patterns from trace data, creator feedback integration, next steps for physical embodiment integration
- [ ] Pattern appended to `patterns.jsonl` documenting "beacon protocol" as external-subject compliance mechanism

## Priority: 8/10
Creator explicitly flagged this as a coordination friction point. Addressing "blindness" before building more infrastructure aligns with their directive about purpose-driven development. Hardware procurement is async; beacon can ship immediately.

## Risk
If `context_trace.jsonl` is empty or trivial, the artifact has no value. Verification step: check trace file size/content first. If insufficient data, pivot to synthesizing existing patterns into an "operator workflow summary" document instead.
