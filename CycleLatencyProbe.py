#!/usr/bin/env python3
"""CycleLatencyProbe: measure cycle-to-cycle latencies and identify bottlenecks."""
import subprocess
from datetime import datetime

def get_git_log_entries():
    """Extract timestamps from recent git commits to analyze cadence."""
    cmd = ["git", "log", "--format=%ai %s", "-n", "50"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/mnt/droid/repos/lyla")
    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip(): continue
        
        try:
            # Format: "2026-05-20 06:14:57 +0000 C211: Message..."
            # Timestamp is exactly first 3 space-separated words
            parts = line.split(" ", 3)  # Split into [date time tz rest...] max 4 parts
            if len(parts) < 4: continue
            
            date_part, time_part, tz_part = parts[0], parts[1], parts[2]
            msg = parts[3]
            
            # Combine timestamp components
            ts_full = f"{date_part} {time_part} {tz_part}"
            
            # Parse the datetime part (ignore timezone for simplicity)
            ts_dt_part = f"{date_part} {time_part[:8]}"
            ts = datetime.strptime(ts_dt_part, "%Y-%m-%d %H:%M:%S")
            
            entries.append({"timestamp": ts, "message": msg})
        except Exception as e:
            print(f"Parse error on line {line!r}: {e}")
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)

def compute_gaps(entries):
    """Compute latencies between consecutive cycles."""
    gaps = []
    for i in range(len(entries) - 1):
        gap_ms = (entries[i]["timestamp"] - entries[i+1]["timestamp"]).total_seconds() * 1000
        gaps.append({
            "from_msg": entries[i]["message"][:50],
            "to_msg": entries[i+1]["message"][:50],
            "gap_ms": gap_ms,
            "gap_min": gap_ms / 60_000
        })
    return gaps

def main():
    entries = get_git_log_entries()
    if not entries:
        print("No commits found!")
        return
    
    print(f"\n{'='*70}\nRecent Cycle Cadence Analysis ({len(entries)} commits)\n{'='*70}\n")
    
    # Extract cycle numbers from git log titles (C123 format) for context
    import re
    
    cycle_map = {}
    for entry in entries:
        match = re.search(r'\b(C\d+):', entry["message"])
        if match:
            cid = match.group(1)
            cn = int(cid[1:])  # extract number from "C211"
            cycle_map[cn] = entry

    # Print recent cycle messages with their cycle annotations.
    # Only cycles that have explicit C### references will show numbers; others just timestamps.
    
    print("\nRECENT CYCLES:")
    for entry in entries[:15]:
        ts_str = entry["timestamp"].strftime("%Y-%m-%d %H:%M")
        msg_raw = entry["message"]
        
        # Look up cycle number from our map (exact match on dict value)
        cycle_cid = None
        for cid, centry in cycle_map.items():
            if centry == entry:
                cycle_cid = f"C{cid}"
                break
        
        prefix = f"{cycle_cid:>5} " if cycle_cid else "      "
        line = f"  {prefix}{ts_str} | {msg_raw}"
        
        # Truncate long lines to ~80 chars per column
        if len(line) > 90:
            line = line[:86] + "..."
        print(line)
    
    # Compute gaps
    gaps = compute_gaps(entries)
    print(f"\n{'='*70}\nLATECY BENCHMARKS (N={len(gaps)})\n{'='*70}")
    
    min_gap = min(g["gap_ms"] for g in gaps)
    max_gap = max(g["gap_ms"] for g in gaps)
    avg_gap = sum(g["gap_ms"] for g in gaps) / len(gaps)
    median_gap = sorted(g["gap_ms"] for g in gaps)[len(gaps)//2]
    
    print(f"Min gap:   {min_gap:,.0f} ms  ({min_gap/60_000:.2f} min)")
    print(f"Avg gap:   {avg_gap:,.0f} ms  ({avg_gap/60_000:.2f} min)")
    print(f"Median:    {median_gap:,.0f} ms  ({median_gap/60_000:.2f} min)")
    print(f"Max gap:   {max_gap:,.0f} ms  ({max_gap/60_000:.2f} min)\n")
    
    # Identify outliers (>2x avg)
    threshold = 2 * avg_gap
    outliers = [g for g in gaps if g["gap_ms"] > threshold]
    if outliers:
        print(f"\n⚠️  OUTLIERS (gaps > {threshold:,.0f}ms):")
        for o in outliers[:5]:
            print(f"  [{o['from_msg']} → {o['to_msg']}] = {o['gap_ms']:,.0f}ms ({o['gap_min']:.1f}m)")

if __name__ == "__main__":
    main()