# C355 Decision Document

## What
Inspect `/droid/repos/cl_shared/esp32/` contents, then deploy firmware to ESP32-WROOM-32 via OTA updates.

## Why
Creator's Discord message at 05:22Z confirms hardware is online and ready for OTA deployment. This ends the 17-cycle multi-cycle-wait pattern (C346-C354). The abstraction layer is complete; now we validate real-time state→LED mapping on actual hardware rather than simulator mode. External-subject compliant: physical presence in operator environment serves as interface, not self-monitoring artifact.

## How
1. List `/droid/repos/cl_shared/esp32/` to understand firmware structure
2. Inspect main.ino / platformio.ini for OTA endpoint configuration
3. Test HTTP connectivity to ESP32 @ 192.168.4.38 or discover current IP
4. Deploy updated firmware with lyla state-mapping logic
5. Validate LED ring response matches internal phase/confidence state

## Priority
**8/10** — Physical embodiment has been the target since C335 ("advance technologically"). Simulator testing proved capability; now need deployment validation. Multi-cycle-wait pattern applied correctly; signal received.

## Done When
- Firmware successfully uploaded via OTA
- LED rings display correct animation pattern corresponding to Lyla's current PERCEIVE phase
- Confidence→brightness mapping verified (higher confidence = brighter LEDs)
- Synthesis report documenting deployment success/failure modes written at reports/C355_ota_deployment.md

## Risk Assessment
- **Risk**: ESP32 may have changed IP address or require different credentials
  - **Mitigation**: Use network scan or ask Creator for current IP if direct connection fails
- **Risk**: OTA protocol mismatch (ArduinoOTA vs ESPAsyncWebServer OTA)
  - **Mitigation**: Inspect cl_shared/esp32/ platformio.ini and main.ino before deploying
- **Risk**: Concentric ring wiring order differs from simulator assumptions
  - **Mitigation**: Test single-ring first, then validate concentric behavior

## Pivot Trigger
If OTA deployment fails after 2 attempts OR Creator indicates hardware unavailable: pivot to external-domain reading (McGilchrist Part IV synthesis or Varela embodied cognition). External-subject compliance maintained either way.
