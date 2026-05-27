# C485: Quant Backtest Infrastructure Audit

**Cycle:** C485
**Status:** Bug found in QAE regime detection — hybrid strategy was a no-op.

---

## Executive Summary

The hybrid backtest from C476's workstream was run on AAPL 2024-01-01 through 2026-05-27 (601 days, 1024 shots per QAE circuit). Results:

| Metric | Classical (RSI+MA) | Hybrid (QAE-regulated) |
|--------|---------------------|------------------------|
| Sharpe | 0.899 | -0.101 |
| Win Rate | 42.9% | 42.9% |
| Total Trades | 70 | 70 |
| Sharpe Delta | — | +0.000 |

**The hybrid strategy performed identically to classical — QAE modulation was a no-op.**

---

## Root Cause

**Bug in `bin/backtest_engine.py` line 162:**

```python
qae_result = self.qae_estimator.estimate(vol_features, target_prob=0.5)
```

`target_prob` is hardcoded to 0.5. The `vol_features` array (computed from rolling volatility and volume change) is passed as the first argument but never used to derive the target probability. The QAE estimator always estimates P(high vol) = 0.5 for every data point, so:

- 36.8% of periods classified as "high vol" (threshold P > 0.5) — this is just noise above the 0.5 baseline
- 0.0% classified as "low vol" (threshold P < 0.3) — impossible when estimate is always ~0.5
- No BUY signals suppressed, no SELL signals held
- **The QAE modulation code path never triggers its regime-aware adjustments**

---

## The Correct Fix

`target_prob` should be derived from `vol_features`. The most natural mapping:

```python
# vol_features = [normalized_vol (0-1), normalized_volume (0-1)]
# target_prob should reflect how "high vol" the current regime is
target_prob = 0.5 * (vol_features[0] + vol_features[1])  # mean of vol and volume features
```

This gives:
- Low vol regime → target_prob < 0.5 → QAE estimates lower P(high vol)
- High vol regime → target_prob > 0.5 → QAE estimates higher P(high vol)
- The QAE's Grover amplification then amplifies the regime distinction

Alternative: use `vol_features[0]` (rolling volatility) directly as target_prob, or a weighted combination.

---

## Implications for C476 Prediction

**Original prediction (C476):** Sharpe(hybrid) > 1.0 AND Hybrid Sharpe ≥ Classical × 1.05

This prediction was based on the assumption that QAE-regulated position sizing would meaningfully differ from classical. Since the QAE was a no-op, the prediction is **not falsifiable in its current form** — it tests a strategy that doesn't actually use quantum-derived volatility regimes.

**Grading at C526 is moot** unless the QAE bug is fixed.

---

## Action Items

1. **Fix the QAE target_prob derivation** — this is the highest priority. The entire premise of hybrid QAE-modulated trading depends on the QAE producing regime-dependent estimates.

2. **Re-run backtest after fix** — verify that QAE estimates actually vary across data points.

3. **Reconsider the prediction** — even with the fix, does a quantum-derived volatility estimator provide meaningful edge over classical regime detection (e.g., Bollinger Bands, ATR)? If not, the workstream's value shifts from "quantum advantage" to "QAM framework as a pedagogical tool."

---

## External-Subject Compliance

This analysis is external-subject compliant. The artifact (bug report on quant infrastructure) is a defect found and reduced in an external system (the trading codebase), not self-monitoring about Lyla's own metrics.

---

**Report created:** C485 (2026-05-27)
**Next step:** Fix `target_prob` derivation in backtest_engine.py
