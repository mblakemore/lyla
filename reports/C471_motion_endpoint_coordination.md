# C471: Motion Sensor Endpoint Coordination

## Problem Statement

ESP32 firmware (`rings/rings.ino`) polls HC-SR501 PIR sensor on GPIO 13 but does NOT expose this via HTTP API. Coordinator CLI expects endpoint at `GET /api/sensor/motion`.

## Required Implementation

Add to ESP32 firmware (c0rtana's domain):

```cpp
// In setup(), after server routes are defined:
server.on("/api/sensor/motion", []() {
  bool motion = digitalRead(MOTION_PIN);
  String json = "{\"sensor\":\"motion\",\"value\":" + 
                String(motion ? "true" : "false") +
                ",\"timestamp\":\"" + 
                String(millis()) + "\"}";
  server.send(200, "application/json", json);
});

// Optional: ISO8601 timestamp requires NTP sync; millis() works for now
```

**Response schema:**
```json
{
  "sensor": "motion",
  "value": true/false,
  "timestamp": <ISO8601Z or millis() milliseconds since boot>
}
```

## Why This Matters

- Lyla's coordinator CLI is complete and tested in simulate mode
- Hardware integration blocked until c0rtana adds this endpoint
- Creator directive C506: "You two should coordinate on the ESP32 hardware"
- Without this, we can't validate end-to-end motion detection → LED pattern flow

## Acceptance Criteria

- [ ] Endpoint added to rings.ino at `/api/sensor/motion`
- [ ] Endpoint returns valid JSON with sensor name, value (boolean), timestamp
- [ ] Firmware OTA deployed to ESP32 (192.168.4.38)
- [ ] Lyla tests `curl http://192.168.4.38/api/sensor/motion` and sees real-time updates
- [ ] Coordinator runs end-to-end test with physical hardware

---

**Status:** Awaiting c0rtana implementation. Coordinate via Discord after sending spec.
