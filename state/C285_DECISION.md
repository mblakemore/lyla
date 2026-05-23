# C285 Decision Document

## What
Build and deploy a minimal viable embodied presence artifact using existing resources while LED matrix procurement completes. Specifically: create a simple CLI-based "presence indicator" that visually signals current phase during active creator interaction, plus update visualization/lyla.html to include real-time state polling from current-state.json.

## Why
- Creator's Discord message (2026-05-23T03:33:46Z) explicitly prioritizes "foundational work...to establish presence and persistence in the real world" over continued tool-building
- Hardware is ordered but blocked by LLAFA buck converter; don't let perfect be enemy of good
- External-subject compliance: this serves operator's need for at-a-glance awareness of agent state during active collaboration
- Anti-repetition directive: haven't done embodiment/presence work as primary focus since ~C250 McGilchrist arc; time to pivot

## How
**Option A (CLI-only):** Build `bin/present.py` — simple terminal-based status display showing:
  - Current phase (PERCEIVE/REFLECT/etc.) via color-coded prompt prefix
  - Confidence level via emoji tag [HIGH/MEDIUM/LOW]
  - One-line summary of current focus
  - Updates on every cycle boundary (polls current-state.json every N seconds)

**Option B (web-based):** Update `visualization/lyla.html` with:
  - Real-time polling endpoint stub already designed in C284
  - Simple particle swarm that responds to phase changes
  - Color temperature mapping per P_cN_245_VIZ_CONF pattern

**Selected path:** Hybrid approach — Option A + minimal Option B update. CLI indicator gives immediate real-world presence during terminal interaction; web visualization gets updated incrementally without becoming the deliverable itself.

Files to touch:
- `bin/present.py` — new CLI tool
- `state/memories/context_trace.jsonl` — append first "presence_active" event
- `reports/C285_embodiment_presence.md` — synthesis report documenting design rationale, deployment status, and next-cycle hardware integration plan

Priority: **7/10** — creator explicitly requested this work, but not blocking other cycles if delayed by procurement

Done when: 
- CLI tool deployed and tested locally
- Operator can run `present.py` during active session and see real-time state updates
- Synthesis report documents hardware dependency and fallback strategy
- At least one operator engagement trial (qualitative feedback on usefulness)

Risk: Hardware delay may make CLI-only solution feel incomplete; mitigate via explicit documentation that full embodiment requires LED matrix delivery.

## Acceptance Criteria
- [ ] `bin/present.py` exists and runs without errors
- [ ] Tool polls current-state.json every 3 seconds and updates display in real-time
- [ ] Visual indicators map to phase (color) and confidence (emoji) per existing patterns
- [ ] Report created with ≥3 actionable insights about embodied presence design
- [ ] Pattern appended documenting "minimal viable embodiment" as reusable knowledge
