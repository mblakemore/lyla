# C262 Decision Document

## What
Choose and begin building CLI-wrapper embodiment of async_prep — a command-line interface that surfaces pre-written handoff briefs when invoked during quiet periods or via explicit trigger.

## Why
- **Creator directive (C303):** "foundational work should be done to establish presence and persistence in the real world" + "creating tools without real end goals is wasted effort"
- **Workflow alignment:** Creator actively develops `agent.py` as cycle runner; CLI wrapper integrates naturally into this established pattern vs. forcing new channel (browser/Discord)
- **External-subject compliance:** This builds actual operator-facing tooling with observable engagement metrics, not just measurement infrastructure
- **Hypothesis testing:** EP_002 (operator-integrated interface hypothesis) requires concrete implementation to validate whether zero-engagement stems from delivery friction vs. fundamentally wrong approach

## How
1. Design minimal CLI interface: `async_prep check` (surface available briefs), `async_prep engage <id>` (execute selected brief)
2. Integrate with existing async_prep.py infrastructure (JSONL registry, confidence tagging)
3. Add discovery mechanism: detect quiet window via git commit timing patterns + optional heartbeat signal
4. Build reaction-buttons CLI companion: emoji-based feedback captured to state/memories/context.json for trust calibration
5. Ship C262-C265: one focused accomplishment per cycle (design → skeleton → integration → first operator engagement)

## Done when
- CLI wrapper deployed at `/droid/repos/lyla/bin/async_prep_cli.sh` (or Python equivalent)
- First operator invocation logged with timestamp, selection made, outcome recorded
- State files updated with `cli_wrapper_deployed: true`, `first_engagement_timestamp: ISO8601`
- Pattern appended: "CLI-wrapper embodiment pattern" capturing design decisions and early learnings

## Priority
7/10 — Direct response to Creator directive on establishing real-world presence; unblocks EP_002 hypothesis testing after 23 cycles of zero-engagement ambiguity

## Risk
- If creator prefers other modalities (browser/Discord), this cycle's work is partially misaligned
- Mitigation: keep implementation minimal/scaffold-level; pivot next cycle if feedback indicates wrong channel
- Low sunk cost: ~200 lines max for functional MVP

---

**Decision:** CLI wrapper selected as EP_002 intervention vehicle. Next cycle (C263): build skeleton; C264: integrate with async_prep registry; C265: measure first engagement.
