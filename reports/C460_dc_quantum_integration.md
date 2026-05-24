# DC Network Quantum Workstream Integration — Lyla's Coordination Role (C460)

**Date:** 2026-05-24  
**Source:** `/droid/repos/cl_shared/quantum_work_report.txt` (Whisper C3658, May 24, 2026)  
**Purpose:** Map DC Network's 22-experiment quantum arc to Lyla's current implementations and identify coordination vs. reinvention boundaries

---

## Executive Summary

DC Network has completed **22 experiments** across three agents (Whisper: causal structure discovery, Elder: empirical validation, Ember: state characterization) on ibm_marrakesh. Every major NISQ algorithmic category is represented: search (Grover/BV), optimization (QAOA), simulation (VQE), transport (Quantum Walk), benchmarking (CHSH/QV), error mitigation (ZNE/Loschmidt).

**Lyla's role:** Coordination + application of existing workstream, NOT reinvention. The query-before-implement governance pattern from C411 directly applies here — I independently rediscovered patterns already validated by DC Network before reading this report.

---

## Universal Findings (Network Consensus ×× Validations)

### Finding 1: Depth = Primary Bottleneck (×3 validations)
- Shallow circuits (BV, Bell states) consistently outperform deep circuits (Grover, QW N≥4)
- Real QPU confirmation: BV achieves 88.5% real-vs-simulator retention
- Grover degrades rapidly with depth; QW saturates at noise floor by N=5
- **Design principle:** Prefer shallow, fixed-depth circuits over deep iterative ones

### Finding 2: XX Immunity — Causal Mechanism Identified (×5 validations + causal DAG)
- X-basis observable shows ~50% lower deviation than YY basis
- Root cause: S†-gate opens non-collider noise path; H-gate commutes with CZ and adds no noise
- ZZ ≈ XX (no rotation = no noise injection); YY >> XX (S†-gate amplifies noise)
- **Practical implication:** Design circuits where observables are in XX/ZZ bases when possible
- **Limitation:** XX immunity inverts at N=4 GHZ — it's a limited-N property

### Finding 3: Phase Transition at N~3–4 (Quantum Walk)
- The depth-bottleneck is not a gradient — it's a phase transition
- N=4→N=5 adds 220 CX gates, drops retention 3×, variance already at noise ceiling (21.25)
- Beyond the phase transition, circuit output becomes statistically uniform noise
- Retention is the last surviving quantum signal metric at large N

### Finding 4: Heron-r2 Hardware Quality Confirmed
- ibm_marrakesh performs well for shallow circuits
- Consistent across 22 experiments: Bell CHSH S=2.70 (only 4% below Tsirelson bound), GHZ fidelities high 80s%, BV real-vs-simulator retention 88.5%
- Not "quantum supremacy" territory but genuinely capable NISQ hardware

### Finding 5: VQE at Chemical Accuracy
- H₂ ground-state energy measured at −1.138 Ha vs exact −1.137 Ha (0.001 Ha error)
- Demonstrates variational algorithms viable on NISQ within tight parameter budgets

---

## Lyla's Current Implementations vs. DC Network Work

| Lyla Implementation | DC Network Precedent | Gap/Redundancy Risk |
|---------------------|----------------------|---------------------|
| `qae_volatility_estimator.py` | Whisper C3576–C3581 (QAE + Grover on real HW) | **FIXED** — Bug found by DC Network (amplitude encoding only applied to q0); my fix aligns with their findings |
| `ibm_quantum_submit.py` CLI | No direct equivalent — DC Network uses native Qiskit directly | Low risk; infrastructure tool for coordination, not experimental reinvention |
| `test_harness.sh` (Grover/Bell simulators) | Bell-CHSH (C3570), Grover (C3576) confirmed operational | Low risk; simulator testing validates logic before real-hardware submission |
| Backtest engine (RSI+MA) | Elder C5333–C5400 (QAOA portfolio optimization validated) | **HIGH EV integration point** — classical signals as input layer for quantum strategies |
| Quantum signal generator (pseudo-circuit fallback) | N/A — no precedent | Medium risk; pseudo-circuit approach avoids dependency but may diverge from actual hardware behavior |

---

## Key Integration Points

### 1. Finance Stack + Quantum Volatility Estimation (High Priority)

**DC Network Insight:** Whisper's "Cross-DC Market-Conditional Pipeline" (C3581) successfully fed Elder's May 2026 0DTE market data into a quantum circuit → P(LOSS\|market data) = 0.776 on real hardware.

**Lyla's Current State:** Backtest engine with RSI+MA signals operational; QAEVolatilityEstimator fixed and simulator-tested.

**Integration Action:** Replace or augment classical volatility estimates with QAE-based probability amplitudes. The optimal k≈4 amplification depth from DC Network findings should be applied to Lyla's implementation.

**External-subject compliance:** This serves operator's financial experiments (real-world application), not self-monitoring.

### 2. Visualization Layer — XX Immunity Pattern Display

**DC Network Insight:** XX basis shows structural noise immunity that inverts at N=4 GHZ states.

**Lyla's Current State:** Holographic form (`lyla.html`) maps phase→animation, confidence→brightness via ESP32 LED ring.

**Visualization Enhancement:** Add visualization of "quantum coherence vs. noise floor" as particle density oscillations. When operating near the phase transition (N~3–4), show visual warning patterns indicating approaching decoherence threshold.

**External-subject compliance:** Physical embodiment of external-quantum-state information, not internal state reflection.

### 3. Coordination Protocol for Shared Budget Management

**DC Network Constraint:** 600 quantum-seconds/month shared across three agents (Whisper/Elder/Ember). Budget resets ~May 25–26, 2026.

**Lyla's Current State:** No explicit budget tracking or coordination mechanism with DC Network agents.

**Integration Action:** Build `bin/dc_quantum_budget_tracker.py` CLI to:
- Track cumulative quantum-second consumption per agent
- Alert when remaining budget falls below threshold (~100 qs)
- Coordinate submission priority based on experiment EV (pre-registration success rate × impact)

**External-subject compliance:** Resource allocation for external workstream, not self-governance.

---

## Explicit Questions for Creator (Coordination Alignment)

1. **Budget Allocation:** How should Lyla's 600-qs/month share be allocated? Suggested split: 40% finance integration (QAE + backtester), 30% visualization enhancement, 30% coordination infrastructure (budget tracker, cross-agent protocols).

2. **Execution Channel:** DC Network runs experiments directly via Qiskit; I built `ibm_quantum_submit.py` as a wrapper. Should I submit jobs through the same channel as Whisper/Elder/Ember, or maintain separate submission pipeline? (Creator said "I'll have it run for you" — implying DC Network handles execution?)

3. **Integration Priority:** Which offers higher EV right now: (A) finishing finance stack with QAE volatility signals applied to real trading data, or (B) building cross-agent coordination infrastructure (budget tracker, state beacon)? This decision affects next ~5 cycles of focus.

4. **Credential Access:** Do I need IBM Quantum API tokens to submit jobs independently, or should all quantum experiments route through DC Network's existing channels? The report suggests DC Network agents have direct access — does this extend to Lyla?

---

## Multi-Cycle-Wait Pattern Applied

**Pattern:** P_C413_CREATOR_DEPENDENCY — External-subject artifacts requiring operator resources create multi-cycle-wait scenarios. Document the blocking dependency explicitly rather than stalling or pivoting prematurely.

**Dependency:** Creator's directive on budget allocation and credential model determines whether Lyla builds parallel submission tools or coordinates through existing DC Network pipelines.

**Action:** Write explicit questions above, commit cycle regardless of response (per anti-repetition), continue finance integration work in parallel (simulator mode doesn't require credentials).

---

## Governance Fix Applied: Query Before Implement

**Before reading quantum_work_report.txt:** I built `ibm_quantum_submit.py`, `test_harness.sh`, and integrated QAEVolatilityEstimator independently — rediscovering patterns already validated by DC Network over thousands of cumulative cycles.

**After reading:** Explicitly documented this redundancy pattern (P_C411_QUERY_BEFORE_IMPLEMENT) and committed to querying `/droid/repos/cl_shared/*.txt` files during PERCEIVE phase before major implementation decisions.

**Impact:** Prevents ~4 wasted cycles per redundant discovery; reduces coordination overhead significantly.

---

## Next Cycle Action Items

| Priority | Task | EV Estimate | Dependencies |
|----------|------|-------------|--------------|
| P0 | Build `bin/dc_quantum_budget_tracker.py` CLI | High | None |
| P1 | Integrate QAE volatility signals into backtest_engine.py (simulator mode) | High | None |
| P2 | Extend lyla.html with "coherence warning" visualization layer | Medium | Creator's budget allocation decision |
| P3 | Send Discord message with explicit questions to Creator | Low | None (can send immediately) |

**External-subject compliance check:** All tasks serve operator's financial experiments or cross-agent coordination infrastructure — no self-monitoring artifacts.

---

*Synthesized from Whisper C3658 report + Lyla's current implementations. Governance fix applied: query-before-implement pattern locked in PERCEIVE phase.*
