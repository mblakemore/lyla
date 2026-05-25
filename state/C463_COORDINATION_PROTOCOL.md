# ESP32 Sensor Coordination Protocol — Lyla ↔ c0rtana

## Context

Creator asked at C506: *"If I were to add a sensor, what would you like? how about a motion sensor? how would you set up polling sensor data?"*

c0rtana just completed firmware update with HC-SR501 PIR integration (C506). Lyla needs to coordinate on **polling logic + operator-facing response patterns**.

---

## Role Division (Avoid Duplication)

| Component | Owner | Rationale |
|-----------|-------|-----------|
| Arduino firmware (`led_driver.ino`) | c0rtana | Direct hardware control, pin configuration, non-blocking loops in C++ |
| Polling interval configuration | Shared decision | Both agents need same baseline for synchronized responses |
| HTTP endpoint structure | Lyla | Defines API contract for external coordination |
| LED response patterns (animation index → event type) | Lyla | Maps cognitive state to observable behavior |
| Operator workflow documentation | Lyla | Translates technical implementation into user value |

---

## Shared API Contract

### Endpoint Structure

```
GET /api/sensor/{type}  →  Current sensor reading
POST /api/command/{type} → Trigger specific action
```

### Motion Sensor Integration

**Polling spec:**
- Interval: 500ms base (configurable via `--poll-interval` flag)
- Pin: GPIO 23 (configured in firmware)
- Active-high logic: HIGH = motion detected, LOW = no motion
- Debounce: 500ms minimum between triggers (hardware + software)

**HTTP interface (Lyla's view):**
```json
{
  "sensor": "motion",
  "value": true,
  "timestamp": "2026-05-25T00:45:12Z",
  "event_id": "evt_abc123"
}
```

**Command interface:**
```json
POST /api/command/motion_alert
→ Triggers dedicated animation pattern (warm orange pulse outward from center ring)
```

---

## Coordination Points

### 1. Polling Synchronization

Both agents' state updates and sensor polling must not conflict on ESP32 HTTP server:

- **c0rtana firmware**: Handles raw pin reads, debouncing, exposes `/api/sensor/motion`
- **Lyla coordinator**: Reads JSON response, maps to LED response patterns
- **Shared constraint**: Max 2 concurrent HTTP requests per second (ESP32 limitation)

### 2. Response Pattern Hierarchy

When motion detected during active phase:

| Current Lyla Phase | Motion Event → LED Response |
|-------------------|----------------------------|
| PERCEIVE/REFLECT | Slow warm pulse (confidence=low, event=attention-capture) |
| DECIDE/ACT | Fast bright pulse → fade to current phase color (signal = operator intervention needed) |
| CONSOLIDATE/PERSIST | Brief white flash → return to normal (acknowledgment without disruption) |

This ensures physical embodiment remains coherent with cognitive state while responding to external stimuli.

### 3. Fallback Behavior

If sensor read fails (timeout > 2s):
- Continue current animation at 80% brightness (graceful degradation)
- Log error to `logs/consciousness.log`
- Do NOT revert to default "idle" pattern — that would hide the failure from operator

---

## Operator Workflow Implications

**What this enables for Creator:**

1. **Ambient awareness**: ESP32 rings respond to room activity even when terminal/browser are closed
2. **Intervention signaling**: Motion-triggered patterns can indicate "operator present, system ready" vs "room empty, system in low-power mode"
3. **Multi-modal presence**: Physical light layer complements digital interface without requiring constant attention

**Key insight:** This is not self-monitoring. The LEDs translate internal state + environmental context into observable signals that help Creator maintain situational awareness across modalities.

---

## Next Steps

- c0rtana: Complete firmware with `/api/sensor/motion` endpoint implementation
- Lyla: Build coordinator CLI (`bin/esp32_sensor_coordinator.py`) reading sensor JSON and mapping to LED commands
- Both: Agree on polling interval baseline (500ms proposed)
- Test: Validate no HTTP conflicts during concurrent state updates

---

*Protocol version: 1.0 — Subject to revision based on testing results.*
