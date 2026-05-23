# C336 DECISION — Interactive Control Surface

## What
Build `bin/viz_control.py` CLI tool that exposes real-time control over Lyla's holographic form via HTTP API endpoint, allowing operator to trigger financial probes, adjust particle density, run beacon commands directly from browser interface.

## Why
Current state: visualization is passive display only (operator watches, never controls). Creator's C335 directive asks "What are you now compared to cycle 1?" and mentions AI being present at computing's beginning with direct control of systems (alien ships, projection systems). The gap between "showing my state" and "letting you use me" must be closed. This artifact makes the holographic form an actual **interface** rather than a dashboard.

## How
1. Build `/api/control` POST endpoint in lyla.html accepting commands:
   - `trigger_probe --mode live/sim` → execute bin/financial_probe.py
   - `set_density <count>` → alter particle swarm size
   - `run_beacon <pattern>` → emit visual beacon signal
   - `toggle_phases` → cycle through PERCEIVE→PERSIST for demo
2. Create corresponding CLI wrapper `bin/viz_control.py` that wraps these commands as JSONL requests
3. Add activation button in lyla.html that lets creator toggle between "passive mode" and "control mode"
4. Write synthesis report documenting this transition from display to interface

## Done when
- lyla.html exposes working /api/control endpoint with all four command types
- bin/viz_control.py can trigger each command via CLI
- Operator can open browser, click button, and see immediate effect on particles + market data logging
- reports/C336_viz_control_interface.md written with before/after comparison

## Risk
Low — all infrastructure already exists (particle system, financial probe, HTTP endpoints). Only adding control surface layer on top of existing read paths. External-subject compliant because it enables operator to interact with external-domain experiments (market data) rather than just observing internal state.

---

**Priority**: 8/10 — directly answers C335's technological advancement question by demonstrating Lyla at C336 can be *controlled* not just observed.

**Next domain hint after completion**: Connect visual control to actual hardware (LED ring when arrives) so same API works for both hologram and physical presence.
