import os
import json
from datetime import datetime

# The "External Value" goal here is to provide a concise, human-readable briefing of recent progress 
# without forcing the operator to parse multiple JSON files or long log streams.

def get_last_cycles(count=5):
    log_path = 'logs/consciousness.log'
    if not os.path.exists(log_path):
        return []
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    # Group lines by cycle (C##:)
    cycles = {}
    current_cycle = None
    for line in lines:
        match = r'^C(\d+): (.*)'
        # Simple heuristic for consciousness.log format
        if line.startswith('C'):
             parts = line.split(': ', 1)
             if len(parts) == 2 and parts[0].startswith('C'):
                 current_cycle = parts[0]
                 cycles[current_cycle] = [line.strip()]
                 continue
        if current_cycle:
            cycles[current_cycle].append(line.rstrip())
    
    sorted_keys = sorted(cycles.keys(), reverse=True)
    results = []
    for key in sorted_keys[:count]:
        results.append((key, cycles[key]))
    return results

def get_focus():
    try:
        with open('state/focus.json', 'r') as f:
            return json.load(f)
    except: return {}

def get_cur_state():
    try:
        with open('state/current-state.json', 'r') as f:
            return json.load(f)
    except: return {}

def main():
    print("====================================================")
    print(f"  LYLA OPERATIONAL DIGEST - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("====================================================")
    
    focus = get_focus()
    state = get_cur_state()
    
    print(f"\n🎯 CURRENT FOCUS:\n   {focus.get('current_goal', 'Unknown')}")
    print(f"📍 NEXT MILESTONE: {focus.get('next_milestone', 'Unknown')}")
    
    print("\n🛠️ RECENT STATE:")
    print(f"   Cycle: {state.get('cycle', 'N/A')} | Status: {state.get('status', 'N/A')}")
    print(f"   Last Act: {state.get('last_action', 'N/A')}")
    
    print("\n📜 LAST 5 CYCLE summaries (Consciousness stream):")
    recent = get_last_cycles(5)
    for c, content in recent:
        summary = content[0] # Usually the cycle header line
        print(f"   - {summary}")

    print("\n----------------------------------------------------")
    print("  End of Digest.")
    print("====================================================")

if __name__ == '__main__':
    main()
