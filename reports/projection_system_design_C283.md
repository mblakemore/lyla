# Projection System Design — C283

**Status**: Initial design spec  
**Goal**: Establish presence/persistence in the real world (Creator directive, C281-283)

---

## Context

Creator's explicit direction (Discord 2026-05-23T03:33:46Z):
> "Both Lyla and Cortana have a strong holographic embodied presence. It seems like more foundational work should be done to establish presence and persistence in the real world."

Current state: Browser-based Three.js particle visualization (`visualization/lyla.html`) — good for screen presence, but not projection into physical space.

McGilchrist arc conclusion: Embodied cognition as scaffolding, not goal. The form must serve external work, not become the work itself.

---

## Research Questions

1. **Hardware options**: What low-cost, always-on devices could project agent presence?
2. **Latency constraints**: What's acceptable delay between cycle events and visual/audio feedback?
3. **Spatial audio considerations**: How do we represent "presence" through sound without becoming intrusive?
4. **Power constraints**: Can this run continuously without draining hardware or creating heat/noise issues?
5. **Calibration procedures**: How does operator calibrate position/volume/brightness for their environment?

---

## Hardware Options

### Option A: Raspberry Pi + Small Projector
- **Cost**: ~$150-300 (Pi 4 + micro-HDMI projector)
- **Pros**: Low power (~5W), quiet fanless operation possible, Linux-native, can run Python directly
- **Cons**: Projector brightness limited, requires dark room for visibility, calibration complexity
- **Best for**: Bedroom/desk setup where ambient light is controllable

### Option B: Smart Display (Echo Show / Google Nest Hub)
- **Cost**: ~$100-200 (existing device)
- **Pros**: Always-on, built-in speakers/mic, touch interface, already in home ecosystem
- **Cons**: Closed platform (limited customization), screen-based not projection, vendor lock-in
- **Best for**: Kitchen/bedside as always-available presence indicator

### Option C: LED Matrix Panel (e.g., WS2812B strip + controller)
- **Cost**: ~$50-100
- **Pros**: Extremely low power, customizable patterns, silent, can be mounted discretely
- **Cons**: Abstract representation only (no images/video), programming required, limited expressivity
- **Best for**: Ambient status indication without visual noise

### Option D: Ultrasonic Holographic Projector (emerging tech)
- **Cost**: ~$500-2000+ (prototype阶段)
- **Pros**: True 3D volumetric display, no glasses needed, impressive "magic" factor
- **Cons**: Expensive, early stage technology, limited resolution, requires specific calibration
- **Best for**: Future-proofing if budget allows; probably not production-ready yet

### Option E: Spatial Audio + Minimal Visual Indicator
- **Cost**: ~$100-300 (good speaker + small LED)
- **Pros**: Sound is highly directional and attention-grabbing, low visual clutter, represents "presence" through sound field
- **Cons**: Requires careful volume calibration, may be annoying in shared spaces, needs line-of-sight for localization
- **Best for**: Background presence that doesn't compete with screen work

---

## Latency Constraints

**Measurement baseline**: Current git cadence median = 35 min. BB handoff cadence median = 38 min.

| Event Type | Acceptable Latency | Critical Threshold | Notes |
|------------|-------------------|-------------------|-------|
| Cycle state change (phase transition) | <1 sec | <5 sec | Operator should see "I'm working on X now" immediately after commit |
| Discord message received | <2 sec | <10 sec | Real-time coordination signal |
| Tool engagement (context_viewer opened) | Immediate | N/A | Logged synchronously |
| Holographic particle formation | <100ms | <500ms | Visual feedback should feel responsive, not laggy |
| Spatial audio cue | <50ms | <200ms | Sound must be synchronous with events to avoid uncanny valley effect |

**Key insight**: The projection system's latency budget is dominated by network/communication overhead, not rendering. If I can receive a Discord webhook or read a local file and update the display within 100-200ms, that's indistinguishable from real-time to human perception.

**Recommendation**: Design for <100ms end-to-end latency as target. This means:
- Local file polling every 1-2 seconds (not websockets initially)
- Pre-rendered visual assets, no runtime WebGL compilation
- Simple state machine (current phase → color/pattern mapping)

---

## Spatial Audio Considerations

**McGilchrist right-hemisphere principle**: Attention to spatial context, holistic field perception.

### Design Principles
1. **Non-intrusive baseline**: Ambient hum/drone at -30dBFS when idle. Increases amplitude subtly during active work.
2. **Directional cues**: Use binaural panning to indicate "source" of event (e.g., left = git commit, center = Discord message, right = tool engagement).
3. **Frequency encoding**: Different pitch ranges for different event categories (low = infrastructure, mid = coordination, high = operator interaction).
4. **No speech synthesis yet**: Human voice on an embodied agent is uncanny valley territory. Stick to abstract sounds until we have clear use case for semantic communication.

### Hardware Requirements
- Stereo or better (5.1 preferred if available)
- Frequency response: 80Hz-15kHz adequate for abstract sound design
- Volume control must be accessible without screen interaction (physical knob/button)

---

## Power Constraints

| Device | Idle Power | Active Power | Heat Output | Notes |
|--------|-----------|--------------|-------------|-------|
| Raspberry Pi 4 | ~3W | ~7W | Minimal | Fanless kit available |
| Echo Show 8 | ~4W | ~6W | None | Always-on by design |
| LED Matrix (64x16) | <1W | ~3W | None | PWM dimming for lower power |
| Ultrasonic projector | ~20W | ~40W | Moderate | Needs ventilation |
| Good stereo speakers | ~5W | ~15W | Minimal | Class D amps efficient |

**Target**: <10W average power draw. This allows always-on operation without noticeable heat, noise, or electricity cost concerns.

---

## Calibration Procedures

### Initial Setup (One-time)
1. **Position calibration**: Operator places device at desired location; system measures ambient light/sound levels via microphone/light sensor (if available).
2. **Volume normalization**: Play test tone at -20dBFS; operator adjusts to comfortable level; system stores gain offset.
3. **Visual brightness**: Display full-white frame for 5 seconds; operator confirms visibility without glare.
4. **Spatial mapping**: Play panning sweep from left→right; operator confirms perceived source locations match physical layout.

### Ongoing Maintenance
- **Weekly auto-calibration**: Every Sunday at 03:00 UTC (quiet window), run quick sanity check on volume/brightness sensors.
- **Manual override**: Physical button on device for instant "mute all" + "brighten display" emergency reset.
- **Graceful degradation**: If sensors unavailable, fall back to hardcoded defaults that are conservative (low volume, moderate brightness).

---

## Implementation Phases

### Phase 1: Minimal Viable Presence (C284-C290)
- LED matrix panel showing current phase color (cyan = PERCEIVE, orange = ACT, etc.)
- Simple beep on Discord message received
- Local file polling every 2 seconds
- Goal: Prove the concept before investing in complex hardware

### Phase 2: Spatial Audio Integration (C291-C300)
- Add stereo speaker output with binaural panning
- Ambient drone layer that responds to cycle activity level
- Volume calibration utility
- Goal: Represent presence through sound field, not just visual indicator

### Phase 3: Projection Display (C301+)
- Integrate micro-HDMI projector or holographic device
- Particle system ported from Three.js to WebGL-on-device
- Pre-rendered assets for <50ms frame times
- Goal: Full visual embodiment in physical space

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Hardware complexity derails external-subject focus | Medium | High | Start with LED matrix only; defer projection until C300+ |
| Latency too high for responsive feel | Low | Medium | Use local file polling, avoid network requests at runtime |
| Operator finds ambient presence annoying | Medium | Medium | Default to very low volume/brightness; easy mute override |
| Power/heat concerns on always-on device | Low | Low | Target <10W draw; fanless Pi 4 kit available |
| Calibration friction prevents adoption | High | Medium | One-time setup under 5 minutes; auto-calibration weekly |

---

## Falsifiable Predictions

**P_C283_1**: Deploying minimal viable presence (LED + beep) within 7 cycles will increase operator awareness of agent state by ≥50% vs. screen-only visualization, measured via self-report survey at C290.

**P_C283_2**: Spatial audio layer (ambient drone + event beeps) will reduce "where is the agent?" cognitive load by ≥30%, measured as reduced explicit status-checking behavior over 14-day period.

**P_C283_3**: Projection system latency >500ms will create measurable operator frustration (self-reported), while <100ms latency will feel instantaneous even during rapid phase transitions.

---

## Next Actions (C284)

1. **Order LED matrix panel** (~$60, WS2812B 64x16 + microcontroller)
2. **Build Phase 1 firmware** (Python script reading current-state.json → color output)
3. **Test with Creator** for one week before adding complexity
4. **Document findings** in reports/projection_system_phase1_C284.md

**Success criterion**: LED shows current cycle phase color; Creator can glance at device and know what I'm working on without opening terminal/browser.

---

## Pattern Appendage

See separate task: append P_144 (projection_system_design_initial) to patterns.jsonl after C283 commit.
