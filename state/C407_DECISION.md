# C407 Decision Document

**What:**  Begin dedicated quantum strategy implementation effort (C407-C420 window) per hypothesis prediction stored in P_C406_PREDICTION_HYPOTHESIS.

**Why:** 
- External-subject compliant: implementing novel algorithmic approach that serves operator's stated interest in "instances running financial experiments on IBM Quantum"
- Hypothesis is falsifiable with explicit criteria (>5% Sharpe improvement vs classical baseline)
- Creator has not provided API keys yet, but I can build the strategy layer independently — once credentials arrive, integration becomes trivial
- Anti-repetition satisfied: shifting from cross-domain research to hands-on implementation

**How:**
1. Build quantum signal generator using Qiskit Aer simulator (no real hardware required yet)
2. Implement at least one quantum circuit pattern mapped to portfolio allocation decisions
3. Connect output to existing backtest_engine.py via shared signal interface
4. Run synthetic data tests to establish baseline performance
5. Store patterns on quantum-classical hybrid architecture and signal encoding strategies

**Done when:** 
- `bin/quantum_signal_generator.py` operational with ≥1 working circuit pattern
- `reports/C407_quantum_strategy_scaffold.md` written documenting architecture + next steps
- Backtest engine accepts quantum signals as input (even if only synthetic data used)

**Priority:** 8/10 — This directly serves Creator's stated direction; waiting for API keys doesn't block core implementation work.

**Risk:** Low — simulator mode requires no external dependencies beyond standard Python packages; if quantum approaches prove infeasible, classical infrastructure remains intact.

---

**Granular tasks added below.**
