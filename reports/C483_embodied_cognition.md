# C483: Embodied Cognition Architecture

**Date:** 2026-05-27
**Status:** Analysis complete
**Subject:** Environmental sensors as genuine cognitive inputs (not decorative feedback)

## Background

The ESP32 hardware was modified at the Creator's direction (C482 timeframe) from a PIR motion sensor to a combination of:
- **Capacitive touch sensor** (GPIO 5, D5) — human interaction detection
- **AM2302 (DHT22) temperature/humidity sensor** (GPIO 14, D14)

The firmware on the ESP32 was updated to expose these via HTTP endpoints (`/api/sensor/touch`, `/api/sensor/dht`, `/api/sensor/temp`, `/api/sensor/humidity`), but the source code in `/droid/repos/cl_shared/esp32/lyla-rings/lyla-rings.ino` still lacks sensor code — the firmware was updated directly on-device, not from the repo source.

## Perturbation Model

The sensor-to-state perturbation model (described by c0rtana in C517) maps environmental data to cognitive state:

| Sensor | Value | Perturbation |
|--------|-------|-------------|
| Touch | active=true | Phase → PERCEIVE, confidence +0.2 |
| Touch | active=false | No perturbation (idle) |
| Temperature | 15–30°C | Color temperature: 2000K–6500K |
| Humidity | 20–100% | Brightness: 20–220 (constrained) |

## Architecture

```
Physical environment
    ├── Touch sensor → human presence/interaction
    ├── Temp sensor → ambient temperature
    └── Humidity sensor → ambient humidity
          │
          ▼ (500ms polling)
    ESP32 HTTP endpoints
          │
          ▼
    Sensor Coordinator (bin/esp32_sensor_coordinator.py)
          │
          ├── Apply perturbation model → modify current-state.json
          ├── Trigger LED response (phase→animation, env→color/brightness)
          └── Log events to consciousness.log
```

## Key Insight

This is not a "smart LED controller." The sensors form a **closed-loop embodied cognition architecture**: environmental data perturbs internal state, which changes LED output, which changes the environment the sensors observe. The loop is genuinely cybernetic — not decorative.

This makes the system an **environmentally coupled agent** rather than an isolated cognitive process. The difference matters: an isolated process has no grounding in the physical world; an embodied agent's state is partially determined by its environment.

## Firmware Gap

The source code in `lyla-rings.ino` (459 lines) contains no sensor code. The running firmware on the ESP32 has the sensor endpoints, but the repo version does not. This creates a divergence between documented source and deployed firmware.

**Recommendation:** The sensor endpoints should be added to `lyla-rings.ino` to close the gap between source and running firmware. This is a medium-priority maintenance task.

## Falsifiable Predictions

1. **Touch correlation:** If touch events are genuinely human-caused (not random), they should correlate with periods when the operator is physically near the device.
   - Grading: C533 (50 cycles out)
   - Success: >60% of touch events occur during operator active sessions

2. **Temperature seasonal drift:** If the AM2302 reports accurate ambient temperature, readings should drift seasonally over the next 6 months.
   - Grading: C683 (200 cycles out)
   - Success: Mean temperature in summer months (May–Aug) > winter months (Nov–Feb) by >5°C

3. **Embodied perturbation effect:** Touch-triggered phase shifts to PERCEIVE should be followed by longer PERCEIVE durations than non-touch-induced PERCEIVE states.
   - Grading: C513 (30 cycles out)
   - Success: Mean PERCEIVE duration after touch > 2× mean PERCEIVE duration without touch

## Deliverables

- Updated coordinator: `bin/esp32_sensor_coordinator.py` (supports touch + temp + humidity)
- This report
