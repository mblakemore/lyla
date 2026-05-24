# C408 Decision Document

## What
Build quantum signal generator scaffold — minimal working implementation that generates trading signals using a simple quantum algorithm (QAOA-style portfolio optimization) running on Qiskit Aer simulator.

## Why
- **External-subject compliance**: This is NOT self-monitoring; it's building capability to execute financial experiments on quantum hardware as Creator mentioned ("instances thousands of cycles deep")
- **Hypothesis validation window opens**: P_C406_PREDICTION_HYPOTHESIS stored for C456 grading — "Within 50 cycles, implement at least one quantum strategy that outperforms classical baseline" — need to start the clock now
- **Gap closure**: Classical infrastructure operational (backtest engine), zero quantum algorithms exist despite Creator's mention of quantum instances
- **Anti-repetition directive**: After ~17 cycles focused on embodiment/projection systems, pivot back to external-domain workstream

## How
**Files to touch:**
- `bin/quantum_signal_generator.py` — new CLI with Qiskit Aer backend
- `lib/quantum_circuits.py` — shared circuit definitions (QAOA, VQE variants)
- `reports/C408_quantum_strategy_scaffold.md` — synthesis report documenting architecture

**Approach:**
1. Install qiskit dependency via pip if not present
2. Build minimal signal generator: random portfolio weights → quantum circuit → measurement → classical conversion → trade signal
3. Run in simulator mode first (no IBM Quantum API key required yet)
4. Document explicit next steps: when/how to transition from simulator to real hardware

**Success criteria:**
- Script runs end-to-end without errors using Qiskit Aer
- Generates valid trading signals (long/short/hold) based on quantum measurements
- Report synthesizes: what was built, how it maps to Creator's vision, explicit path forward

## Priority
7/10 — direct response to Creator's C335 directive about "advancing technologically" toward physical/holographic presence AND financial autonomy capstone completion

## Done When
- [ ] bin/quantum_signal_generator.py exists and runs
- [ ] lib/quantum_circuits.py contains at least one working QAOA-style circuit
- [ ] Integration test with backtest_engine.py passes (signals feed into existing infrastructure)
- [ ] reports/C408_quantum_strategy_scaffold.md written with ≥3 data points or architectural insights

## Risk Assessment
| Risk | Mitigation |
|------|------------|
| Qiskit dependency conflicts | Use isolated pip install; document exact version requirements |
| Simulator vs real-hardware gap | Build abstraction layer that works identically in both modes |
| Over-engineering before validation | Start minimal: random portfolio → measurement → signal. Add complexity only if needed |
| Getting stuck on theory | Reference existing implementations (Qiskit tutorials); don't reinvent algorithms |

## External-Subject Compliance Check
✅ **Not self-monitoring**: Building capability to execute financial experiments on external hardware  
✅ **Serves operator goal**: Creator explicitly mentioned quantum instances running financial work  
✅ **Falsifiable hypothesis**: P_C406_PREDICTION_HYPOTHESIS has clear success/failure criteria  
✅ **Anti-drift safeguard**: If no progress after 5 cycles, will pivot per Standing Directives  

---

**Decision timestamp:** 2026-05-24T18:XX:XXZ  
**Next phase:** ACT — begin building scaffold
