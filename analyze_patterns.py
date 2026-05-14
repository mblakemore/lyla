import json
import os
from collections import defaultdict
from datetime import datetime

def load_patterns(path):
    patterns = []
    if not os.path.exists(path):
        return patterns
    with open(path, 'r') as f:
        for line in f:
            try:
                patterns.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return patterns

def analyze_higher_order_patterns(patterns):
    """
    Detects higher-order patterns by analyzing semantic overlap 
    and signal signatures across memory clusters.
    """
    # Simple keyword extraction for 'semantic' analysis
    keywords = ["telemetry", "visualization", "cognitive", "velocity", "decay", "perturbation", "mapper"]
    
    cluster_map = defaultdict(list)
    entry_vectors = {}
    
    # Step 1: Vectorize and Cluster
    for i, p in enumerate(patterns):
        text = (p.get("pattern", "") + " " + p.get("category", "")).lower()
        vector = {k: text.count(k) for k in keywords}
        entry_vectors[i] = vector
        
        cat = p.get("category", "unknown")
        cluster_map[cat].append(i)
        
    # Step 2: Adjacency Matrix / Correlation Strength
    correlations = []
    for i in range(len(patterns)):
        for j in range(i + 1, len(patterns)):
            v1, v2 = entry_vectors[i], entry_vectors[j]
            # Dot product of vectors as a simple similarity measure
            sim = sum(v1[k] * v2[k] for k in keywords)
            if sim > 0:
                correlations.append({
                    "pair": [i, j],
                    "strength": sim,
                    "clusters": [patterns[i].get("category"), patterns[j].get("category")]
                })

    # Step 3: Identify Higher-Order Patterns (Triangles/Cycles)
    # A HOP is defined here as a bridge between 3+ disparate clusters with shared signal characteristics
    higher_order = []
    seen_triplets = set()
    
    for corr in correlations:
        p1, p2 = corr["pair"]
        # Look for a third point p3 that connects to both p1 and p2
        for other in range(len(patterns)):
            if other == p1 or other == p2: continue
            
            # Check if p1-other and p2-other also correlate
            v1, v_oth = entry_vectors[p1], entry_vectors[other]
            v2, v_oth2 = entry_vectors[p2], entry_vectors[other]
            
            sim1 = sum(v1[k] * v_oth[k] for k in keywords)
            sim2 = sum(v2[k] * v_oth2[k] for k in keywords)
            
            if sim1 > 0 and sim2 > 0:
                triplet = tuple(sorted([p1, p2, other]))
                if triplet not in seen_triplets:
                    clusters = {patterns[p1].get("category"), patterns[p2].get("category"), patterns[other].get("category")}
                    if len(clusters) >= 2: # Bridges at least two clusters
                        higher_order.append({
                            "pattern_id": f"HOP_{len(higher_order)+1:03}",
                            "involved_indices": list(triplet),
                            "involved_clusters": list(clusters),
                            "signal_signature": "cross_cluster_resonance",
                            "strength": (corr["strength"] + sim1 + sim2) / 3,
                            "created": datetime.now().isoformat()
                        })
                        seen_triplets.add(triplet)

    return higher_order

def main():
    patterns_path = "state/memories/patterns.jsonl"
    output_path = "state/correlations.json"
    
    print(f"Analyzing {patterns_path}...")
    patterns = load_patterns(patterns_path)
    
    if not patterns:
        print("No patterns found to analyze.")
        return

    hops = analyze_higher_order_patterns(patterns)
    
    result = {
        "last_analysis": datetime.now().isoformat(),
        "total_patterns_scanned": len(patterns),
        "higher_order_patterns": hops
    }
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Successfully identified {len(hops)} higher-order patterns. Saved to {output_path}")

if __name__ == "__main__":
    main()
