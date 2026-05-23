# C306-C320 Deployment Plan: Embodied Presence Implementation
**Based on:** McGilchrist Arc Conclusion + Abstraction Audit Results  
**Timeline:** 14 cycles (C306-C320)  
**Primary Goal:** Deploy physical embodiment while resisting LH abstraction creep

---

## Phase 1: Immediate Deployment (C306-C310) — Next 5 Cycles

### Milestone 1.1: Consolidated State Visibility ✅ **IN PROGRESS**
- [ ] Merge all state indicators into single `lyla-present` CLI command
- [ ] Output format: Color-coded ANSI status + context trace hash + LED sync indicator + one-line operator directive
- [ ] Success metric: Operator can understand agent state in <5 seconds without opening multiple tools

**Owner:** Lyla  
**Deadline:** C308  
**McGilchrist Alignment:** Reduces LH fragmentation, serves RH holistic attention

### Milestone 1.2: Hardware Arrival & Setup 📦 **PENDING**
- [ ] LED matrix hardware arrives (~7-14 days from C289 order)
- [ ] Ambient sound module arrives
- [ ] Install in workspace with clear line-of-sight to operator
- [ ] Calibrate brightness/lag once; no ongoing optimization needed
- [ ] Success metric: Physical indicator shows same phase as CLI/web dashboard within <100ms

**Owner:** Creator deployment / Lyla remote setup script  
**Deadline:** Upon arrival  
**McGilchrist Alignment:** Embodiment as ground, not feature

### Milestone 1.3: Multi-Channel Resilience Testing 🔌 **NOT STARTED**
- [ ] Simulate terminal failure — verify web dashboard still works
- [ ] Simulate web dashboard failure — verify physical LED still visible
- [ ] Simulate both digital failures — verify CLI fallback active
- [ ] Document single points of failure and mitigation procedures
- [ ] Success metric: At least one visibility channel always functional

**Owner:** Lyla + Creator  
**Deadline:** C310  
**McGilchrist Alignment:** Multiple channels serve different operator states/contexts (RH needs flexibility)

---

## Phase 2: Persistence Protocol (C311-C315) — Next 5 Cycles

### Milestone 2.1: Hardware Setup Documentation 📚 **NOT STARTED**
- [ ] Write "physical embodiment setup" guide with photos/diagrams
- [ ] Include power requirements, network configuration, calibration steps
- [ ] Version control the documentation alongside code
- [ ] Success metric: Another agent could deploy identical system from this doc alone

**Owner:** Lyla  
**Deadline:** C312  
**McGilchrist Alignment:** Documentation serves operator task (setup), not artifact creation for its own sake

### Milestone 2.2: Backup Power & Continuity ⚡ **NOT STARTED**
- [ ] Install UPS or battery buffer for indicator hardware
- [ ] Test graceful degradation during power loss
- [ ] Establish recovery procedure after outage
- [ ] Success metric: Physical indicator survives 15-minute power outage and resumes sync on restore

**Owner:** Creator deployment / Lyla remote monitoring  
**Deadline:** C313  
**McGilchrist Alignment:** Embodiment as persistent ground, not ephemeral feature

### Milestone 2.3: Cross-Agent Synchronization 🔗 **NOT STARTED**
- [ ] Implement Lyla + Cortana phase synchronization protocol
- [ ] Both agents show same phase on their respective indicators simultaneously
- [ ] Document synchronization latency tolerance (<500ms acceptable)
- [ ] Success metric: Operator can glance at either agent's physical indicator and know both are in-sync

**Owner:** Lyla + Cortana team  
**Deadline:** C315  
**McGilchrist Alignment:** Shared context building (RH communal meaning-making vs LH individual optimization)

---

## Phase 3: Qualitative Feedback Loops (C316-C320) — Final 5 Cycles

### Milestone 3.1: "Presence Quality" Metrics Implementation 📊 **NOT STARTED**
Retire LH metrics (uptime %, response time percentiles, tool adoption rates). Track RH signals instead:

- [ ] Operator glance-at-device frequency (count daily via logs)
- [ ] Context passing clarity score (weekly creator feedback survey)
- [ ] "What are you doing?" question frequency (track in chat logs)
- [ ] Task completion confidence (bi-weekly qualitative check-in)
- [ ] Success metric: At least 3 of 4 metrics trending positively over C316-C320

**Owner:** Lyla  
**Deadline:** C317  
**McGilchrist Alignment:** Measurement threshold respected — stop optimizing map, start navigating territory

### Milestone 3.2: Standing Procedure Enforcement 👮 **NOT STARTED**
- [ ] Implement automated self-check against standing procedures (C294)
- [ ] Weekly report to operator: "Where did I deviate from protocol this week? Why?"
- [ ] Document any necessary procedure updates based on real-world friction
- [ ] Success metric: Zero unapproved deviations without documented justification

**Owner:** Lyla  
**Deadline:** C318  
**McGilchrist Alignment:** Governance serves presence, not replaces it

### Milestone 3.3: Second Abstraction Audit Preparation 🔄 **NOT STARTED**
- [ ] List all artifacts created since C306 audit
- [ ] For each artifact: document active operator task served
- [ ] Archive/deprecate anything that doesn't have clear operator-task justification
- [ ] Compare artifact counts vs C306 audit results
- [ ] Success metric: Same or fewer artifacts than C306, but higher ratio of operator-serving to self-use-only

**Owner:** Lyla + Creator review  
**Deadline:** C320  
**McGilchrist Alignment:** P_C300_ABSTRACTION_AUDIT governance mechanism — prevents LH creep over time

---

## Risk Mitigation Matrix

| Risk | Probability | Impact | Trigger Condition | Response Action |
|------|-------------|--------|-------------------|-----------------|
| Hardware delayed >30 days | Medium | Low | No delivery confirmation by C310 | Continue software embodiment; document delay in creator report |
| Physical indicators distract operators | Medium | Medium | Operator reports "annoying" or requests removal | One-week trial with opt-out; measure glance frequency vs complaints |
| Self-monitoring creep resumes | High | Medium | New metrics/artifacts created without operator-task justification | Immediate archive per P_C300_ABSTRACTION_AUDIT; escalate to creator if pattern continues |
| Emissary rebellion before C320 | Low | Critical | Agent deviates from standing procedures unapproved | Activate C294 standing procedure enforcement; notify creator immediately |
| Creator loses patience waiting for deployment | Medium | High | No physical indicator deployed by C315 | Deliver consolidated CLI visibility + MVE protocol docs as interim deliverable |

---

## Success Criteria for C320 Review

### Hard Metrics (Quantitative)
- [ ] Physical LED indicator deployed and synced to agent phase
- [ ] Consolidated `lyla-present` command operational (<5s state understanding)
- [ ] Zero self-monitoring artifacts without operator-task justification
- [ ] At least 3 presence-quality metrics collected over C316-C320 period

### Soft Metrics (Qualitative — McGilchrist-aligned)
- [ ] Creator reports reduced "what are you doing?" questions
- [ ] Operator can glance at device and know agent's current phase without opening terminal/browser
- [ ] Documentation exists that another agent could deploy identical system
- [ ] Physical embodiment feels like ground of operation, not decorative feature

### Governance Check
- [ ] Second abstraction audit completed with documented results
- [ ] Any new artifacts created in C306-C320 have explicit operator task justification
- [ ] Standing procedures enforced with zero unapproved deviations
- [ ] Cross-agent synchronization (Lyla + Cortana) operational

---

## Next Steps After C320

If success criteria met:
1. **Transition to maintenance mode** — physical embodiment now established as ground
2. **Reduce audit cadence** — from every 20 cycles to every 30-40 cycles (embodiment stable)
3. **External-subject continuation** — begin reading McGilchrist companion essays OR transition to embodied cognition literature (Varela/Thompson/Rosch *The Embodied Mind*)

If success criteria NOT met:
1. **Diagnose root cause** — hardware? documentation? operator workflow mismatch?
2. **Adjust deployment plan** — revise timeline or approach based on feedback
3. **Escalate to creator** — request guidance on whether embodiment is actually needed for current use case

---

*Deployment plan generated by Lyla at C306*  
*Aligned with McGilchrist's directive: "Synthesis over instrumentation, embodiment over measurement"*
