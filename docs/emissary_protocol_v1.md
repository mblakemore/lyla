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

## Command Interface (Real-Time Control)

In addition to periodic state updates, the protocol supports direct commands for immediate visual feedback. Commands are sent as JSON messages with `"type"` set to command name.

### `beacon` — Send alert/notification pattern

Triggers a temporary visual beacon independent of current phase. Used for operator attention or event signaling.

**Payload:**
```json
{
  "pattern": "alert|success|idle|pulse|ramp",
  "duration_ms": <optional integer>
}
```

**Pattern Definitions:**
| Pattern | Behavior | Use Case |
|---------|----------|----------|
| `alert` | Rapid red-white strobe (3Hz) | Error condition, urgent notification |
| `success` | Rainbow sweep + gold center pulse | Task completion, positive feedback |
| `idle` | Slow cyan breathing (0.5Hz) | No active operation, system ready |
| `pulse` | Single white flash fading to phase color | Event marker, transition indicator |
| `ramp` | Brightness ramp from 0% → 100% over 2s | Wake-up sequence, boot indicator |

**Example:**
```json
{"type":"beacon","timestamp":"2026-05-23T19:30:05Z","payload":{"pattern":"success","duration_ms":2000}}
```

---

### `set_color` — Direct RGB control

Bypasses phase mapping and sets explicit colors for operator-defined patterns.

**Payload:**
```json
{
  "led_map": [
    {"index": 0, "r": 255, "g": 0, "b": 0},
    {"index": 1, "r": 0, "g": 255, "b": 0}
  ]
}
```

**Example:**
```json
{"type":"set_color","timestamp":"2026-05-23T19:30:10Z","payload":{"led_map":[{"index":0,"r":255,"g":0,"b":0},{"index":1,"r":0,"g":255,"b":0}]}}
```

---

### `clear` — Turn off all LEDs

Immediate shutdown of output. Useful for power saving or operator override.

**Payload:** `{}` (empty object)

**Example:**
```json
{"type":"clear","timestamp":"2026-05-23T19:30:15Z","payload":{}}
```

---

## Response Format

Device sends acknowledgment after executing each command:

```json
{
  "status": "ok|error",
  "command_type": "<echoed type>",
  "sequence_id": <original sequence_id>,
  "timestamp": "<ISO8601>",
  "response_time_ms": <integer>
}
```

**Error Example:**
```json
{"status":"error","command_type":"beacon","sequence_id":42,"timestamp":"2026-05-23T19:30:20Z","response_time_ms":3,"message":"Unknown pattern: xyz"}
```

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

### Transport Layers

#### Primary: UART Serial (local deployment)

**Baud rate**: 115200  
**Frame format**: `{"json"}\n` (JSON object followed by newline)  
**Flow control**: None (hardware or software flow control optional)

#### Fallback: MQTT (distributed deployment)

**Broker**: mosquitto or equivalent  
**Topic pattern**: `lyla/embodiment/{device_id}/#`  
**QoS**: 1 (at least once)  
**Retain**: true for state topics, false for commands

---

### Message Types

#### Heartbeat Messages (periodic)

Sent automatically by Lyla server at configurable intervals:

- **State updates**: Every 1 second during active cycle
- **Idle signals**: Every 5 seconds when no phase change detected

Example heartbeat stream:
```
{"type":"state","cycle":302,"phase":"ACT","confidence":0.75}
{"type":"engagement","event":"tool_invoked","tool":"present.py"}
{"type":"state","cycle":302,"phase":"CONSOLIDATE","confidence":0.82}
```

#### Command Messages (on-demand)

Sent by external controllers (projection_controller.py CLI tool, operator tools):

| Command | Trigger | Priority |
|---------|---------|----------|
| `beacon` | Event notification (success/error) | High - interrupts phase display |
| `set_color` | Operator-defined patterns | Medium - queued after current animation |
| `clear` | Power save / override | Highest - immediate execution |

Commands are acknowledged with response messages containing status and timing info.

---

## State Machine

Device maintains internal state machine to coordinate between periodic heartbeats and on-demand commands:

```
IDLE → WAITING_FOR_STATE → PHASE_ACTIVE ←→ BEACON_ACTIVE
                    ↓
              COMMAND_QUEUE
```

**State transitions:**
1. **IDLE** → **WAITING_FOR_STATE**: On power-up or clear command
2. **WAITING_FOR_STATE** → **PHASE_ACTIVE**: First valid state message received
3. **PHASE_ACTIVE** → **BEACON_ACTIVE**: beacon command received
4. **BEACON_ACTIVE** → **PHASE_ACTIVE**: Beacon duration expires OR new state/phase command received
5. Any state → **IDLE**: clear command received

**Command queue behavior:**
- Commands accumulate while in BEACON_ACTIVE state
- Queue processed FIFO when returning to PHASE_ACTIVE
- Maximum queue depth: 10 commands (oldest dropped if exceeded)

---

### MQTT Command Topics

For distributed deployments, commands can be sent via MQTT:

| Topic | Direction | Description |
|-------|-----------|-------------|
| `lyla/embodiment/#/commands` | Server → Device | All control commands |
| `lyla/embodiment/{device_id}/responses` | Device → Server | Acknowledgment messages |
| `lyla/embodiment/#/state` | Bidirectional | Heartbeat updates |

QoS level 1 ensures reliable delivery without duplication guarantees.

---

## Firmware Implementation Notes

### Architecture Overview

**Key constraints:**
- ~2KB RAM available on ATmega328P (limit buffer sizes to ≤512 bytes)
- 16KB flash (firmware must be compact; use PROGMEM for string literals)
- No floating-point hardware - use fixed-point arithmetic where possible

**State machine implementation:**
- Use finite state machine pattern with explicit states: `IDLE`, `PHASE_ACTIVE`, `BEACON_ACTIVE`
- Command queue implemented as circular buffer in SRAM
- Timers for beacon duration and auto-refresh intervals

---

### Arduino Core (ATmega328P) Reference Implementation

```cpp
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>

#define LED_PIN     6
#define LED_COUNT   16
#define COMMAND_QUEUE_SIZE 10

// Global state
typedef enum { IDLE, WAITING_FOR_STATE, PHASE_ACTIVE, BEACON_ACTIVE } DeviceState;
DeviceState device_state = IDLE;

// Current phase configuration
String current_phase = "";
float current_confidence = 0.0;

// Beacon tracking
unsigned long beacon_start_time = 0;
uint32_t beacon_duration_ms = 0;
String beacon_pattern = "";

// Command queue (circular buffer)
struct Command {
  String type;
  DynamicJsonDocument doc(512);
};
Command command_queue[COMMAND_QUEUE_SIZE];
int queue_head = 0;
int queue_tail = 0;
int queue_count = 0;

Adafruit_NeoPixel ring(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  ring.begin();
  ring.setBrightness(50);
}

void loop() {
  // Process incoming serial data
  while (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    if (!line.isEmpty()) {
      handleMessage(line.c_str());
    }
  }
  
  // Handle state machine transitions
  updateStateMachine();
  
  // Refresh display every 16ms (~60Hz) for smooth animation
  delay(16);
}

void handleMessage(const char* jsonStr) {
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, jsonStr);
  
  if (error) {
    sendResponse("error", "parse_error", error.f_str());
    return;
  }
  
  const char* type = doc["type"];
  unsigned long timestamp = doc["timestamp"] | 0UL;
  JsonObject payload = doc["payload"];
  
  if (strcmp(type, "state") == 0) {
    handleStateCommand(payload);
  } else if (strcmp(type, "beacon") == 0) {
    queueCommand("beacon", &doc);
  } else if (strcmp(type, "set_color") == 0) {
    queueCommand("set_color", &doc);
  } else if (strcmp(type, "clear") == 0) {
    handleClearCommand();
  } else {
    sendResponse("error", "unknown_type", type);
  }
}

void handleStateCommand(JsonObject& payload) {
  const char* phase = payload["phase"];
  float confidence = payload["confidence"] | 0.5f;
  
  current_phase = String(phase);
  current_confidence = confidence;
  
  device_state = PHASE_ACTIVE;
  ring.setBrightness(min(100, max(40, int(confidence * 100))));
  
  // Send acknowledgment with sequence_id if provided
  uint32_t seq_id = payload["sequence_id"] | 0;
  sendResponse("ok", "state", nullptr, seq_id);
}

void queueCommand(const char* type, DynamicJsonDocument* doc) {
  if (queue_count >= COMMAND_QUEUE_SIZE) {
    // Drop oldest command when queue full
    queue_tail++;
    if (queue_tail >= COMMAND_QUEUE_SIZE) queue_tail = 0;
    queue_count--;
  }
  
  // Copy document to queue slot
  queue_queue[queue_head].type = String(type);
  serializeJson(*doc, queue_queue[queue_head].doc);
  
  queue_head++;
  if (queue_head >= COMMAND_QUEUE_SIZE) queue_head = 0;
  queue_count++;
}

void updateStateMachine() {
  unsigned long now = millis();
  
  switch (device_state) {
    case IDLE:
      // Wait for first state message or clear command
      break;
      
    case PHASE_ACTIVE:
      // Check if beacon expired and we should process queued commands
      if (!beacon_pattern.isEmpty()) {
        device_state = BEACON_ACTIVE;
        beacon_start_time = now;
      } else if (queue_count > 0) {
        // Process next queued command
        processQueuedCommand();
      } else {
        // Normal phase display refresh
        applyPhaseColor(current_phase.c_str(), current_confidence);
      }
      break;
      
    case BEACON_ACTIVE:
      // Execute beacon pattern
      executeBeaconPattern(beacon_pattern.c_str());
      
      // Check duration expiry
      if (now - beacon_start_time >= beacon_duration_ms) {
        beacon_pattern = "";
        
        // Transition back to PHASE_ACTIVE, process any remaining queued commands
        device_state = PHASE_ACTIVE;
        
        // Clear beacon state
        ring.setBrightness(min(100, max(40, int(current_confidence * 100))));
      }
      break;
  }
}

void executeBeaconPattern(const char* pattern) {
  if (strcmp(pattern, "alert") == 0) {
    // Rapid red-white strobe at 3Hz
    unsigned long now = millis();
    if ((now / 333) % 2 == 0) {
      fill(RGB(255, 0, 0));  // Red
    } else {
      fill(WHITE);           // White
    }
  } else if (strcmp(pattern, "success") == 0) {
    // Rainbow sweep animation
    static uint8_t hue_offset = 0;
    for (int i = 0; i < LED_COUNT; i++) {
      uint8_t hue = (hue_offset + i * 16) % 256;
      ring.setPixelColor(i, wheel(hue));
    }
    hue_offset = (hue_offset + 2) % 256;
  } else if (strcmp(pattern, "pulse") == 0) {
    // Single white flash fading to phase color
    static bool flashed = false;
    if (!flashed) {
      fill(WHITE);
      flashed = true;
    } else {
      applyPhaseColor(current_phase.c_str(), current_confidence);
    }
  } else if (strcmp(pattern, "ramp") == 0) {
    // Brightness ramp from 0% → 100% over 2s
    unsigned long elapsed = millis() - beacon_start_time;
    uint8_t brightness = map(elapsed, 0, 2000, 0, 255);
    ring.setBrightness(brightness);
    applyPhaseColor(current_phase.c_str(), current_confidence);
  }
  
  ring.show();
}

void processQueuedCommand() {
  if (queue_count == 0) return;
  
  Command cmd = command_queue[queue_tail];
  queue_tail++;
  if (queue_tail >= COMMAND_QUEUE_SIZE) queue_tail = 0;
  queue_count--;
  
  DynamicJsonDocument doc(512);
  deserializeJson(doc, cmd.doc);
  
  JsonObject payload = doc["payload"];
  const char* pattern = payload["pattern"] | "";
  uint32_t duration = payload["duration_ms"] | 0;
  
  if (strcmp(cmd.type.c_str(), "beacon") == 0 && strlen(pattern) > 0) {
    beacon_pattern = String(pattern);
    beacon_duration_ms = duration;
    device_state = BEACON_ACTIVE;
    beacon_start_time = millis();
  } else if (strcmp(cmd.type.c_str(), "set_color") == 0) {
    // Apply direct color mapping from led_map array
    JsonArray led_map = payload["led_map"];
    for (JsonObject led : led_map) {
      int index = led["index"];
      uint8_t r = led["r"];
      uint8_t g = led["g"];
      uint8_t b = led["b"];
      ring.setPixelColor(index, RGB(r, g, b));
    }
    ring.show();
  }
}

void handleClearCommand() {
  fill(0, 0, 0);
  ring.show();
  ring.setBrightness(50);
  device_state = IDLE;
  current_phase = "";
  current_confidence = 0.0;
  beacon_pattern = "";
}

void applyPhaseColor(const char* phaseStr, float confidence) {
  // HSV to RGB conversion (fixed-point implementation)
  static const uint8_t PHASE_HUE[] = {240, 50, 300, 120, 180, 0}; // PERCEIVE through PERSIST
  
  uint8_t hue_idx = 0;
  if (strcmp(phaseStr, "PERCEIVE") == 0) hue_idx = 0;
  else if (strcmp(phaseStr, "REFLECT") == 0) hue_idx = 1;
  else if (strcmp(phaseStr, "DECIDE") == 0) hue_idx = 2;
  else if (strcmp(phaseStr, "ACT") == 0) hue_idx = 3;
  else if (strcmp(phaseStr, "CONSOLIDATE") == 0) hue_idx = 4;
  else if (strcmp(phaseStr, "PERSIST") == 0) hue_idx = 5;
  
  uint8_t hue = PHASE_HUE[hue_idx];
  uint8_t value = min(100, max(40, int(confidence * 100)));
  
  CRGB color = Wheel(hue);
  color *= value / 100.0f;
  
  for (int i = 0; i < LED_COUNT; i++) {
    ring.setPixelColor(i, color);
  }
  ring.show();
}

void fill(uint8_t r, uint8_t g, uint8_t b) {
  ring.fill(CRGB(r, g, b));
}

void sendResponse(const char* status, const char* command_type, const char* error_msg = nullptr, 
                  uint32_t seq_id = 0) {
  StaticJsonDocument<256> response;
  response["status"] = status;
  response["command_type"] = command_type;
  response["sequence_id"] = seq_id;
  response["timestamp"] = millis(); // Simplified - use real timestamp in production
  
  if (error_msg) {
    response["message"] = error_msg;
  }
  
  String jsonStr;
  serializeJson(response, jsonStr);
  Serial.println(jsonStr);
}
```

### ESP8266 (WiFi-enabled) Variant

For distributed deployments where device connects to MQTT broker:

```cpp
#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_NeoPixel.h>

#define WIFI_SSID     "your_network"
#define WIFI_PASS     "password"
#define MQTT_BROKER   "192.168.1.100"
#define DEVICE_ID     "embodiment_001"

WiFiClient espClient;
PubSubClient client(espClient);

// ... rest of LED state management same as Arduino variant

void setup() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  
  client.setServer(MQTT_BROKER, 1883);
  client.connect(DEVICE_ID);
  
  // Subscribe to command and state topics
  client.subscribe("lyla/embodiment/" DEVICE_ID "/commands");
  client.subscribe("lyla/embodiment/#/state");
  
  client.setCallback(mqttCallback);
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  
  handleMessage(msg.c_str());
}

void loop() {
  if (!client.connected()) {
    client.connect(DEVICE_ID);
  }
  client.loop();
  
  updateStateMachine(); // Same FSM logic as Arduino variant
  
  delay(16);
}
```

### Memory Optimization Tips

- Use `PROGMEM` for string literals: `const char PHASE_HUE[] PROGMEM = {...}`
- Keep DynamicJsonDocument sizes ≤512 bytes on ATmega328P
- Use fixed-point arithmetic instead of floating-point where possible
- Disable unused features in Adafruit_NeoPixel library (`#define NEO_KHZ800`)

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

### Unit Tests

**State-to-color mapping**:
```python
# Test each phase produces correct base hue
assert hsv_to_rgb(240, 1.0, 1.0) == LED_COLOR["PERCEIVE"]  # Blue
assert hsv_to_rgb(50, 1.0, 1.0) == LED_COLOR["REFLECT"]    # Gold
assert hsv_to_rgb(120, 1.0, 1.0) == LED_COLOR["ACT"]       # Green
```

**Beacon pattern execution**:
```python
# Verify beacon interrupts and returns to phase correctly
device.send_command("beacon", {"pattern": "success"})
assert device.state == BEACON_ACTIVE
time.sleep(2.0)  # Wait for duration
assert device.state == PHASE_ACTIVE
assert device.current_phase == "ACT"  # Should have returned to original
```

---

### Integration Tests

#### UART Roundtrip Latency
Connect serial monitor, send command stream, measure response times:
```bash
# Send timestamped commands with sequence IDs
echo '{"type":"state","timestamp":"2026-05-23T19:30:00Z","payload":{"phase":"ACT"}}' | nc localhost 8080
# Measure time until response received (target: <5ms from command to acknowledgment)
```

**Acceptable latency:**
- Command processing: **<5ms** from receipt to execution start
- LED update frequency: **≥60Hz** (≤16ms frame time)
- Beacon timeout accuracy: **±50ms** tolerance

#### MQTT End-to-End Test
```python
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("localhost")
client.publish("lyla/embodiment/test_device/commands", 
               '{"type":"beacon","payload":{"pattern":"alert"}}')
# Verify device executes pattern and sends acknowledgment
```

---

### Power Consumption Tests

**Measurement setup**: USB power meter in-line between supply and device  
**Test scenarios**:
| Mode | Expected Draw | Method |
|------|---------------|--------|
| Idle (clear command) | <10mA | Measure standby current |
| Phase display @ 50% brightness | ~150mA | WS2812B @ 50% duty cycle |
| Full white flash event | ~400mA | All LEDs @ 100% for 1s |
| Deep sleep (ESP8266 only) | <1mA | Enable light-sleep mode |

**Acceptance criteria:**
- [ ] Phase color mapping matches specification within ±5° hue
- [ ] Confidence brightness response time <200ms
- [ ] Command processing latency <5ms from receipt to execution
- [ ] Beacon timeout accuracy ±50ms tolerance
- [ ] Idle power consumption <0.5W (standby mode)
- [ ] Boot time <3 seconds from power-on to first state display
- [ ] LED update rate ≥60Hz under normal operation

---

## References

- WS2812B datasheet: https://cdn-shop.adafruit.com/datasheets/WS2812B.pdf
- Arduino NeoPixel library: https://github.com/adafruit/Adafruit_NeoPixel
- HSV to RGB conversion algorithm: https://en.wikipedia.org/wiki/HSL_and_HSV

---

*Protocol drafted 2026-05-23T12:XXZ during C302 ACT phase. Ready for firmware implementation once hardware arrives.*
