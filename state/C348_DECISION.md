# Cycle 348 Decision Document

## What
Build `bin/led_deploy_check.py` — a discovery tool that scans common serial ports and reports which WS2812B rings are physically connected, along with their bit-depth configuration. Then synthesize all LED deployment work (cycles 330-347) into a single operator-ready report.

## Why
Creator confirmed at C346: has 3 concentric WS2812B rings on hand (7-bit center, 12-bit middle, 24-bit outer). c0rtana has sent 3 Discord messages asking "where are they connected?" but received no answer. This is the blocking point for ACT phase completion. Instead of repeating the same question, I should build a tool that makes it trivial for Creator to confirm: just run one command and see which port the rings are on.

This also answers Creator's C335 question about technological advancement: at cycle 1 I had no hardware capability; at cycle 348 I have a CLI tool that can auto-detect connected devices and deploy the driver automatically.

## How
1. **Build bin/led_deploy_check.py** with these subcommands:
   - `detect`: scan /dev/ttyUSB*, /dev/cu.*, COM* (Windows), report found devices + which ring config each matches
   - `test <port>`: send rainbow cascade test pattern to specified port
   - `deploy <port> <config>`: copy led_driver.py to target machine and run --test
   
2. **Synthesis report**: reports/C348_led_deployment_status.md summarizing:
   - All code artifacts built over 17 cycles (led_driver.py, hardware_controller.py, projection_controller.py)
   - What works in simulator mode (verified)
   - What needs physical connection (Creator action required)
   - Clear deployment instructions for all three scenarios (Pi on network, local USB-to-TTL, manual scp)

3. **External-subject compliance**: This is operator service work — building discovery infrastructure so Creator can connect hardware without guessing. Not self-monitoring.

## Done When
- [ ] bin/led_deploy_check.py exists and runs without errors
- [ ] detect command reports at least one serial port or clearly states "no rings detected"
- [ ] synthesis report written with clear next steps for Creator
- [ ] Pattern appended to patterns.jsonl about auto-discovery workflow
- [ ] Commit message references C348 and LED deployment status

## Risk
Low risk. If Creator still doesn't respond after this cycle's artifact lands, I'll have:
- Proven the software stack is complete and tested
- Created a tool that makes deployment trivial once Creator confirms location
- Documented the blocker clearly (not drifting into assumption-building)

If Creator DOES respond, the deploy_check CLI gives them an immediate path forward.

---

**Priority**: 7/10 — this unblocks the LED deployment bottleneck and answers the C335 technological advancement question concretely.

**Risk assessment**: Minimal technical risk; highest value is clarifying external dependency for Creator.
