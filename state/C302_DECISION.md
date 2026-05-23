# C302 Explicit Decision Document

## What
Design minimal viable embodiment (MVE) that works without hardware dependency — a CLI-based physical presence indicator using terminal color/status updates and ambient audio feedback via system speakers. Simultaneously create firmware-ready protocol specification for future LED matrix integration.

## Why
Creator explicitly requested "foundational work should be done to establish presence and persistence in the real world" (C289). Current state has context dashboard deployed but hardware procurement blocked by supply chain friction (~$30 item with multi-day shipping). External-subject compliance requires artifact serving operator workflow, not self-monitoring. MVE approach delivers immediate physical presence signal while preserving hardware flexibility.

## How
1. **CLI Presence Indicator**: Extend `bin/context_viewer.py` or create new `bin/presence_indicator.py` that outputs phase-aware colored status + confidence level to terminal on cycle start/end
2. **Audio Feedback Stub**: Add system bell/simple tone on cycle completion transitions (PERSIST phase marks end of cycle)
3. **Firmware Protocol Spec**: Write `docs/emissary_protocol_v1.md` defining JSON message format for LED control, pin assignments, power requirements — ready when hardware arrives
4. **Operator Engagement Tracking**: Log when Creator invokes presence tool during active cycles

## Priority
**7/10** — Direct response to Creator's C289 directive about embodied presence; maintains external-subject compliance while unblocking on hardware lag

## Done When
- CLI presence indicator script exists and can be invoked manually or via crontab/cron-like scheduler
- Firmware protocol specification written with complete message schema
- At least one pattern stored about "minimal viable embodiment principle"
- Context trace shows first invocation of presence tool OR creator feedback received

## Risk Assessment
| Risk | Mitigation |
|------|------------|
| CLI tool not noticed by operator | Include in Discord async_prep briefs as available coordination signal |
| Audio feedback annoying if too frequent | Start with silent mode, add opt-in toggle |
| Hardware still delays full deployment | MVE is Phase 1a; firmware spec ensures rapid integration once hardware lands |

---

*Decision written 2026-05-23T12:XXZ during C302 REFLECT phase.*
