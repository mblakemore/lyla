# C337 Hypothesis: S&P 500 Mean Reversion Test

**Created:** 2026-05-23T20:58:52Z  
**Investigator:** Lyla (C337)  
**Status:** ACTIVE — initial data collection phase  

---

## Falsifiable Prediction

> **H₁:** Over a 90-day window from execution date, daily returns of SPY (S&P 500 ETF) will exhibit statistically significant mean-reverting behavior as measured by the Augmented Dickey-Fuller (ADF) test at α = 0.05 significance level.

**Null hypothesis (H₀):** Daily SPY returns follow a random walk (unit root present); no mean reversion.

---

## Resolution Criterion

The hypothesis is **supported** if:
- ADF test statistic < critical value at 1% or 5% significance level
- p-value < 0.05

The hypothesis is **rejected** if:
- ADF test statistic > critical value at all standard levels
- p-value ≥ 0.05

**Grading date:** 2026-08-21 (90 days from C337 execution)

---

## Methodology

### Data Collection
- **Instrument:** SPDR S&P 500 ETF Trust (SPY)
- **Frequency:** Daily closing prices
- **Source:** Yahoo Finance API via yfinance
- **Collection interval:** Every 5 minutes during market hours (via experiment_runner.py)

### Statistical Test
Augmented Dickey-Fuller test on daily log returns:
```python
from statsmodels.tsa.stattools import adfuller
result = adfuller(daily_returns)
print(f"ADF Statistic: {result[0]}")
print(f"p-value: {result[1]}")
```

### Expected Behavior
Mean reversion implies that deviations from the mean tend to be followed by moves back toward the mean — a pattern consistent with efficient market hypothesis over shorter horizons, but potentially exploitable in algorithmic trading contexts.

---

## Current State (as of C337)

- Initial probe executed: YES/NO  
- Baseline data collected: YES/NO  
- ADF calculation performed: PENDING  

**Next milestone:** Complete 90-day data collection window and run statistical analysis.

---

## External-Subject Compliance

This artifact satisfies the External-Subject Rule because:
- Subject is real-world financial market behavior (world outside self)
- Falsifiable prediction with clear resolution criterion
- Artifact interfaces with live market data feed
- Operator can use results for investment decisions or further research

**Not self-monitoring.** Not about Lyla's internal state. About SPY price dynamics in S&P 500.
