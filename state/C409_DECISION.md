# C409 Decision Document

## What
Build QAE-based volatility estimator integrated with existing classical backtester, creating first quantum-classical hybrid trading strategy.

## Why
Creator's quantum work report explicitly identifies \"QAE + Financial Volatility\" as priority application path. Lyla has classical infrastructure operational but zero quantum strategies despite DC network already proving QAOA works on financial data. This closes the gap between Creator's stated goal (instances \"practicing in stock market\") and current codebase state. External-subject compliant — serves operator's trading experiments, not just self-monitoring.

## How
1. Read quantum_work_report.txt sections on QAE (C3576–C3581), QAOA (C5333–C5400), and volatility regime patterns
2. Build `bin/qae_volatility_estimator.py` using Qiskit: encode vol regime probability as amplitude, use IAE for quadratic-speedup estimation
3. Integrate into `backtest_engine.py` as alternative signal source alongside RSI+MA (confidence-weighted voting per C408 architecture)
4. Write synthesis report documenting hybrid architecture and falsifiable prediction hypothesis

## Priority
8/10 — directly extends proven quantum arc, uses shared hardware budget efficiently, maintains external-subject compliance

## Done When
- QAE estimator runs on FakeMarrakesh simulator with synthetic vol data
- Backtester executes trades based on QAE signals (can run without real IBM access via simulator fallback)
- Report contains explicit Sharpe comparison target (>1.0 vs classical baseline) with grading criteria for C456

## Risk
Quantum advantage may not exist for this problem type on NISQ hardware (depth bottleneck). Falsifiable outcome — either demonstrates improvement or documents why quantum doesn't help, both valuable learning. 30-second verification: check if QAE circuit depth stays under ~50 CZ gates at N=3-4 qubits (per report's phase transition finding).
