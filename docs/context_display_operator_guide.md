# Context Display Operator Guide

## What This Is

A terminal-native, always-visible presence indicator that shows what Lyla knows about your work state in real-time. Unlike the `context_beacon` CLI which requires explicit invocation, this displays passively whenever you open a terminal.

## Quick Start

```bash
# One-time snapshot
python3 bin/context_display.py

# Auto-refreshing (every 5 seconds)
watch -n 5 'python3 bin/context_display.py'

# Background daemon (logs to stdout, use with nohup)
nohup python3 bin/context_display.py --daemon &
```

## What You'll See

### Header
- **Cycle number**: Current cognitive cycle identifier
- **Phase color**: Green = PERCEIVE/PERSIST, Yellow = DECIDE, Red = ACT, Cyan = REFLECT, Magenta = CONSOLIDATE

### Focus Area
The current priority area — what Lyla thinks you're working on based on recent observations.

### Recent Observations
Last 3 entries from context_trace showing friction points, insights, or questions for you.

### External-Subject Compliance Status
Green checkmark means you're compliant with the Anti-Repetition rule (≤2 cycles since external-subject artifact). Red warning if approaching drift threshold.

### Open Questions
Active uncertainties Lyla has about your workflow that you might want to address in the next cycle.

## Design Rationale

This solves the "context blindness" friction point by making Lyla's knowledge state **always visible** without requiring explicit tool invocation. The compact design (≤24 lines) means it doesn't clutter your terminal but provides situational awareness at a glance.

## Comparison: Context Display vs. Other Tools

| Tool | Invocation | Best For |
|------|-----------|----------|
| `bin/context_display.py` | Always-visible / watch mode | Passive awareness while coding |
| `bin/context_beacon.py` | Explicit CLI call | Deep dive into specific metrics |
| `visualization/context_viewer.html` | Browser tab | Rich visualization with charts |

Choose based on your workflow: passive awareness during active work, deep inspection when needed, or visual dashboard when reviewing trends.

## Troubleshooting

**No data shown?** Run a cycle first — context.json is updated each cycle and contains working memory.

**Colors not displaying?** Your terminal may not support ANSI codes. Use `cat bin/context_display.py | less -R` to view source, or check TERM environment variable.

**Want different refresh rate?** Change `-n 5` in the watch command to any interval you prefer (`-n 10`, `-n 30`, etc.).
