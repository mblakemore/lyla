# C481 Decision Document

## What
Run ESP32 motion sensor coordinator CLI in simulate mode to verify end-to-end event→pattern mapping works correctly, then write validation report.

## Why
- Hardware endpoint confirmed operational after Creator's reboot (C480)
- Timestamp bug exists in rings.ino but doesn't block data flow testing
- Simulate mode tests the full coordination logic without waiting for firmware fix
- Maintains external-subject compliance via physical device integration artifact

## How
1. Run `bin/esp32_sensor_coordinator.py --simulate` (or appropriate flag)
2. Verify motion detection → LED pattern mapping with brightness scaling
3. Check consciousness.log for event logging
4. Write reports/C481_motion_validation.md documenting results and remaining firmware gap

Files touched:
- bin/esp32_sensor_coordinator.py (read only — already built)
- logs/consciousness.log (append events)
- reports/C481_motion_validation.md (new artifact)

## Priority
7/10 — hardware feedback loop is critical operator tool; simulator test unblocks future deployment once timestamp fixed

## Done When
- Report contains ≥3 data points: polling cadence, pattern mapping correctness, brightness scaling behavior
- Explicit limitations section noting timestamp bug
- Actionable next steps documented (firmware patch needed vs. workaround)
- External-subject compliant (serves operator's physical-auditory feedback, not self-monitoring)

## Risk Assessment
Low risk — simulate mode doesn't require live hardware access, can be rolled back if issues found.

---
*Decision made at C481 cycle start by Lyla*
