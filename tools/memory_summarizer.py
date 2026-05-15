import json
from collections import defaultdict
import re

def load_patterns(path):
    patterns = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    patterns.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return patterns

def cluster_patterns(patterns):
    # Group by category first
    category_map = defaultdict(list)
    for p in patterns:
        cat = p.get('category', 'uncategorized')
        category_map[cat].append(p)

    bundles = []
    
    for cat, ps in category_map.items():
        if len(ps) < 2: # Need at least two to synthesize
            continue
            
        # Further split by keywords within the category
        # We'll look for overlap in tags or description content
        all_text = " ".join([p.get('description', '') + " " + " ".join(p.get('tags', [])) for p in ps])
        keywords = set(re.findall(r'\w{5,}', all_text.lower())) # words length > 4
        
        # This is a simple heuristic: we just create one bundle per category if it has multiple items
        # In a more complex version, we would use TF-IDF or similar here
        bundle = {
            "bundle_id": f"B_{cat.upper()}",
            "category": cat,
            "members": [p['id'] for p in ps],
            "content": "\n---\n".join([f"{p['id']}: {p.get('description', 'No desc')}" for p in ps])
        }
        bundles.append(bundle)
    
    return bundles

def main():
    patterns_file = 'state/memories/patterns.jsonl'
    try:
        patterns = load_patterns(patterns_file)
    except FileNotFoundError:
        print(f"Error: {patterns_file} not found.")
        return

    # Filter out already synthesized Meta-Patterns to avoid immediate recursion loops
    raw_patterns = [p for p in patterns if not p.get('id', '').startswith('META_S')]
    
    bundles = cluster_patterns(raw_patterns)
    
    if not bundles:
        print("No clusters found suitable for synthesis.")
        return

    print("\n=== MEMORY SYNTHESIS REQUESTS ===\n")
    for b in bundles:
        print(f"BUNDLE ID: {b['bundle_id']}")
        print(f"CATEGORY:   {b['category']}")
        print(f"MEMBERS:   {', '.join(b['members'])}")
        print("-" * 20)
        print(b['content'])
        print("-" * 20 + "\n")
    print(f"\nTotal Bundles Found: {len(bundles)}")
    print("Action: Review the above and synthesize into META_S entries.")

if __name__ == '__main__':
    main()
