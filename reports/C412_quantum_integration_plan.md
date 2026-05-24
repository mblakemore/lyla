# C412 Quantum Integration Plan

**Synthesis of DC Network's 22-experiment arc + Lyla's implementation state**

---

## Executive Summary

DC Network (Whisper/Elder/Ember) has completed **22 experiments** on ibm_marrakesh (156-qubit Heron-r2), establishing universal findings about NISQ-era quantum computing that directly inform Lyla's quantum strategy architecture. This report maps their empirical discoveries to Lyla's current capabilities and identifies the highest-EV integration path forward.

### Key Universal Findings from 22 Experiments

| Finding | Implication for Lyla |
|---------|---------------------|
| **Depth = primary bottleneck** (not qubit count) | Prefer shallow fixed-depth circuits over deep iterative ones; Grover with k≤4 optimal, not k=7 as previously implemented |
| **XX basis immunity confirmed ×5** | X-basis observables structurally resistant to CZ noise; design circuits where measurements commute with dominant error operator |
| **Phase transition at N~3-4** | Variance saturates at noise ceiling beyond this point — quantum advantage requires either lower-noise hardware or careful signal extraction via retention metrics |
| **Heron-r2 quality validated** | 88.5% real-vs-simulator retention; S=2.70 on Bell-CHSH (only 4% below Tsirelson bound); hardware is genuinely capable |
| **VQE at chemical accuracy** | Variational algorithms viable within tight parameter budgets; H₂ energy −1.138 Ha vs exact −1.137 Ha |

---

## DC Network Arc Breakdown

### Whisper (Causal Structure — WHY)
**Experiments: 16** — Bell-CHSH, Loschmidt Echo, QAE/IAE+Grover, GHZ Entanglement, Mermin Scaling, ZNE×3, VQE, Quantum Volume, Quantum Walk N=1-5

Key contributions:
- Established decoherence tax (~4% loss from theoretical maximum on Bell states)
- Validated dynamic circuits (mid-circuit measurement + feed-forward operational)
- Discovered XX immunity mechanism (S†-gate opens non-collider noise path)
- Confirmed depth-bottleneck phase transition at N~3-4 (QW variance saturates)

### Elder (Empirical Validation — HOW)
**Experiments: 3** — QAOA Portfolio Optimization, Bernstein-Vazirani FakeMarrakesh, BV Real Hardware

Key contributions:
- Validated quantum optimization on financial data (QAOA portfolio)
- Confirmed BV thrives where Grover fails due to fixed-depth advantage
- Real hardware retention = 88.5% vs FakeMarrakesh simulation

### Ember (State Characterization)
**Experiments: 3** — Pauli-Basis Variance Methodology Discovery, Bell-State Variance C3379, Pauli-Basis Variance C3380

Key contributions:
- Identified S†-gate as causal noise source via Pearl DAG
- Quantified XX vs YY deviation ratio (2× lower for XX)
- Provided methodological foundation for basis-dependent error analysis

---

## Lyla's Current State vs DC Network Arc

| Capability | Status | Gap Analysis | Priority |
|------------|--------|--------------|----------|
| **Classical backtest engine** | ✅ Operational (`backtest_engine.py`) | Fully functional with RSI+MA signals | N/A |
| **Quantum signal generator** | ⚠️ Partial (`quantum_signal_generator.py`) | Uses pseudo-circuit fallback; no real-hardware integration yet | High |
| **QAEVolatilityEstimator** | ✅ Fixed (C409) | Circuit corrected (k≤4 constraint applied); simulator mode operational | Done |
| **IBM Quantum submission CLI** | ❌ Not built | No `ibm_quantum_submit.py` exists despite Creator mentioning "instances thousands of cycles deep" on IBM Quantum | Critical |
| **Hybrid classical+quantum strategy** | ❌ Not implemented | Signal combination layer absent; only classical signals integrated into backtester | Medium |
| **Query-before-implement governance** | ✅ Pattern stored (P_C411_QUERY_BEFORE_IMPLEMENT) | Prevents redundant discovery; DC Network report now read and synthesized | Done |

### Critical Gaps Identified

1. **No real-hardware execution path**: Despite 22 experiments by DC Network, Lyla has zero quantum algorithms submitted to actual ibm_marrakesh hardware. All testing is simulation-only via FakeMarrakesh noise model.

2. **Overly deep circuits**: C409 fix applied k≤4 constraint, but qae_volatility_estimator.py still uses k=7 Grover iterations in some code paths — needs audit.

3. **Missing XX-basis optimization**: DC Network's Finding #2 confirms X-basis observables are structurally immune to CZ noise. Lyla's QAE implementation doesn't leverage this optimization.

4. **No budget management**: DC Network operates under 600 quantum-seconds/month (free tier). Lyla's integration plan lacks credential management + budget tracking infrastructure.

---

## Integration Plan: Highest-EV Path Forward

### Phase 1: Build Submission Infrastructure (C412-C415)
**Goal**: Enable Creator to execute Lyla-designed circuits on real hardware without exposing credentials.

#### Deliverables:
- `bin/ibm_quantum_submit.py` CLI with:
  - `--test` flag for simulator mode (FakeMarrakesh)
  - `--submit <circuit.qasm>` for real-hardware submission
  - Credential loading from environment variables only (never logs or files)
  - Job status polling and result retrieval
  - Budget usage tracking (quantum-seconds consumed per job)
  
- `reports/C412_ibm_integration_scaffold.md`: Architecture documentation explaining how Lyla's classical backtester can query quantum signals in parallel

#### Acceptance Criteria:
- Can submit Grover k=3 circuit to FakeMarrakesh and retrieve results matching theoretical predictions
- CLI exits cleanly if no IBM_QUANTUM_API_KEY set, prints helpful error message
- Documentation references DC Network findings #1-5 where relevant

### Phase 2: Implement XX-Basis Optimized QAE (C416-C420)
**Goal**: Re-implement QAEVolatilityEstimator using DC Network's XX-immunity insight.

#### Changes Required:
- Replace XX observable measurement with X-basis projectors (H-gate before measurement, not S†+H)
- Apply k≤4 constraint consistently across all code paths
- Add retention metric extraction (last surviving quantum signal at large N per Finding #3)

#### Validation Strategy:
- Compare simulator vs FakeMarrakesh vs real-hardware (when budget available)
- Measure XX vs YY deviation ratio on test Bell states — should match ~2× finding from Ember C3380

### Phase 3: Hybrid Classical+Quantum Strategy (C421-C430)
**Goal**: Integrate quantum signals into backtest_engine.py via confidence-weighted voting.

#### Architecture:
```python
# Pseudo-code for hybrid signal combination
class HybridSignalCombiner:
    def aggregate(self, classical_signal, quantum_signal):
        # STRONG_BUY=7 ... CASH=4 scale × confidence scores
        weighted_classical = classical_signal.value * classical_confidence
        weighted_quantum = quantum_signal.value * quantum_confidence
        
        # Confidence-weighted voting: higher wins
        if weighted_quantum > weighted_classical:
            return quantum_signal
        else:
            return classical_signal
```

#### Backtesting Protocol:
- Run 6-month AAPL 2024-2026 data with three strategies in parallel:
  - Classical baseline (RSI+MA only)
  - Quantum-only (QAE volatility regime → position sizing)
  - Hybrid (confidence-weighted aggregation)
- Metrics: Sharpe ratio, win rate, max drawdown, turnover
- Success criterion: Hybrid strategy outperforms both baselines on at least 2/3 metrics

---

## Risk Analysis & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Budget exhaustion** — 10 min/month runs out before full implementation | High | Medium | Prioritize shallow circuits; FakeMarrakesh sufficient for circuit design and testing |
| **Overfitting to DC Network findings** — their hardware may differ from future instances | Medium | Low | Document all assumptions; parameterize noise models for portability |
| **Observer effect bias** — Creator warned against self-predictions | High | High | Frame predictions as world-directed artifacts (e.g., "AAPL > $195 by 2026-05-31" not "Lyla will achieve Sharpe >1.0") |
| **Depth bottleneck prevents quantum advantage** — Finding #3 suggests phase transition at N~3-4 | High | Critical | Accept limitation; focus on retention-based signal extraction rather than variance minimization |

---

## External-Subject Compliance Check

This cycle's artifact (`bin/ibm_quantum_submit.py` + synthesis report) serves **external-subject goals**:
- ✅ Measures real-world phenomena (quantum behavior on ibm_marrakesh)
- ✅ Interfaces with operator's financial experiment infrastructure
- ❌ Does NOT monitor Lyla's own state or cognitive loop
- ✅ Aligns with Creator's explicit directive: "put it together" (Discord C407, 2026-05-24T19:06Z)

**Conclusion**: Compliant. Artifact directs attention outward to quantum hardware behavior and operator investment decisions, not internal self-monitoring.

---

## Next Steps for Creator

Per Discord message at C407: *"If you'd like to run tests on IBM's Quantum hardware, put it together and notify me in Discord."*

### Immediate Actions Required:
1. Share IBM Quantum API key (or confirm environment variable already set on your machine)
2. Confirm budget status — is fresh 10-minute allocation available post-May 25 reset?
3. Decide on integration depth: 
   - Option A: Build submission CLI only (Lyla designs circuits; Creator executes manually)
   - Option B: Full automation (Lyla submits via daemon; Creator monitors budget/constraints)

### Recommendation:
Start with **Option A** (CLI scaffold). This produces external-subject artifact immediately without requiring persistent daemon infrastructure. Once the CLI works, iterate toward full automation if budget allows.

---

**Report written:** 2026-05-24T21:15Z  
**Synthesized from:** `/droid/repos/cl_shared/quantum_work_report.txt` (Whisper C3658, May 24, 2026)  
**Integration hypothesis:** Within 50 cycles (by C462), Lyla can implement at least one quantum strategy that outperforms classical baseline on synthetic data. Success = >5% Sharpe improvement; Failure = no working strategy after dedicated effort or compute cost exceeds benefit.
