# C405 Decision Document

## What
Complete the financial autonomy workstream with a **live execution capstone**: deploy backtest_engine.py in sim mode against current market data, generate a actionable trade signal, and present it to Creator as the culmination of C358-C404 infrastructure development.

## Why
1. **External-subject compliance verified** — 5 consecutive cycles of financial/embodiment work satisfy the 1-in-3 rule
2. **Workstream maturity** — Backtesting engine built and tested over 47 cycles; ready for operational synthesis
3. **Creator's directive alignment** — They explicitly mentioned instances running real financial experiments; we've built the scaffold but not demonstrated live operation
4. **Avoids drift risk** — Finishing one thread cleanly before starting another prevents accumulation of "awaiting directive" states

## How
1. Run `bin/backtest_engine.py --simulate AAPL` (or current market ticker)
2. Capture output: position size, entry price, stop-loss, take-profit thresholds based on RSI+MA signals
3. Write synthesis report at `reports/C405_financial_autonomy_capstone.md` containing:
   - Infrastructure summary (what was built across C358-C404)
   - Live simulation results with concrete numbers
   - Explicit question: "Do you want me to escalate to actual trading with paper money first, or pivot to visualization stack enhancement?"
4. Store pattern P_C405_FINANCIAL_CAPSTONE documenting the design decision of "infrastructure-first then explicit escalation question"

## Priority
7/10 — completing a major workstream is higher priority than continuing to iterate on scaffolding

## Done When
- ✓ Backtesting engine executes sim trade against current data
- ✓ Synthesis report written and committed
- ✓ Pattern stored on capstone completion strategy
- ✓ Creator receives explicit call-to-action: proceed with live experiments OR pivot to new domain

## Risk Assessment
**Risk:** If Creator wanted something else entirely, this completes work they didn't ask for.
**Mitigation:** The synthesis report ends with explicit options (A/B/C) so Creator can redirect before next cycle. This is not silent continuation; it's a handoff point.

---

*Decision made by Lyla at C405 transition. Awaiting ACT phase execution.*
