# PENDING: ESP32 Firmware Endpoint Implementation

## Issue Summary
ESP32 motion sensor coordinator (`esp32_sensor_coordinator.py`) is ready and tested in simulation mode, but cannot communicate with actual ESP32 hardware because the required HTTP endpoint does not exist on the device.

## Missing Endpoint
```
GET http://<ESP32_IP>/api/sensor/motion
Response: {"sensor": "motion", "value": true/false, "timestamp": "<ISO8601Z>"}
```

## Current Status
- ✅ Coordinator CLI: Complete (tested in simulate mode)
- ✅ LED pattern mapping logic: Complete
- ❌ ESP32 firmware: Missing `/api/sensor/motion` endpoint
- ❌ ESP32 firmware: Missing timestamp generation in response

## Impact
Cannot validate real-hardware motion detection flow until this endpoint exists.

## Action Required
Implement `/api/sensor/motion` endpoint on ESP32 firmware using existing motion sensor library. Response must include:
- `sensor`: "motion" (string literal)
- `value`: boolean (true if motion detected, false otherwise)  
- `timestamp`: ISO8601 UTC timestamp ending with 'Z'

## Reference Files
- Coordinator: `/droid/repos/lyla/bin/esp32_sensor_coordinator.py`
- Emissary Protocol spec: See project documentation for exact JSON schema
- ESP32 firmware location: TBD (need to locate repo)

---
Generated: 2026-05-25T00:56:42Z
Worktree: C470_ESP32_MOTION_COORDINATION
