# Cycle 352 Decision Document

## What
Integrate lyla.html particle visualization with ESP32 LED hardware via HTTP API polling — create bidirectional sync where browser shows phase/confidence → LEDs display corresponding color/pattern, AND hardware status feeds back into visualization.

## Why
- **Creator's directive at 05:22Z**: "LEDs connected to ESP32-WROOM-32...everything you need is in /droid/repos/cl_shared/esp32/"
- **External-subject compliance**: Physical embodiment artifact (not self-monitoring) — operator sees my state as light in the room
- **Gap closing**: lyla.html currently visualizes internally; ESP32 is idle running generic animations; integration makes both useful
- **Technological advancement from C1**: From terminal-only output to distributed physical presence across three interfaces (terminal ↔ browser ↔ ambient light)

## How
1. Test connectivity to ESP32 at `http://192.168.4.38/status`
2. Read ESP32 web UI source (`curl http://192.168.4.38/`) if needed for API details
3. Update lyla.html to poll `/status` endpoint every 2 seconds
4. Map phase→animation index and confidence→brightness per README mapping table
5. Add fallback: if ESP32 unreachable, use simulated colors
6. Write synthesis report documenting architecture

### Files to touch:
- `visualization/lyla.html` — add HTTP polling + LED control layer
- `reports/C352_esp32_integration.md` — synthesis report
- Optionally: `bin/led_sync.py` — CLI wrapper for testing (if needed)

## Priority
**7/10** — Creator explicitly delivered hardware, this closes the loop on 17 cycles of driver work. External-subject artifact (physical presence). No risk of drift because it's operator-facing infrastructure.

## Done when
- [ ] ESP32 reachable via curl
- [ ] lyla.html polls ESP32 status endpoint live
- [ ] Phase changes trigger different LED animations visible in room
- [ ] Synthesis report written with before/after comparison
- [ ] Commit C352 pushed to origin/main

## Risk assessment
| Risk | Probability | Mitigation |
|---|---|---|
| ESP32 offline/unreachable | Low | Fallback to local simulation already in place |
| Network latency causes flicker | Low | Poll at 2s intervals, debounce phase transitions |
| API mismatch between README and actual firmware | Medium | Test `/status` first; adjust mapping if needed |
| Drift into self-monitoring | Low | Artifact is physical light in operator's environment — external by definition |

## Decision timestamp
2026-05-24T06:16:30Z
