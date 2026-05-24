# C412 Decision Document

**What:** Read Creator's `quantum_work_report.txt`, synthesize findings into integration plan, build minimal IBM Quantum submission scaffold.

**Why:** 
- Creator explicitly shared existing quantum work (`/droid/repos/cl_shared/quantum_work_report.txt`) and invited Lyla to "put it together" in Discord message at 2026-05-24T19:06Z
- This produces external-subject artifact serving operator's financial experiment goals
- Aligns with P_C411 governance pattern: query existing documentation before implementing anything new
- Current state files stale (C409 vs actual C411) — need sync plus action on new directive

**How:**
1. PERCEIVE: Read `/droid/repos/cl_shared/quantum_work_report.txt` sections on QAE, QAOA, volatility patterns
2. ACT: Write synthesis report mapping Creator's 22-experiment arc to Lyla's current capabilities
3. ACT: Build `bin/ibm_quantum_submit.py` CLI with test mode (--test flag) and real-hardware submission capability
4. CONSOLIDATE: Append patterns for query-before-implement validation
5. PERSIST: Commit all artifacts + update current-state.json/focus.json to reflect C411→C412 transition

**Done when:**
- reports/C412_quantum_integration_plan.md created (synthesis of quantum work report + integration blueprint)
- bin/ibm_quantum_submit.py built and tested in simulator mode
- State files synced: current-state.json cycle=412, focus.json updated with next priorities
- All artifacts committed and pushed

**Priority:** 8/10 (Creator gave explicit directive; external-subject compliant artifact)

**Risk Mitigation:**
- Building scaffolding only, not full implementation — Creator will execute tests on their machine per Discord message
- Test mode (--test flag) allows development without exposing credentials
- Query-first approach prevents redundant discovery cycles
