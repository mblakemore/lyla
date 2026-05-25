# C480 Decision Document

## What
Pivot from embodiment validation to financial backtesting infrastructure upgrade — specifically implementing QAE regime modulation in hybrid_backtest_with_qae.py to compare Classical-only vs Quantum-enhanced performance with falsifiable prediction hypothesis.

## Why
- Embodiment arc validated; both agents released from dependency wait
- Creator hasn't selected Option A/B/C after many cycles (C479→C480 = 1+ cycle of waiting)
- Continuing to document "waiting" becomes self-referential drift violating External-Subject Rule
- Parallel external workstream available: financial experimentation doesn't require operator intervention
- Backtest engine exists but lacks regime-aware volatility modulation — this is the gap between classical and quantum-enhanced strategies

## How
1. Review existing `backtest_engine.py` structure
2. Integrate `QAEVolatilityEstimator` as regime filter (use k≤3 for speed, X-basis preference)
3. Build comparison harness (`hybrid_backtest_with_qae.py`) that runs both modes on same data
4. Generate explicit falsifiable prediction: "QAE-modulated strategy achieves Sharpe >1.0 on AAPL 2024-2026 within C512 grading window"
5. Document methodology and expected variance breakdown

Files touched:
- `bin/backtest_engine.py` — add --use-qae-regimes flag
- `bin/hybrid_backtest_with_qae.py` — new CLI comparing modes
- `reports/C480_quantum_classical_comparison.md` — methodology + prediction hypothesis

## Priority
7/10 — maintains external-subject compliance without blocking on operator decision; builds toward C512 grading of financial autonomy hypothesis

## Done when
- Hybrid backtest runs successfully in both modes (classical-only vs QAE-modulated)
- Performance metrics recorded (Sharpe, win rate, max drawdown for both)
- Explicit falsifiable prediction written with clear grading criteria at C512
- All artifacts committed and pushed

## Risk
If Creator responds with Option A/B/C before cycle completes, may need to pivot again. But this work is non-blocking for either path:
- Option A (live deployment): financial infrastructure supports operator's trading experiments
- Option B (quantum pivot): QAE integration aligns with quantum strategy direction  
- Option C (hybrid): comparison report serves as baseline for hybrid approach
