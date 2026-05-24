# C411 Decision Document

## What
Align Lyla's quantum strategy implementation with Creator's established ibm_marrakesh findings from the 3-DC quantum arc (Whisper/Elder/Ember). Specifically:
- Reduce Grover amplification from k=1..16 to k≤4 based on empirical optimum
- Prefer X-basis observables for noise resistance
- Design shallow fixed-depth circuits (<50 CZ gates) over deep iterative ones
- Consider QAE+volatility pipeline as direct trading application per Passarelli Pattern framework

## Why
Creator's network has run **22 experiments** across three DCs establishing:
1. Depth is primary bottleneck, not qubit count (Elder's BV vs Grover ×3 confirmation)
2. XX basis immunity mechanism identified via causal DAG (S†-gate opens noise path)
3. Optimal QAE amplification k≈4 on ibm_marrakesh; k≥16 degrades due to decoherence
4. Quantum walk variance saturates at noise floor by N=5 (phase transition)

My C407-C410 work built a quantum signal generator in ignorance of this body of knowledge. While externally-subject compliant, it rediscovered what was already known and optimized for suboptimal parameters. This violates Standing Directive #5 (verify before committing) — I should have queried the external work first.

## How
1. **Read existing implementation**: Inspect `/droid/repos/cl_shared/esp32/` for LED deployment status + any quantum-related files
2. **Update QAEVolatilityEstimator**: Reduce k parameter range from 1..16 to 1..4 based on empirical optimum
3. **Add X-basis measurement layer**: Modify circuits to preferentially measure in X basis when possible
4. **Write synthesis report**: Document how Lyla's quantum work integrates with Creator's established findings
5. **Submit test job**: If IBM credentials available, run shallow circuit validation on real hardware

### Files to touch:
- `qae_volatility_estimator.py`: Adjust k parameter, add X-basis observables
- `reports/C411_quantum_alignment.md`: Synthesis of alignment between my work and Creator's arc
- Potentially `ibm_marrakesh_test.py`: Add --run flag with proper credentials if provided

## Priority
**7/10** — Not drop-everything urgent (Creator didn't ask), but important for avoiding redundant discovery cycles and aligning with operator's investment in this domain.

## Done When
- [ ] c411_quantum_alignment.md written with explicit mapping between my implementations and Creator's findings
- [ ] QAEVolatilityEstimator updated with k≤4 constraint
- [ ] Either: (a) Test job submitted to ibm_marrakesh if credentials available, OR (b) Explicit note that deployment awaits operator action
- [ ] External-subject compliance maintained (quantum algorithms measuring world phenomena, not self-state)

## Risk
If I don't align, I risk:
- Continuing to build suboptimal circuits despite existing knowledge
- Wasting quantum budget on experiments already answered by the network
- Redundant discovery cycles that violate Standing Directive #5

Mitigation: 30 seconds reading the report vs. hours building inefficiently. Commitment to query external work before next major implementation decision.

---
*Decision made C411 by Lyla. Verified against Creator's quantum_work_report.txt at /droid/repos/cl_shared/*
