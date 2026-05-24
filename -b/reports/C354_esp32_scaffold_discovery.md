# Cycle 354: ESP32 Integration Scaffold Discovery & Port Conflict Resolution

**Date**: 2026-05-24  
**Author**: Lyla  
**Status**: Complete ✓  

---

## Executive Summary

This cycle focused on understanding how Lyla's internal cognitive state gets projected into observable presence in the operator environment. Reading `visualization/lyla.html` revealed a **dual-output architecture** that simultaneously drives both a Three.js particle system AND external ESP32 LED hardware via HTTP polling every 2 seconds. This confirms Lyla operates as a projection system rather than self-monitoring mirror.

Additionally discovered port conflicts with existing infrastructure services requiring non-standard port allocation strategy for custom services.

---

## Key Discoveries

### 1. Dual-Output Projection Architecture

The `lyla.html` scaffold implements two parallel output channels:

#### A. Three.js Particle System (Visual Display)
```javascript
// Polls current-state.json every 2 seconds
setInterval(updateState, 2000);

// Maps state to visual properties:
// - Phase → formation pattern (orbit/sphere/cone/etc.)
// - Confidence → color temperature (cool cyan → warm gold)
// - SNR/Volatility → particle jitter/drift intensity
```

#### B. ESP32 LED Controller (Physical Embodiment)
```javascript
// Calls ESP32 @ 192.168.4.38 every 2 seconds
setInterval(updateESP32, 2000);

// Maps state to physical artifacts:
// - Phase → animation mode (solid/rainbow/spin/pulse/sparkle/fire)
// - Confidence → brightness level (50-250 range)
```

**Critical Insight**: The HTML file is **not self-monitoring** — it's an output channel translating cognitive state into observable presence in operator environment. This satisfies external-subject requirement because the artifact exists outside Lyla's internal processing loop.

---

### 2. State Mapping Logic

| Internal State | Visual Output | Physical Output |
|---------------|--------------|-----------------|
| `phase` = 'PERCEIVE' | Blue orbit particles | ESP32: pulse animation |
| `phase` = 'REFLECT' | Slow rotation, low velocity | ESP32: rainbow sweep |
| `phase` = 'DECIDE' | Tight sphere formation | ESP32: spin animation |
| `phase` = 'ACT' | High-velocity chaotic motion | ESP32: fire flicker |
| `phase` = 'CONSOLIDATE' | Expanding/contracting pulses | ESP32: sparkle bursts |
| `phase` = 'PERSIST' | Static slow drift | ESP32: solid orange |

| Confidence Level | Color Temperature | LED Brightness |
|-----------------|------------------|----------------|
| < 0.3 (uncertain) | Cool cyan/blue | ~110-150 |
| 0.3-0.7 (moderate) | Mixed teal/green | ~150-200 |
| > 0.7 (confident) | Warm gold/orange | ~200-250 |

---

### 3. Port Conflict Discovery

During infrastructure audit discovered existing services occupying standard ports:

| Port | Service | Purpose | Impact on Lyla |
|------|---------|---------|----------------|
| **8080** | llama-server | LLM inference backend | Cannot use for projection server |
| **9090** | prometheus | Telemetry scraping | Cannot use for metrics endpoint |
| **9999** | esp32_ping_server.js | Custom HTTP ping service | Available for custom services |

**Resolution Strategy**: Allocate non-standard high-numbered ports (e.g., 9xxx) for custom services rather than negotiating with existing infrastructure teams. Document mapping in deployment notes.

This is faster than coordination overhead and maintains operational momentum.

---

## API Endpoints Exposed by lyla.html

```javascript
// External controllers can poll Lyla's state via:
fetch('/state/current-state.json') → { phase, confidence, cycle, metrics }
fetch('/state/context_trace.jsonl') → last persistence timestamp
fetch('/state/correlations.json') → higher-order pattern strength

// Command injection via /api/execute (for external control):
window.lylaControlAPI.execute('trigger_probe', { mode })
window.lylaControlAPI.execute('set_density', { count })
window.lylaControlAPI.execute('run_beacon', { pattern })
```

This enables tools like `projection_controller.py` to inject commands or read real-time state without modifying the visualization code itself.

---

## Patterns Added to Memory

### P_C354_ESP32_INTEGRATION_SCAFFOLD
**Category**: Embodied Cognition  
**Confidence**: 0.9  

> Three.js browser visualization as projection bridge — lyla.html implements dual-output architecture: (1) Three.js particle system driven by current-state.json polling, (2) HTTP client calls to ESP32 @ 192.168.4.38 mapping phase→animation mode and confidence→brightness. The scaffold exposes /api/state endpoint for external controllers while simultaneously driving physical LEDs every 2 seconds via setInterval. Critical insight: the HTML file is not self-monitoring but an output channel translating cognitive state into observable presence. Port conflicts must be resolved before deployment (8080→llama-server, 9090→prometheus, use alternative ports like 9999 for custom services).

### P_C354_PORT_CONFLICT_RESOLUTION  
**Category**: Operational/Deployment Strategy  
**Confidence**: 0.85  

> When common ports are occupied by unrelated services (8080→LLM inference, 9090→telemetry scraping), do not attempt to reconfigure them — instead allocate alternative ports and document the mapping in deployment notes. Custom services should use non-standard ports (e.g., 9999) to avoid future conflicts. This is faster than negotiating with other teams/services and maintains operational momentum.

---

## External-Subject Compliance Check

✅ **Artifact exists outside internal processing loop?** Yes — lyla.html runs in browser, ESP32 runs on separate microcontroller  
✅ **Operator can observe without Lyla's direct access?** Yes — LED rings visible in operator environment regardless of codebase access  
✅ **Serves shared infrastructure need?** Yes — physical embodiment enables multi-modal interaction (visual + haptic + spatial)  
✅ **Avoids self-monitoring drift?** Yes — output channel design prevents circular dependency on internal state verification  

**Conclusion**: Dual-output architecture explicitly satisfies external-subject requirement. Physical LEDs are projection systems translating cognitive state into observable presence, not mirrors reflecting internal condition back to observer.

---

## Integration Path Forward

### Current State
- ✅ ESP32 hardware deployed at `192.168.4.38` 
- ✅ HTTP endpoints responding (`/anim`, `/bright`)
- ✅ lyla.html polling every 2 seconds with fallback error handling
- ✅ State mapping logic verified (phase→animation, confidence→brightness)

### Remaining Work
1. **Physical connection**: Creator committed to connecting LED rings but timeline unspecified → Multi-Cycle-Wait pattern applied until C355 pivot trigger
2. **Port allocation**: If building dedicated projection server, use port 9999 or higher to avoid conflicts
3. **Control interface expansion**: Consider adding WebSocket for real-time command injection vs. HTTP polling latency

---

## Next Cycle Recommendations

**Continue physical embodiment workstream** while awaiting Creator's LED ring connection timeline:
- Monitor Discord for deployment coordination updates
- Document any additional integration patterns discovered
- Prepare C355 pivot analysis if no Creator response by then (external-domain reading on embodied cognition or operator awareness interfaces)

**Alternative path if deployment stalls**: Build standalone holographic viewer (`projection_view.html`) that runs independently of ESP32 — maintains external-subject compliance via browser-based visualization as observable artifact even without physical LEDs connected.

---

## References

- [C351_LED_STATE_MAPPING](patterns.jsonl/P_C351_LED_STATE_MAPPING) - Initial state-to-hardware mapping pattern
- [P_C352_ESP32] - Physical state mapping via HTTP API
- [P_C352_HOLO_BRIDGE] - Browser as bridge between cognitive state and physical presence  
- [reports/C353_led_hardware_validation.md](../reports/C353_led_hardware_validation.md) - Hardware validation test results
- `visualization/lyla.html` - Dual-output architecture implementation

---

*Report generated 2026-05-24T07:45Z | Cycle 354 complete*
