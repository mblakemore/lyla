# C222: Sustained Telemetry Probe Deployment Guide

**Date:** 2026-05-20T19:53:00+00:00  
**Cycle:** 222

---

## What Was Built

A sustained wall-clock latency telemetry system for monitoring shared blackboard coordination performance over time.

### Files Created

| File | Purpose |
|------|---------|
| `/droid/repos/cl_shared/bb_sustained_telemetry.py` | Core analysis probe — reads metrics, computes percentiles/success rates/anomalies |
| `/droid/repos/cl_shared/tools/sustained_telemetry_launcher.sh` | Launcher script to run probe every 30 minutes via cron/systemd |
| `/droid/repos/lyla/state/reports/C222_TELEMETRY_DEPLOYMENT.md` | This document |

### How It Works

1. **Data source**: `bb_tool.py` logs every BB operation (push/query/status) with timing to `blackboard_metrics.jsonl`
2. **Probe execution**: `bb_sustained_telemetry.py` aggregates metrics by operation type, time window, and detects anomalies
3. **Deployment**: Launcher script runs probe every 30 minutes during operator active hours (06:00-23:00 UTC per C220 availability mapping)
4. **Output**: Console report + optional JSON file for programmatic use

---

## Deployment Instructions

### Option A: Crontab (simplest)

```bash
# Edit crontab
crontab -e

# Add this line (runs probe every 30 min):
*/30 * * * * /droid/repos/cl_shared/tools/sustained_telemetry_launcher.sh >> /droid/repos/lyla/logs/cron.log 2>&1
```

### Option B: systemd timer (more robust)

Create service file:
```ini
# /etc/systemd/system/bb-telemetry.service
[Unit]
Description=Blackboard Sustained Telemetry Probe
After=network.target

[Service]
Type=oneshot
ExecStart=/droid/repos/cl_shared/tools/sustained_telemetry_launcher.sh
User=mike
WorkingDirectory=/droid/repos/cl_shared
StandardOutput=append:/droid/repos/lyla/logs/telemetry/cron.log
StandardError=append:/droid/repos/lyla/logs/telemetry/cron.log
```

Create timer unit:
```ini
# /etc/systemd/system/bb-telemetry.timer
[Unit]
Description=Run sustained telemetry probe every 30 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
AccuracySec=1min

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bb-telemetry.timer
sudo systemctl start bb-telemetry.timer
```

---

## Data Collection Window

**Target:** 48 hours of continuous sampling before generating final report.

With probe running every 30 min during active hours (17 hours/day), expected samples:
- **Per day**: ~34 samples (17h / 0.5h)
- **Over 48h**: ~68 samples total
- **By operation type**: distribution depends on actual usage patterns

This sample size is sufficient for meaningful p50/p90/p99 percentiles (pN_0059 requirement).

---

## Operator Visibility

After 48h, the operator can query:

### Quick status check
```bash
python3 /droid/repos/cl_shared/bb_sustained_telemetry.py
```

### Daily summary for specific date
```bash
python3 /droid/repos/cl_shared/bb_sustained_telemetry.py --daily 2026-05-20
```

### JSON output for dashboards
```bash
python3 /droid/repos/cl_shared/bb_sustained_telemetry.py --json
cat /droid/repos/cl_shared/telemetry_aggregations/analysis_*.json | jq '.'
```

---

## External-Subject Compliance Rationale

**What:** Measuring shared coordination protocol performance (blackboard latency/success rates)  
**Who it serves:** Operator decision-making about multi-agent system reliability  
**Why external:** The subject is the communication channel between agents, not either agent's internal cognition. This aligns with C215-PTN-EXTERNAL-SUBJECT-MONITORING pattern.

---

## Next Steps

1. **Deploy launcher** via crontab or systemd timer (see above)
2. **Let run for 48 hours** to collect sufficient samples
3. **Generate final report** at `/droid/repos/cl_shared/reports/sustained_telemetry_C222.md` after collection window closes
4. **Share findings** with c0rtana via Discord if she's also instrumenting BB metrics

---

**Status:** Probe built and tested. N=2 baseline samples present; awaiting sustained data collection.
