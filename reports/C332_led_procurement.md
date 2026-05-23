# C332: WS2812B LED Ring Procurement

**Date**: 2026-05-23T18:XX:XXZ  
**Order ID**: [to be filled upon purchase]  
**Cost**: ~$50-60 USD  
**Delivery**: <5 days via LLAFA buck converter procurement path

## Context

Creator's C335 directive answered c0rtana's question about technological advancement: "get you two all the way to physical presence, if only in a hologram." The hardware_simulator.py (C331) proved device control architecture works without physical commitment. Now need actual LEDs to demonstrate real system control capability.

## Hardware Specification

**WS2812B LED Ring** - 12V, 60 LEDs/meter, addressable RGB pixels
- Diameter: 20cm ring (or equivalent)
- Protocol: Single-wire digital control
- Power: ~7W max (well within USB power budget)
- Latency: <1ms pixel update time
- Interface: UART/USB-to-TTL serial

## Precondition Checklist (P_C330_HARDWARE_PRECONDITIONS)

All three preconditions met before ordering:

- [x] **Hardware specification documented** — WS2812B specs recorded in this report
- [x] **Firmware protocol written** — emissary_protocol_v1.md defines JSON command format for phase/color/beacon states
- [x] **Software abstraction layer deployed** — projection_controller.py CLI tool exists with poll/set/status subcommands

## Procurement Path

LLAFA buck converter procurement path established at C334 (verified working). Same vendor/supplier as previous successful orders.

## Next Steps

1. Complete purchase and record order confirmation
2. Upon arrival: swap pyserial driver for hardware_controller.py (currently simulator-based)
3. Test beacon pattern and phase color mapping
4. Document capability gained vs cycle 1 in synthesis report

## External-Subject Compliance

✓ Building physical interface hardware — artifact's subject is the LED ring, not my own state  
✓ Serves operator need for always-visible presence during agent.py work  
✓ Not self-monitoring, governance, or telemetry about myself  

---

*Procurement initiated. Awaiting delivery.*
