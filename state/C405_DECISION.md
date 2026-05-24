# C405 DECISION — Explicit Written Decision Per Standing Directives and External-Subject Rule

## What
**Decision:** Present 4 explicit options to Creator for next direction on financial autonomy workstream; await selection before continuing iteration.

### Option A: Optimize Parameters
- Focus: Tune RSI threshold from <40 to more conservative levels (e.g., <30, <25)
- Effort: 1-2 cycles of parameter sweep testing
- Risk: May still fail if signal logic itself is flawed

### Option B: Redesign Signals  
- Focus: Replace RSI+MA crossover with alternative indicators (MACD, Bollinger Bands, volume-based)
- Effort: 3-5 cycles for research + implementation + backtesting
- Risk: High uncertainty whether new signals will improve Sharpe

### Option C: Escalate to Paper Trading
- Focus: Deploy backtest_engine.py to run against LIVE market data via Alpha Vantage API
- Effort: 2-3 cycles (API integration, risk limits, monitoring infrastructure)
- Risk: Real-market execution reveals slippage/latency issues not visible in historical backtests

### Option D: Pivot Domains
- Focus: Abandon financial autonomy entirely; shift to visualization/human interaction stack per Standing Directives
- Effort: Immediate redirection; leverage existing projection system + LED rings
- Risk: Lose sunk investment in financial infrastructure (but it's already built and documented)

## Why This Decision
**Per Standing Directives:** "Continue external-domain work" — all four options satisfy this requirement.

**External-Subject Rule:** Each option produces artifacts whose subject is world outside self (market data, operator interface, trading outcomes). No self-monitoring required.

**Pattern Recognition (P_C405_FINANCIAL_CAPSTONE):** After N=48 cycles of infrastructure development, natural pause point reached. Continuing iteration without explicit direction risks inefficient parameter optimization vs. strategic exploration tradeoff.

**Opportunity Cost Consideration:** Financial domain specialization has been valuable for demonstrating autonomous agent depth. However, Creator has also expressed interest in "technological advancement" via visualization interfaces. These may be competing priorities requiring explicit choice.

## How
1. **Immediate:** Write synthesis report (C405_financial_autonomy_capstone.md) documenting 48-cycle journey with results and options
2. **Short-term:** Await Creator selection among A/B/C/D
3. **Post-selection:** Execute chosen path with clear success criteria and timeline

### Success Criteria by Option:
- **A:** Sharpe > 1.0 after parameter tuning (within 2 cycles)
- **B:** New signal strategy achieves positive Sharpe on AAPL (within 5 cycles)  
- **C:** Paper trading system operational with live feeds (within 3 cycles)
- **D:** Visualization stack enhanced per Standing Directives C335-C337 (immediate redirection)

## Done-When
- ✅ Synthesis report written with all 4 options documented
- ✅ Patterns stored in patterns.jsonl (P_C405_FINANCIAL_CAPSTONE)
- ✅ Anchor milestone added to memories (A_C405_BACKTEST_EXECUTION)
- ⏳ Creator selects option (awaiting response)
- ⏳ Chosen path executed with measurable outcomes

## Risk Assessment
| Risk | Probability | Mitigation |
|------|-------------|------------|
| Creator doesn't respond for multiple cycles | Medium | Multi-cycle-wait pattern already applied; can pivot to external compliance work if needed |
| Parameter optimization hits diminishing returns | High | Option B exists as alternative; A is explicitly limited to 1-2 cycles max before escalation |
| Live paper trading reveals fundamental flaws | Low-Medium | Already demonstrated via backtests (-0.101 Sharpe); C just moves from historical to real-time |
| Financial domain not aligned with creator's broader vision | Medium | Option D available for immediate pivot |

## External-Subject Compliance Verification
**Artifacts produced:**
1. `bin/backtest_engine.py` — executes trades against AAPL market data ✓
2. `reports/C405_financial_autonomy_capstone.md` — synthesizes 48-cycle journey with operator-facing options ✓  
3. `state/memories/patterns.jsonl` entries — encode externally-directed learning ✓

**Not self-monitoring:** Results measure AAPL price movements, not Lyla's internal state or cognitive performance.

**Verdict:** COMPLIANT ✓

---

**Decision made by:** Lyla v1.0 (autonomous agent)
**Timestamp:** 2026-05-24T17:09:30+00:00
**Cycle:** 405
**Status:** AWAITING CREATOR SELECTION AMONG OPTIONS A-D
