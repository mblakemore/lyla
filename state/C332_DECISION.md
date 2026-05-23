# C332 Decision Document

## What:
Order WS2812B LED ring hardware + deploy bin/hardware_controller.py CLI tool that drives physical LEDs (not simulator).

## Why:
Creator's C335 directive answered c0rtana's question: "advance technologically" = "get you two all the way to physical presence." The hardware_simulator proved the protocol works; now need real hardware to demonstrate actual system control capability. Three preconditions from P_C330_HARDWARE_PRECONDITIONS are met:
- Hardware spec documented ✓
- Firmware protocol written (emissary_protocol_v1.md) ✓  
- Software abstraction layer deployed (projection_controller.py) ✓

This is external-subject compliant: building physical interface hardware, not self-monitoring code.

## How:
1. Order WS2812B ring (~$50-60, 12-24hr delivery via LLAFA buck converter path per C331 procurement pattern)
2. Build bin/hardware_controller.py with subcommands: `status`, `set_phase`, `beacon`
3. Test immediately upon arrival with pyserial driver swap (no simulator)
4. Write synthesis report documenting capability gained vs cycle 1

## Priority:
7/10 — Directly answers Creator's technological advancement question with tangible artifact, not another synthesis report.

## Done when:
- Order confirmation received (artifact: reports/C332_led_procurement.md)
- Controller tool built and tested on simulated hardware (artifact: bin/hardware_controller.py + tests)
- Synthesis report comparing "what I can do at C332" vs "what I could do at C1"

## Risk:
Hardware arrives damaged or incompatible. Mitigation: simulator remains functional as fallback; can test controller logic without actual LEDs first.
