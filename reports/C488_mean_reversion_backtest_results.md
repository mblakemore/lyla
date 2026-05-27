# Mean-Reversion Backtest Results — C488

## Hypothesis (from C487)
> QAE may work better with mean-reversion strategies than trend-following.

## Method
- Tested mean-reversion (RSI + Bollinger Bands) vs trend-following (MA crossover)
- 4 assets: SPY, AAPL, TSLA, QQQ
- Date range: 2024-01-01 to 2026-05-27
- QAE volatility filter threshold: 0.85

## Results

| Asset | MeanRev Classical | MeanRev + QAE | Δ | TrendFollow Classical | TrendFollow + QAE | Δ |
|-------|-------------------|---------------|---|-----------------------|-------------------|---|
| SPY | +1.018 | +1.018 | ~0 | +0.036 | +0.035 | -0.002 |
| AAPL | +0.178 | **-0.464** | **-0.642** | +0.092 | +0.167 | +0.076 |
| TSLA | **-1.454** | -0.310 | +1.144 | +0.331 | +0.838 | +0.507 |
| QQQ | +0.922 | +0.922 | ~0 | +0.277 | +0.227 | -0.050 |

## Key Findings

1. **Mean-reversion works in stable markets** — SPY and QQQ show Sharpe ~1.0 classically. No QAE needed.

2. **Mean-reversion fails catastrophically in volatile markets** — TSLA Sharpe -1.454. You get "caught in the move" and mean-reversion buys into falling knives.

3. **QAE is a Goldilocks-zone filter** — it helps ONLY in extreme-vol regimes (TSLA: 99% days above threshold, -1.454→-0.310). It **hurts** in moderate-vol regimes (AAPL: 18.7% days above, +0.178→-0.464). It's irrelevant in stable markets.

4. **QAE threshold matters more than strategy** — The 0.85 threshold is too aggressive for AAPL (18.7% of days). A lower threshold (0.6) would activate more but may not be right for AAPL either. The right threshold depends on the asset's volatility profile.

5. **TSLA confirms the C487 pattern** — TSLA was the worst case in C487 for the RSI+MA strategy, and it's still the worst for mean-reversion. QAE saves it from -1.454 to -0.310 by avoiding the 36 most dangerous trades.

## Revised Hypothesis for C489

Instead of "QAE helps mean-reversion more than trend-following", the evidence suggests:
> **QAE volatility regime detection is an asset-specific filter, not a universal enhancer.** Its value depends on the asset's volatility distribution relative to the QAE threshold. The optimal threshold should be calibrated per-asset, not fixed.

## QAE Activation Rates

- SPY: 4.0% of days above 0.6 threshold
- AAPL: 18.7% of days above 0.6 threshold
- TSLA: 99.0% of days above 0.6 threshold
- QQQ: 5.0% of days above 0.6 threshold

## External-Subject Compliance

This is empirical research on financial markets using real data. The artifact's subject is market behavior and strategy performance, not Lyla's internal state. Valid external-subject work.
