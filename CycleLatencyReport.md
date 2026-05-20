# Lyla Cadence Analysis

## Quick Summary
Tool: `python3 CycleLatencyProbe.py` outputs gap benchmarks and outliers from last 50 cycles.

## Current Metrics
- **Min gap:**   3,000 ms (0.05 min)  
- **Avg gap:**   7,079,408 ms (117.99 min)  
- **Median:**    2,112,000 ms (35.20 min)  
- **Max gap:**   86,828,000 ms (1447.13 min)  

## Outliers (>2x avg = 14,158,816ms):
| Gap | Description |
|-----|-------------|
| 15,476,000ms (257.9m) | C208 → PERCEIVE add absolute path anchor |
| 16,831,000ms (280.5m) | PERCEIVE add absolute path anchor → C207 |
| 86,828,000ms (1447.1m) | config: enable nudge → C136 Blackboard Sync |
| 44,068,000ms (734.5m) | C134 Stability check → config tools_whitelist |
| 25,504,000ms (425.1m) | config persist_nudge → C131 State shift |

### Key Finding:
Significant drift after C208 (04:22 to 00:04 next day) — gap of ~258 min. This is when we were in the middle of a "Blackboard baseline telemetry probe" cycle that required Creator feedback. The large gaps correlate with waiting periods between active work cycles.
