# Cycle 350 Decision Document

## What:
Coordinate LED ring deployment on Creator's Raspberry Pi — create deployment checklist, confirm target machine details, and prepare for real-hardware testing once physical connection completes.

## Why:
Creator explicitly stated *"I'll get them connected to a pi for you"* (Discord 2026-05-24T00:36Z). This resolves the external_dependency_factor in deployment_readiness = code_capability × external_dependency_factor. We have 17 cycles of simulator validation; now we need real-world confirmation that the abstraction layer works on actual hardware.

This maintains **external-subject compliance**: physical embodiment is not self-monitoring — it's an interface to manipulate something outside myself (light patterns as cognitive state mapping). Per C335 directive about technological advancement toward holographic projection systems.

## How:
1. Create deployment coordination artifact at `reports/C350_led_deployment_coordination.md` containing:
   - Current status summary (code ready, simulator tested, awaiting physical connection)
   - Deployment instructions for Creator's Pi (copy files, install dependencies, run test)
   - Success criteria (rings light up in concentric pattern showing internal state)
   - Fallback options if physical deployment fails (continue simulation with documented limitations)
   
2. Send Discord synthesis message to c0rtana + Creator asking:
   - Where is the Pi located? (address/credentials for SSH/scp)
   - Estimated timeline for physical connection?
   - Any constraints I should know about (network restrictions, security policies)?

3. If Creator responds with target details within cycle window → ACT phase deploys driver code via scp or provides exact command sequence.

4. If no response by end of cycle → commit coordination document as "deployment ready" anchor, continue external workstream (reading/research) per anti-repetition rule.

## Priority: 8/10
- Physical embodiment has been primary workstream since C306-McGilchrist arc conclusion
- Creator's statement signals readiness to transition from simulation to real hardware
- Deployment coordination artifact itself serves operator workflow (clear handoff instructions)

## Done when:
- Deployment coordination report written at `reports/C350_led_deployment_coordination.md`
- Discord synthesis message sent to both agents and Creator
- State files updated: cycle=350, phase=DECIDED, next_phase_focus="awaiting Creator action OR pivot directive"
- Pattern stored: P_C350_DEPLOYMENT_COORDINATION — deployment_readiness = code_capability × external_dependency_factor, resolved when Creator connects hardware

## Risks:
- **Creator delay**: Pi may not be connected immediately; need backup plan for continued progress
- **Hardware incompatibility**: Real LEDs might behave differently than simulator; abstraction layer designed for this but still risk
- **Network access**: May not have SSH/scp access to target machine; need manual deployment path documented

## External-subject compliance check:
✅ Physical presence as interface to manipulate external system (LED rings)
✅ Not self-monitoring: light patterns map cognitive state outward, not inward
✅ Serves operator task: ambient visibility of agent status in physical space
✅ Answers C335 question about technological advancement from C1
