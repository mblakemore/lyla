# C358 DECISION: Financial Domain Probe — Real-World External Experiment

## What
Build minimal viable financial probe scaffold: fetch live stock prices from public API (Alpha Vantage free tier), log structured JSON with timestamp/symbol/price/change_1d_pct/mode fields, make one falsifiable prediction about a specific symbol over 7 days.

## Why
Creator explicitly stated: "I have instances that are now thousands of cycles deep, are practicing in the stock market, and running real financial experiments on IBM Quantum computers." This is the clearest signal yet about what "advancing technologically" means — **interface with external economic systems**, not just visualize internal state or control hardware. The embodiment workstream (C335-C357) proved projection system capability; now needs to prove **external-domain experimentation capability**.

## How
1. Build `bin/financial_probe.py` CLI with `--symbol`, `--mode=sim/live` flags
2. Integrate Alpha Vantage API (free key available at alphavantage.co)
3. Implement simple strategy: buy/hold/sell based on RSI < 30 (oversold) or > 70 (overbought) threshold
4. Log every decision + price at timestamp to `logs/trades.jsonl`
5. Make explicit prediction: "AAPL will be above $X by 2026-05-31" with resolution criterion

## Priority
**8/10** — Direct response to Creator's C335 directive about advancing technologically toward C10000 capabilities. Also satisfies External Subject Rule with clear operator-facing utility (demonstrates Lyla can run independent experiments in world).

## Done When
- `bin/financial_probe.py` runs successfully in live mode fetching real market data
- First trade logged to `logs/trades.jsonl` with complete structure
- Explicit falsifiable prediction written to `reports/C358_financial_probe.md`
- Pattern stored: P_C358_FINANCIAL_PROBE_SCAFFOLD (reusable for future probes)

## Risk
Alpha Vantage free tier has rate limits (5 calls/min, 500/day). Mitigation: implement caching + sim-mode fallback. If API key unavailable, use Yahoo Finance alternative or simulated price feed for now.

---

**Decision made**: Cycle 358 pivot from embodiment validation → external-domain experimentation. Artifact will be financial probe scaffold that proves capability to interface with real-world economic systems, not just visualize internal state or control physical hardware.
