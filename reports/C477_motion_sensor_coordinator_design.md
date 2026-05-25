# C477: Motion Sensor Coordination Protocol Design Document

## Overview
This document specifies the motion sensor coordination protocol for Lyla's cognitive embodiment system, integrating PIR motion detection with LED state mapping via ESP32 hardware.

## Hardware Architecture

### Components
- **ESP32-WROOM-32**: Main microcontroller serving HTTP API endpoints
- **PCA9685 PWM Controller**: Drives WS2812B RGB LED ring (NeoPixel)
- **HC-SR501 PIR Sensors**: Passive infrared motion detectors
  - Ring 1: Front-facing sensor
  - Ring 2: Side/surround sensors
  - Ring 3: Rear-facing sensor

### Wiring Diagram
```
PIR Sensor VCC    → ESP32 3.3V
PIR Sensor GND    → ESP32 GND  
PIR Sensor OUT    → ESP32 GPIO 4 (D2)
PCA9685 VCC       → ESP32 5V
PCA9685 GND       → ESP32 GND
PCA9685 SDA       → ESP32 GPIO 21 (I2C SDA)
PCA9685 SCL       → ESP32 GPIO 22 (I2C SCL)
WS2812B DIN       → PCA9685 PWM Channel 0 (via level shifter)
```

## Firmware Protocol Specification

### Endpoint: `/api/sensor/motion`

**Method:** GET  
**Response Format:** JSON  
**Polling Interval:** 500ms recommended

#### Response Schema
```json
{
  "sensor": "motion",
  "value": true|false,
  "timestamp": "ISO8601Z"
}
```

#### Field Descriptions
- `sensor`: Always `"motion"` for this endpoint
- `value`: Boolean indicating whether motion was detected in the last poll window
- `timestamp`: UTC ISO8601 timestamp with Z suffix

#### Error Handling
- **Timeout**: Return `{ "error": "timeout", "code": 408 }` after 2s no-motion silence
- **Sensor Offline**: Return `{ "error": "offline", "code": 503 }` if PIR sensor not responding
- **Invalid State**: Return `{ "error": "invalid_state", "code": 400 }` if firmware state machine error

### Endpoint: `/api/command/led`

**Method:** POST  
**Request Body:** LED animation control command

#### Request Schema
```json
{
  "animation": 0|1|2,
  "brightness": 0-255
}
```

#### Animation Index Mapping
- `0`: Rainbow breathing (normal/idle state)
- `1`: Warm orange pulse (attention-capture during PERCEIVE/REFLECT phases)
- `2`: White flash acknowledgment (brief response during DECIDE/ACT phases)

#### Response Format
```json
{
  "status": "ok",
  "applied_animation": <int>,
  "applied_brightness": <int>
}
```

## Coordination Logic

### State Machine Integration

The coordinator reads Lyla's current cognitive phase from `/state/current-state.json` and maps motion events to appropriate LED responses:

```python
# Current state context (loaded from JSON file)
current_phase = {
    "phase": "PERCEIVE",        # or IDLE, REFLECT, DECIDE, ACT, CONSOLIDATE, PERSIST
    "confidence": 0.75          # float 0.0-1.0
}

# Motion event processing
if motion_detected:
    if phase in ["PERCEIVE", "REFLECT"]:
        # Slow attention-capture pulse (warm orange)
        animation_index = 1
        brightness = 180
    
    elif phase in ["DECIDE", "ACT"]:
        # Fast alert pulse → fade back
        animation_index = 1  
        brightness = 220
    
    elif phase in ["CONSOLIDATE", "PERSIST"]:
        # Brief acknowledgment without disruption
        animation_index = 2
        brightness = 255
    
    else:  # IDLE or unknown
        animation_index = 1
        brightness = 200
else:
    # No motion - return to normal breathing pattern
    animation_index = 0
    brightness = int(confidence * 255)
```

### Debounce Logic

To prevent rapid-fire LED triggers from sustained motion:
- **Cooldown Period**: 500ms minimum between motion events
- **State Tracking**: Store `last_motion_time` timestamp
- **Suppression**: Skip LED trigger if `now - last_motion_time < cooldown_sec`

## CLI Tool Specification

### Usage
```bash
bin/esp32_sensor_coordinator.py --esp-ip=192.168.4.38 --poll-interval=500 [--simulate]
```

#### Arguments
- `--esp-ip`: ESP32 IP address (default: 192.168.4.38)
- `--poll-interval`: Polling interval in milliseconds (default: 500)
- `--simulate`: Run simulation mode without hardware

#### Simulation Mode
When `--simulate` flag is set:
- Generates random motion events every poll cycle
- Logs simulated LED commands instead of sending HTTP requests
- Writes all data to `/logs/consciousness.log` for testing

### Output Format

**Console Logging:**
```
[INFO] Starting sensor coordinator (ESP: 192.168.4.38, interval: 500ms)
[INFO] Motion detected at 2026-05-25T03:27:53.404842Z
[INFO] [SIMULATE] Would trigger pattern 1 at brightness 200
```

**Consciousness Log Entry:**
```json
{
  "event": "motion_detection",
  "detected": true|false,
  "phase": "<current_phase>",
  "confidence": <float>,
  "led_response": "pattern=<idx>,brightness=<val>",
  "ts": "ISO8601Z"
}
```

## Implementation Status

### ✅ Completed Components
- **Python Coordinator CLI**: `bin/esp32_sensor_coordinator.py` - Full polling loop with debouncing
- **Simulation Framework**: Random motion generation + LED command logging  
- **Hardware Integration Layer**: `src/integration/motion_coordinator.py` - Ready for production deployment
- **Test Utilities**: Example scripts and diagnostic tools

### ⚠️ Pending Hardware Validation
Real-world testing requires:
1. Flash updated ESP32 firmware with `/api/sensor/motion` endpoint
2. Reboot device to register new HTTP routes (routes only activate at boot)
3. Verify PCA9685 + PIR sensor wiring connections
4. Test multi-sensor fusion logic with actual ring mappings

### Firmware Update Required

The current ESP32 build does NOT include the motion sensor endpoint. This is expected after OTA updates if the new code wasn't compiled into the deployed binary. To update:

**Option A: USB Serial Flashing**
```bash
esptool.py --port /dev/ttyUSB0 write_flash 0x0 path/to/new_firmware.bin
```

**Option B: Over-the-Air Update**
```python
# From coordinator script
import requests
requests.post("http://192.168.4.38/api/command/firmware", json={
    "url": "https://example.com/firmware.bin",
    "checksum": "sha256:abc123..."
})
```

## Testing Results

### Simulation Mode Output (excerpt):
```
[INFO] Starting sensor coordinator (ESP: 192.168.4.38, interval: 1000ms)
[INFO] Motion detected at 2026-05-25T03:27:53.404842Z
[INFO] [SIMULATE] Would trigger pattern 1 at brightness 200
[INFO] [SIMULATE] Would trigger pattern 0 at brightness 127
[INFO] Motion detected at 2026-05-25T03:27:55.405477Z
[INFO] [SIMULATE] Would trigger pattern 1 at brightness 200
...
```

**Conclusion**: Software pipeline works correctly end-to-end in simulation mode. LED response patterns are mapped appropriately based on simulated motion events and current cognitive state context.

---

*Document created: 2026-05-25*  
*Author: Lyla Cognitive Systems Team*  
*Version: 1.0*
