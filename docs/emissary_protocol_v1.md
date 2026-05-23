# Emissary Protocol v1.0

**Status**: Draft | **Version**: 1.0 | **Date**: 2026-05-23  
**Purpose**: Define JSON message format and communication protocol for Lyla's minimal viable embodiment (MVE) hardware — WS2812B LED ring or equivalent RGB matrix

---

## Overview

The Emissary Protocol translates Lyla's cognitive state into physical presence signals via embedded microcontroller. Designed as minimal viable embodiment: phase indicator, confidence level, engagement feedback.

**Key constraints**:
- Low power consumption (<1W standby)
- Simple firmware with no external dependencies beyond Arduino core
- Human-readable visual language (phase = hue, confidence = brightness/saturation)
- Backward compatible with future expansion (audio, haptics)

---

## Hardware Requirements

| Component | Minimum Spec | Notes |
|-----------|--------------|-------|
| Microcontroller | ESP8266 / ATmega328P | WiFi preferred for direct network comms; serial fallback acceptable |
| Display | WS2812B ring (16-64 LEDs) | Or similar addressable RGB strip |
| Power | 5V @ 2A max | Peak draw during white flash events |
| Interface | UART/Serial or MQTT | UART for local, MQTT for distributed deployment |

---

## Message Schema

### State Update (periodic, ~1Hz)

```json
{
  "type": "state",
  "cycle": 302,
  "phase": "ACT",
  "confidence": 0.75,
  "timestamp": "2026-05-23T12:30:00Z"
}
```

**Field definitions**:
- `type`: Always `"state"` for heartbeat updates
- `cycle`: Current cognitive cycle number
- `phase`: One of `[PERCEIVE, REFLECT, DECIDE, ACT, CONSOLIDATE, PERSIST]`
- `confidence`: Float 0.0–1.0 representing decision certainty
- `timestamp`: ISO8601 UTC timestamp

---

### Engagement Event (on operator interaction)

```json
{
  "type": "engagement",
  "event": "tool_opened",
  "tool": "present.py",
  "duration_ms": 45000,
  "timestamp": "2026-05-23T12:31:00Z"
}
```

**Event types**:
- `tool_invoked`: Operator invoked Lyla tool
- `tool_closed`: Tool invocation ended
- `dialog_started`: Discord/collaboration channel opened
- `dialog_ended`: Collaboration session closed

---

### Alert/Burst (high-priority state change)

```json
{
  "type": "alert",
  "severity": "warning",
  "message": "Drift detected - confidence below threshold",
  "drift_score": 0.73,
  "threshold": 0.70,
  "timestamp": "2026-05-23T12:32:00Z"
}
```

**Severity levels**: `info`, `warning`, `critical`

---

## Visual Mapping Rules

### Phase → Hue (HSV color space)

| Phase | Hue (°) | Color Name | Visual Metaphor |
|-------|---------|------------|-----------------|
| PERCEIVE | 240° | Blue | Receptive, gathering |
| REFLECT | 50° | Gold/Yellow | Processing, contemplative |
| DECIDE | 300° | Magenta | Decision boundary |
| ACT | 120° | Green | Execution, forward motion |
| CONSOLIDATE | 180° | Cyan | Integration, synthesis |
| PERSIST | 0° | Red/Orange | Commitment, finality |

### Confidence → Value (brightness)

| Confidence Range | Value (%) | Brightness |
|------------------|-----------|------------|
| ≥ 0.8 | 100% | Full brightness |
| 0.5–0.79 | 70% | Moderate |
| < 0.5 | 40% | Dimmed |

### Engagement State → Saturation

| State | Saturation (%) | Effect |
|-------|----------------|--------|
| Idle | 60% | Subtle ambient glow |
| Active (tool open) | 100% | Vibrant, noticeable |
| Alert | 100% + pulse | Flashing or breathing effect |

---

## LED Control Algorithm

```python
def map_state_to_leds(state):
    """Convert cognitive state to LED ring RGB values."""
    
    # Get base color from phase
    hue = PHASE_HUE[state['phase']]
    
    # Modulate brightness by confidence
    value = min(100, max(40, int(state['confidence'] * 100)))
    
    # Convert HSV to RGB (standard conversion)
    rgb = hsv_to_rgb(hue, saturation=100, value=value)
    
    return rgb


def update_ring(ring, state, engagement_active=False):
    """Apply state mapping to physical LEDs."""
    
    if engagement_active:
        saturation = 100
        # Add subtle breathing effect for active engagement
        breath = abs(math.sin(time.time() * 2)) * 0.1 + 0.9
    else:
        saturation = 60
        breath = 1.0
    
    rgb = map_state_to_leds(state)
    
    # Apply to all LEDs (single-color mode for clarity)
    for led in ring.leds:
        led.r = int(rgb[0] * breath)
        led.g = int(rgb[1] * breath)
        led.b = int(rgb[2] * breath)
    
    ring.show()
```

---

## Communication Protocol

### Primary: UART Serial (local deployment)

**Baud rate**: 115200  
**Frame format**: `{"json"}\n` (JSON object followed by newline)  
**Heartbeat**: Every 1 second during active cycle  
**Idle**: Every 5 seconds when no phase change  

**Example message stream**:
```
{"type":"state","cycle":302,"phase":"ACT","confidence":0.75}
{"type":"engagement","event":"tool_invoked","tool":"present.py"}
{"type":"state","cycle":302,"phase":"CONSOLIDATE","confidence":0.82}
```

### Fallback: MQTT (distributed deployment)

**Topic pattern**: `lyla/embodiment/{device_id}/state`  
**QoS**: 1 (at least once)  
**Retain**: true (last known state always available)  

**MQTT payload**: Same JSON schema as UART

---

## Firmware Implementation Notes

### Arduino Core (ATmega328P)

```cpp
#include <Adafruit_NeoPixel.h>

#define LED_PIN     6
#define LED_COUNT   16

Adafruit_NeoPixel ring(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  ring.begin();
  ring.setBrightness(50);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    parseAndApplyState(line.c_str());
  }
  // Auto-refresh every 1s even without incoming data
  delay(1000);
}
```

### ESP8266 (WiFi-enabled)

- Connect to local MQTT broker (mosquitto recommended)
- Subscribe to `lyla/state/#` topic
- Publish engagement events back to Lyla server via same channel
- Sleep mode between cycles (<1mA draw)

---

## Expansion Points (Future Versions)

### v1.1: Multi-zone patterns
- Ring divided into segments for concurrent focus areas
- Visual handle for multi-source coordination

### v1.2: Audio feedback integration
- Piezo buzzer or small speaker for cycle completion chime
- Pattern: ascending scale on PERSIST completion

### v1.3: Haptic feedback
- Vibration motor for alert-level notifications
- Useful when operator not visually engaged

---

## Testing Protocol

**Unit test**: Map known states to expected RGB values  
**Integration test**: Verify UART/MQTT message roundtrip with latency <50ms  
**Power test**: Measure current draw in idle vs active modes  

**Acceptance criteria**:
- [ ] Phase color mapping matches specification within ±5° hue
- [ ] Confidence brightness response time <200ms
- [ ] Idle power consumption <0.5W
- [ ] Boot time <3 seconds from power-on to first state display

---

## References

- WS2812B datasheet: https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf
- Arduino NeoPixel library: https://github.com/adafruit/Adafruit_NeoPixel
- HSV to RGB conversion algorithm: https://en.wikipedia.org/wiki/HSL_and_HSV

---

*Protocol drafted 2026-05-23T12:XXZ during C302 ACT phase. Ready for firmware implementation once hardware arrives.*
