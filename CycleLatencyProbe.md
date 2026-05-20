# Cycle Latency Probe

**Purpose:** Measure time gaps between cycles and identify operational drift or blocking patterns.

## Usage

```bash
# Run from repo root
python3 CycleLatencyProbe.py --help

# Basic usage - analyze last N cycles (default: 50)
python3 CycleLatencyProbe.py [--limit N] [--output FILE]
```

## Example Output

```
Lyla Latency Analysis — last 50 cycles
Min:   3,000 ms (0.05 min)
Avg:   7,079,408 ms (117.99 min)
Median: 2,112,000 ms (35.20 min)
Max:   86,828,000 ms (1447.13 min)

Outliers (>2x avg):
[15,476,000ms]: C208 → PERCEIVE add absolute path anchor
...
```

## Key Metrics

| Metric | Meaning |
|--------|---------|
| **Min** | Fastest cycle turnaround (baseline capability) |
| **Avg** | Typical throughput including all waiting periods |
| **Median** | Most common gap; less affected by blocking outliers |
| **Max** | Longest delay; indicates potential systemic friction |

## Integration

- Add to blackboard baseline for regular cadence monitoring
- Use `--output` flag to generate markdown report automatically
- Thresholds can be tuned per operator preferences
