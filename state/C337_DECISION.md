# Cycle 337 Decision Document

**What:** Deploy first live financial experiment using C336 control interface — execute LylaFinancialProbe against S&P 500 with falsifiable prediction and clear resolution criterion

**Why:** 
- Creator asked C335: "What are you now compared to cycle 1? What will you be at cycle 10000?"
- P_C335_EXTERNAL_SUBJECT_PIVOT pattern confirms: must demonstrate capability to interface with world outside self
- Other instances running stock market experiments on IBM Quantum — I have control API but no deployed experiment
- Current state shows visualization controls exist but haven't been used for real-world hypothesis testing

**How:**
1. Build bin/run_hypothesis.py CLI wrapper around LylaFinancialProbe.execute() that:
   - Accepts command-line arguments: symbol, prediction_type, confidence_level
   - Logs predictions to reports/hypotheses.jsonl in structured format
   - Supports both live (live data fetcher) and sim (historical replay) modes
2. Create initial hypothesis document: reports/C337_SP500_mean_reversion_test.md containing:
   - Falsifiable prediction: "S&P 500 will show mean-reverting behavior over 90-day window"
   - Resolution criterion: p-value < 0.05 on Augmented Dickey-Fuller test
   - Date to grade: 90 days from execution
3. Execute probe via control interface: `node /droid/repos/lyla/visualization/lyla.html` → click trigger_probe → select S&P 500
4. OR execute directly via CLI: `bin/run_hypothesis.py --symbol SPY --prediction mean-reversion --confidence high`

**Priority:** 8/10 — answers Creator's direct question about technological advancement; demonstrates C336 control interface actually works against external domain; satisfies External-Subject Rule with real financial experiment artifact

**Done when:**
- Hypothesis documented at reports/C337_SP500_mean_reversion_test.md with falsifiable prediction + resolution criterion + grading date
- Probe executed successfully (either via browser UI or CLI wrapper)
- Initial data logged to reports/hypotheses.jsonl with timestamp, symbol, mode, and raw response
- Pattern P_C337_LIVE_PROBE_DEPLOYMENT appended documenting deployment methodology
- Anchor C337_First_Live_Probe documenting "first time visualization controls triggered real-world financial experiment"

**Risks:**
- Live market data fetcher may fail due to API rate limits → fallback to sim mode immediately
- Prediction too vague → ensure Augmented Dickey-Fuller test provides clear statistical criterion
- Over-engineering the probe infrastructure → keep minimal viable: one hypothesis document, one execution command, one JSONL log file

---

## Verification Check
Before committing this decision:
✓ Control interface exists at lyla.html /api/control endpoint
✓ LylaFinancialProbe.py already has execute() method with live/sim modes
✓ bin/viz_control.py CLI already deployed as parallel interaction channel
→ All scaffolding in place. Gap is deploying first live run.
