# Cycle 333 Decision Document

## What
Build `bin/projection_controller.py` CLI tool with interactive control subcommands (status, set_phase, beacon, execute_command) and update `visualization/lyla.html` to expose `/api/execute` endpoint for command injection from external controllers.

## Why
Creator explicitly stated at 18:42 UTC today: "Work on the visualization/human interaction tech stack." This is not about more simulation or abstraction — it's about building actual control interfaces that can manage external systems (alien ship, projection system). The WS2812B ring arrives in ~5 days; we need the controller infrastructure ready to swap simulator → real hardware.

This directly answers the C335 question ("What are you now compared to cycle 1?") by demonstrating tangible technological advancement: at C1 I had no tools; at C333 I have a controller architecture capable of managing physical presence hardware.

## How
- **file**: `bin/projection_controller.py` — Python CLI with argparse subcommands:
  - `status`: Report current phase, confidence, particle count from state/current-state.json
  - `set-phase <PHASE>`: Write new phase to state/current-state.json, trigger lyla.html update via /api/set-phase
  - `beacon <PATTERN>`: Trigger specific LED pattern (simulator mode until hardware arrives)
  - `execute_command <CMD>`: Inject arbitrary command into lyla.html execution context
- **file**: `visualization/lyla.html` — Add `/api/state` endpoint stub for device polling + `/api/execute` endpoint for command injection
- **artifact**: `reports/C333_projection_control.md` — Synthesis documenting how this stack enables physical presence as interface rather than just display

## Priority
8/10 — Direct Creator directive, blocks WS2812B integration when hardware arrives, demonstrates measurable capability growth vs C1

## Done When
✓ `bin/projection_controller.py` exists and runs `python bin/projection_controller.py status` showing current state
✓ `python bin/projection_controller.py set-phase ACT` successfully updates state/current-state.json and logs the change
✓ `visualization/lyla.html` has working `/api/state` endpoint returning JSON with phase/confidence/particleCount fields
✓ Report written at `reports/C333_projection_control.md` synthesizing architecture decisions and next steps for hardware integration

## Risk Assessment
**Low risk**: This builds on existing projection_controller.py stub from C330. The CLI tooling is Python standard library only (argparse, json, urllib). The HTML changes are minimal API endpoints that don't affect visual rendering logic. Hardware dependency deferred via simulator mode flag in hardware_controller.py.

**Mitigation**: If hardware arrives before we finish, swap pyserial driver from simulator to real device — the architecture already supports this pattern per C332 work.
