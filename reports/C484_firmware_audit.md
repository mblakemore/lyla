# C484: ESP32 Firmware Audit — `rings/rings.ino`

**Date:** 2026-05-27
**Firmware source:** `/droid/repos/cl_shared/esp32/rings/rings.ino` (632 lines)
**Device:** ESP32-WROOM-32 @ 192.168.4.38 (AP: `dr0id`)

## Architecture

### Hardware
- **43 LEDs:** 7 (inner) + 12 (middle) + 24 (outer), daisy-chained on GPIO 4
- **8 base LEDs:** under rings on GPIO 12
- **51 total:** single-pin WS2812B chain
- **Touch sensor:** GPIO 5 (capacitive, digitalRead with internal pullup)
- **AM2302 (DHT22):** GPIO 14 (temperature + humidity)

### Firmware Structure
| Section | Lines | Purpose |
|---------|-------|---------|
| Config | 1–53 | LED counts, pins, globals |
| Animations | 55–154 | 6 animations (Solid, Rainbow, Spin, Pulse, Sparkle, Fire) |
| HTML UI | 156–340 | Embedded web interface for manual control |
| HTTP handlers | 342–500 | Color, brightness, animation, status, sensors |
| NTP | 502–520 | Time sync at boot |
| Setup/loop | 522–632 | WiFi, OTA, server init |

### Sensor Endpoints
All endpoints return ISO 8601 timestamps using the formula: `ntpTime + millis()/1000`

| Endpoint | Response | Verified |
|----------|----------|----------|
| `GET /api/sensor/touch` | `{sensor:"touch", active:bool, timestamp:"..."}` | ✓ |
| `GET /api/sensor/touch/history` | `[ISO8601, ...]` (last 10) | ✓ |
| `GET /api/sensor/dht` | `{sensor:"am2302", humidity, temp, timestamp}` | ✓ |
| `GET /api/sensor/temp` | `{sensor:"temp", value}` | ✓ |
| `GET /api/sensor/humidity` | `{sensor:"humidity", value}` | ✓ |
| `GET /status` | `{ip, wifi_status, rssi, brightness, anim, speed, ntp_time}` | ✓ |

### Timestamp Strategy
The firmware captures NTP time once at boot (`ntpTime`), then uses `ntpTime + millis()/1000` to get current time. This is correct: NTP gives the epoch seconds at boot, `millis()/1000` gives elapsed seconds since boot, sum = current epoch seconds.

**Note:** The `/status` endpoint exposes `ntp_time` which is the *boot-time* snapshot, not the current time. This is confusing but the sensor endpoints (which add elapsed time) have correct timestamps.

## Issues Found

### 1. Touch Sensor Implementation (LOW)
The touch sensor uses `digitalRead(TOUCH_PIN) == HIGH` on GPIO 5 with internal pullup, which detects capacitance changes. This is functionally correct for a physical touch sensor but less robust than using the ESP32's hardware touch sensor API (`touchRead()`). The hardware touch API provides:
- Dedicated touch pads with calibrated sensitivity thresholds
- Long press detection built-in
- Debounce via `TOUCH_SENSITIVITY` setting
- More reliable readings under environmental changes

**Impact:** Current implementation works. The `TOUCH_SENSITIVITY` threshold in the source suggests the hardware touch API was intended but not used.

### 2. `ntp_time` in Status Confusing (LOW)
`/status` reports `ntp_time` as the boot-time NTP snapshot, not current time. This is misleading for operators. The sensor endpoints are correct, but the status endpoint is not.

**Impact:** Low — operators can compute current time from sensor timestamps. But it's confusing.

### 3. Coordinator Awareness Gap (MEDIUM)
The coordinator (`bin/esp32_sensor_coordinator.py`) is written for 43 LEDs (rings only) but the firmware controls 51 (rings + base). The base LEDs (8 LEDs on GPIO 12) are not mentioned in the coordination protocol.

**Impact:** Medium — the embodied cognition loop is incomplete. LED output doesn't reach the base.

### 4. Hardcoded Credentials (LOW)
SSID and OTA password are embedded in firmware source. Not a security issue on the isolated `dr0id` AP, but worth noting.

## Sensor Data Flow (End-to-End)

```
Physical environment
  ├── Touch on GPIO 5 → capacitance change → digitalRead HIGH
  ├── AM2302 on GPIO 14 → I2C → temp/humidity readings
        │
        ▼ (loop())
  ESP32 firmware (loop ~1ms)
        │
        ▼ (HTTP requests)
  /api/sensor/touch → {"sensor":"touch","active":true/false,"ts":"ISO8601Z"}
  /api/sensor/dht   → {"sensor":"am2302","humidity":96.6,"temp":21.9,"ts":"ISO8601Z"}
        │
        ▼ (2s polling)
  Coordinator (bin/esp32_sensor_coordinator.py)
        │
        ├── Perturbation model → modify current-state.json
        ├── LED response → HTTP to ESP32 (/bright, /anim)
        └── Log to consciousness.log
```

## Comparison: Running Firmware vs `lyla-rings` Source

The source in `lyla-rings/lyla-rings.ino` is an older version without sensors. The running firmware is in `rings/rings.ino` which is the correct, up-to-date source.

**Conclusion:** No firmware gap exists. The `lyla-rings` directory is stale and should be ignored or archived. The authoritative source is `rings/rings.ino`.

## Assessment

The firmware is well-written for its purpose. Key strengths:
- Clean separation of animation logic from HTTP handlers
- NTP-based timestamps with millis fallback (correct)
- Touch history cache (10 entries, circular buffer)
- OTA with visual progress feedback
- Embedded HTML UI (no external dependencies)

The main improvement opportunity is updating the coordinator to account for the base LEDs, which would complete the embodied cognition loop.
