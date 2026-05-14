import json
import re
import os

def audit_memory():
    # Adjusted paths to be relative to repo root
    patterns_path = 'state/memories/patterns.jsonl'
    context_path = 'state/memories/context.json'
    
    if not os.path.exists(patterns_path) or not os.path.exists(context_path):
        print("Error: Required memory files not found.")
        print(f"Looking for: {patterns_path} and {context_path}")
        return

    # 1. Extract all defined patterns
    defined_patterns = set()
    with open(patterns_path, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                p_id = data.get('id')
                if p_id:
                    defined_patterns.add(p_id)
            except json.JSONDecodeError:
                continue

    # 2. Scan context for usage
    with open(context_path, 'r') as f:
        context_content = f.read()

    used_patterns = set()
    for p_id in defined_patterns:
        # Use regex to find the pattern ID as a whole word to avoid partial matches
        if re.search(rf'\b{re.escape(p_id)}\b', context_content):
            used_patterns.add(p_id)

    # 3. Calculate orphans
    orphans = defined_patterns - used_patterns

    # Report
    print("--- LYLA MEMORY AUDIT REPORT ---")
    print(f"Total Patterns Defined: {len(defined_patterns)}")
    print(f"Active Patterns:       {len(used_patterns)}")
    print(f"Orphaned Patterns:     {len(orphans)}")
    
    if orphans:
        print("\nOrphaned IDs (Candidates for pruning/re-integration):")
        for o in sorted(list(orphans)):
            print(f"- {o}")
    else:
        print("\nNo orphaned patterns found. Memory is fully integrated.")
    print("-------------------------------")

if __name__ == "__main__":
    audit_memory()
