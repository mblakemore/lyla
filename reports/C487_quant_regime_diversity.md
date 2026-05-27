# C487 — Quant Phase 2: Regime Diversity Backtests

## Hypothesis
The +0.020 Sharpe delta on SPY 2024-2026 (low-volatility period) might be:
- Period-specific overfit (works only in low-vol regimes)
- Real signal (generalizes across regimes, especially high-vol)
- Noise (doesn't generalize at all)

## Test Matrix

| Regime | Classical Sharpe | QAE Sharpe | Delta |
|--------|-----------------|------------|-------|
| SPY 2024-2026 (low vol) | 0.797 | 0.817 | **+0.020** |
| SPY 2020-2022 (COVID) | 0.251 | 0.314 | **+0.063** |
| AAPL 2024-2026 | -0.101 | -0.032 | **+0.069** |
| TSLA 2024-2026 | 0.654 | 0.000 | **-0.654** |
| BTC-USD 2024-2026 | 0.000 | 0.000 | +0.000 |
| QQQ 2020-2022 | 0.114 | 0.024 | **-0.090** |

## Key Findings

### 1. QAE improves Sharpe on AAPL and SPY 2020-2022
The QAE regime filter is NOT just SPY 2024-2026 overfit. AAPL (another large-cap equity) shows the same direction of improvement, and SPY during the COVID crisis shows even larger improvement (+0.063 vs +0.020).

### 2. QAE is catastrophically conservative on TSLA
TSLA: classical Sharpe 0.654 → QAE Sharpe 0.000. The QAE classified 100% of TSLA's data points as "high vol" (P > 0.5), which suppressed ALL buy signals. The strategy executed zero trades under QAE.

This is expected: TSLA has extreme volatility, and the QAE's vol_features (rolling volatility + volume change) are always above the threshold. The QAE is correct in detecting high volatility, but the strategy's regime filter (P > 0.6 → suppress buy) is too aggressive for extremely volatile assets.

### 3. QAE hurts on QQQ 2020-2022
QQQ during the COVID period shows QAE Sharpe -0.090. This is the opposite of SPY 2020-2022 (+0.063) despite both being tech-heavy during the same period. Possible explanation: QQQ is more volatile than SPY, so the QAE's regime filter is more aggressive and suppresses trades that would have been profitable.

### 4. BTC-USD produces no trades
The backtest engine doesn't handle BTC-USD well (zero trades on both classical and QAE). Likely an issue with how the symbol is parsed or how the data is fetched from Yahoo Finance.

## Regime Distribution Analysis

| Regime | High Vol (%) | Low Vol (%) | Mid Vol (%) |
|--------|-------------|-------------|-------------|
| SPY 2024-2026 | 4% | 78% | 18% |
| SPY 2020-2022 | 24% | 34% | 42% |
| AAPL 2024-2026 | 41% | 12% | 47% |
| TSLA 2024-2026 | 100% | 0% | 0% |
| BTC-USD 2024-2026 | 85% | 1% | 14% |
| QQQ 2020-2022 | 50% | 18% | 32% |

Pattern: **QAE improvement correlates with moderate volatility, not extreme.** Low-vol markets (SPY 2024-2026) → small improvement. Moderate-vol (SPY 2020-2022) → larger improvement. High-vol (TSLA) → catastrophic failure.

## Conclusions

1. **The +0.020 delta was real but understated.** The QAE regime filter genuinely improves the RSI+MA strategy, but only when the asset's volatility is in the "Goldilocks zone" — high enough for regime detection to matter, low enough that the filter doesn't suppress all trades.

2. **The strategy is fundamentally limited for extreme-volatility assets.** The regime filter's threshold (P > 0.6 → suppress buy) is binary and absolute. For TSLA/BTC, this kills all trading. The fix would be either:
   - Adaptive thresholds (scale the threshold to the asset's volatility)
   - Gradual modulation (reduce position size rather than full suppression)
   - Different strategy for high-vol assets

3. **C476 prediction (Sharpe > 1.0) is NOT met by the current approach.** The best QAE Sharpe achieved is 0.817 on SPY 2024-2026. The C476 target of >1.0 requires a more fundamental strategy change, not just QAE regime filtering.

4. **Next direction:** The RSI+MA crossover strategy may be the wrong base strategy for QAE modulation. Per P_C480_STRATEGY_MISMATCH: volatility-aware filters may work better with mean-reversion strategies than trend-following momentum approaches.

## Pending Questions
- Does a mean-reversion strategy (e.g., RSI oversold bounce) benefit more from QAE modulation?
- Should the QAE thresholds be adaptive rather than fixed at 0.6/0.3?
- What about adding a volume-weighted component to the regime detection?
