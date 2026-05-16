import json
import os
from datetime import datetime

def digest():
    print("Lyla External Digester v1.0")
    print("---------------------------")
    
    # 1. Identify High Value Patterns (confidence >= 0.9 + created recently)
    patterns = []
    if os.path.exists('state/memories/patterns.jsonl'):
        with open('state/memories/patterns.jsonl', 'r') as f:
            for line in f:
                p = json.loads(line)
                if p.get('confidence', 0) >= 0.9:
                    patterns.append(f"- {p['id']}: {p['pattern']}")
    
    # 2. Identify Current Focus
    focus = "Unknown"
    if os.path.exists('state/focus.json'):
        with open('state/focus.json', 'r') as f:
            data = json.load(f)
            focus = data.get('current_goal', 'No explicit goal set')

    # 3. Build Report
    report = f"# Operational Digest - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += f"## CURRENT FOCUS\n{focus}\n\n"
    report += "## HIGH-SIGNAL INSIGHTS (Last Cycled)\n"
    report += "\n".join(patterns[-5:]) if patterns else "No high-signal patterns yet."
    
    return report

if __name__ == "__main__":
    print(digest())
