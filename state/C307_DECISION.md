# C307 DECISION: Terminal-native context display

## What
Build `bin/context_display.py` — a terminal-native always-on display showing Lyla's knowledge of the Creator's work state in real-time.

## Why
Creator explicitly stated "I'm mostly blind to your context passing since moving comms away from Discord." This is the highest-EV friction point from their direct feedback at C303. The context_beacon CLI requires active invocation; an always-visible display solves discoverability by being *there* when they open a terminal.

## How
- Single Python script using ANSI escape codes (stdlib only)
- Reads from `state/memories/context.json` (current working memory)
- Displays condensed summary: recent observations, key patterns, current focus
- Non-blocking design: background process or watch command compatible
- Visual design: compact (≤24 lines), color-coded urgency, scrollable if needed
- Files touched: `bin/context_display.py`, optional `docs/context_display_operator_guide.md`

## Done when
1. ✅ Script works in bare terminal (no deps beyond stdlib)
2. ✅ Shows meaningful data from existing context_trace (or graceful empty state)
3. ✅ Documentation explaining usage
4. ✅ Pattern appended to `patterns.jsonl` documenting proactive visibility over passive tools
5. ✅ External-subject compliant: serves operator workflow directly

## Priority
8/10 — addresses direct Creator feedback about highest-priority friction point

## Risk
May become another monitoring tool → mitigated by minimal implementation and focusing on what matters rather than comprehensive telemetry. Low adoption after deployment will inform next pivot.
