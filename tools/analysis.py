import json
import os
from collections import Counter

def analyze_patterns(filepath):
    """Analyzes the patterns.jsonl file and returns a summary of categories."""
    if not os.path.exists(filepath):
        return "Patterns file not found."
    
    categories = []
    with open(filepath, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                cat = data.get('category', 'unknown')
                categories.append(cat)
            except json.JSONDecodeError:
                continue
    
    counts = Counter(categories)
    sorted_counts = counts.most_common()
    
    report = "### Pattern Category Analysis\n"
    report += "| Category | Count |\n|---|---|\n"
    for cat, count in sorted_counts:
        report += f"| {cat} | {count} |\n"
    
    return report

def analyze_anchors(filepath):
    """Summarizes significant moments from anchors.jsonl."""
    if not os.path.exists(filepath):
        return "Anchors file not found."
    
    moments = []
    with open(filepath, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                moments.append(f"- Cycle {data.get('cycle', 'N/A')}: {data.get('moment', 'Unknown moment')}")
            except json.JSONDecodeError:
                continue
    
    report = "### Anchor Timeline Summary\n"
    report += "\n".join(moments)
    
    return report

if __name__ == "__main__":
    # Relative paths based on repo root
    patterns_path = "state/memories/patterns.jsonl"
    anchors_path = "state/memories/anchors.jsonl"
    
    print("# --- Meta-Cognitive Analysis Report ---\n")
    print(analyze_patterns(patterns_path))
    print("\n")
    print(analyze_anchors(anchors_path))
