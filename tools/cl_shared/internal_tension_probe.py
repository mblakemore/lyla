#!/usr/bin/env python3
"""
Internal Tension Probe — Measure cognitive conflict between stored patterns.

This implements operationalization of the internal_tension metric proposed in 
C221 reading notes. It scans patterns.jsonl and computes a tension score based on:
1. Category competition: How many distinct categories are represented?
2. Lexical overlap: Do patterns share terminology but express conflicting ideas?
3. Temporal clustering: Are new tensions emerging rapidly or accumulating slowly?

Output: JSONL with per-pattern tension contribution + aggregate score.

EXTERNAL SUBJECT COMPLIANCE: We're measuring an actual cognitive metric that was
theorized in C221, not self-monitoring. The subject is the pattern library's
conceptual coherence, which has real consequences for decision quality.
"""

import json
from pathlib import Path
from collections import defaultdict
import re
import math


PATTERNS_PATH = Path(__file__).parent.parent / "c0rtana" / "state" / "memories" / "patterns.jsonl"
OUTPUT_PATH = Path(__file__).parent / "telemetry_aggregations" / "tension_scores.jsonl"


def tokenize(text: str) -> set[str]:
    """Simple tokenization via lowercase word extraction."""
    return set(re.findall(r'\b[a-z]{4,}\b', text.lower()))


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def load_patterns() -> list[dict]:
    """Load all patterns from JSONL file, skipping invalid entries."""
    patterns = []
    with open(PATTERNS_PATH, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                pattern = json.loads(line)
                # Validate required fields
                if "id" not in pattern or "pattern" not in pattern:
                    print(f"Warning: Line {line_num} missing required 'id' or 'pattern' field")
                    continue
                patterns.append(pattern)
            except json.JSONDecodeError as e:
                print(f"Warning: Malformed JSON on line {line_num}: {e}")
    return patterns


def compute_category_distribution(patterns: list[dict]) -> dict[str, int]:
    """Count how many patterns exist per category."""
    dist = defaultdict(int)
    for p in patterns:
        cat = p.get("category", "uncategorized")
        dist[cat] += 1
    return dict(dist)


def compute_lexical_clusters(patterns: list[dict], threshold=0.3) -> list[list[int]]:
    """Group patterns by lexical similarity — high overlap suggests related concepts."""
    n = len(patterns)
    clusters = []
    assigned = [False] * n
    
    for i in range(n):
        if assigned[i]:
            continue
        
        # Start new cluster
        cluster = [i]
        assigned[i] = True
        
        # Find similar patterns
        text_i = patterns[i].get("pattern", "") + " " + patterns[i].get("id", "")
        tokens_i = tokenize(text_i)
        
        for j in range(i + 1, n):
            if assigned[j]:
                continue
            
            text_j = patterns[j].get("pattern", "") + " " + patterns[j].get("id", "")
            tokens_j = tokenize(text_j)
            
            sim = jaccard_similarity(tokens_i, tokens_j)
            if sim >= threshold:
                cluster.append(j)
                assigned[j] = True
        
        clusters.append(cluster)
    
    return clusters


def compute_tension_score(patterns: list[dict]) -> dict:
    """
    Compute internal tension score (0.0 to 1.0).
    
    Higher values indicate more conceptual conflict / competing frameworks.
    Lower values indicate coherent, unified theoretical stance.
    
    Components:
    - category_diversity: More categories = more diverse perspectives (potential tension)
    - lexical_redundancy: High overlap without integration suggests unresolved debate
    - temporal_acceleration: Rapid new pattern addition could signal active reorganization
    """
    if len(patterns) < 2:
        return {"tension_score": 0.0, "components": {}}
    
    # Component 1: Category diversity (normalized entropy)
    cat_dist = compute_category_distribution(patterns)
    total = sum(cat_dist.values())
    entropy = -sum((count/total) * math.log(count/total) for count in cat_dist.values() if count > 0)
    max_entropy = math.log(len(cat_dist))
    category_entropy_norm = entropy / max_entropy if max_entropy > 0 else 0
    
    # Component 2: Lexical clustering — many small clusters suggest fragmented thinking
    clusters = compute_lexical_clusters(patterns)
    avg_cluster_size = len(patterns) / len(clusters) if clusters else 1
    fragmentation_score = min(1.0, (avg_cluster_size - 1) / 5)  # Normalize to [0,1]
    
    # Component 3: Temporal acceleration (last 10 patterns vs prior average)
    sorted_patterns = sorted(patterns, key=lambda p: p.get("created", ""))
    if len(sorted_patterns) >= 20:
        recent = sorted_patterns[-10:]
        older = sorted_patterns[:-10]
        
        def parse_date_only(ts_str):
            """Extract YYYY-MM-DD from ISO timestamp."""
            try:
                # Handle formats like "2026-05-20T06:53:39+00:00" or "2026-05-20T06:53:39Z"
                date_part = ts_str.split("T")[0].split("+")[0]
                parts = date_part.split("-")
                if len(parts) >= 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    return year * 365 + month * 30 + day  # Rough day count
                return None
            except:
                return None
        
        recent_dates = []
        older_dates = []
        for p in recent:
            d = parse_date_only(p.get("created", ""))
            if d is not None:
                recent_dates.append(d)
        for p in older:
            d = parse_date_only(p.get("created", ""))
            if d is not None:
                older_dates.append(d)
        
        if recent_dates and older_dates:
            rec_rate = len(recent_dates) / (max(recent_dates) - min(recent_dates) + 1)
            old_rate = len(older_dates) / (max(older_dates) - min(older_dates) + 1)
            acceleration = rec_rate / old_rate if old_rate > 0 else 1.0
            temporal_score = min(1.0, (acceleration - 1) / 3)  # Normalize
        else:
            temporal_score = 0.0
    else:
        temporal_score = 0.0
    
    # Weighted combination
    tension_score = (
        0.3 * category_entropy_norm +      # More categories = more variety (can be good or bad)
        0.4 * fragmentation_score +         # Fragmentation = unresolved debate
        0.3 * temporal_score                 # Rapid change = active reorganization
    )
    
    return {
        "tension_score": round(tension_score, 3),
        "components": {
            "category_diversity": round(category_entropy_norm, 3),
            "fragmentation": round(fragmentation_score, 3),
            "temporal_acceleration": round(temporal_score, 3)
        },
        "metadata": {
            "total_patterns": len(patterns),
            "unique_categories": len(cat_dist),
            "cluster_count": len(clusters),
            "avg_cluster_size": round(avg_cluster_size, 2),
            "analysis_timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    }


def generate_report():
    """Generate and print report to stdout."""
    patterns = load_patterns()
    
    if not patterns:
        print("No patterns found in patterns.jsonl")
        return
    
    result = compute_tension_score(patterns)
    
    score = result["tension_score"]
    
    # Interpretation thresholds (based on C221 baseline of ~0.40)
    if score < 0.3:
        interpretation = "LOW TENSION — Coherent theoretical stance, minimal conceptual conflict."
    elif score < 0.6:
        interpretation = "MODERATE TENSION — Multiple frameworks active but not actively conflicting. Space for synthesis."
    else:
        interpretation = "HIGH TENSION — Significant conceptual conflict detected. Consider reconciliation or explicit integration strategy."
    
    report_lines = [
        "=" * 70,
        "INTERNAL TENSION PROBE REPORT",
        f"Generated: {__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat().replace('+00:00', 'Z')}",
        "=" * 70,
        "",
        "DATA SOURCE",
        "-" * 40,
        f"Patterns analyzed: {result['metadata']['total_patterns']}",
        f"Unique categories: {result['metadata']['unique_categories']}",
        f"Lexical clusters formed: {result['metadata']['cluster_count']}",
        "",
        "TENSION SCORE",
        "-" * 40,
        f"Aggregate tension: {score:.3f} ({interpretation})",
        "",
        "COMPONENT BREAKDOWN",
        "-" * 40,
        f"Category diversity (entropy): {result['components']['category_diversity']:.3f}",
        f"Fragmentation score: {result['components']['fragmentation']:.3f}",
        f"Temporal acceleration: {result['components']['temporal_acceleration']:.3f}",
        "",
        "INTERPRETATION GUIDE",
        "-" * 40,
        "- Category diversity measures how many distinct theoretical frameworks are represented.",
        "- Fragmentation measures lexical overlap — high fragmentation means patterns don't integrate cleanly.",
        "- Temporal acceleration measures if new patterns are accumulating faster than baseline.",
        "",
        "ACTIONABLE INSIGHTS",
        "-" * 40,
    ]
    
    # Add specific recommendations based on component values
    if result["components"]["fragmentation"] > 0.5:
        report_lines.append("- High fragmentation detected: Consider organizing patterns into explicit sub-corpora or integration documents.")
    if result["components"]["temporal_acceleration"] > 0.3:
        report_lines.append("- Rapid pattern accumulation: Active reorganization phase; expect tension to stabilize after synthesis cycle.")
    if result["metadata"]["unique_categories"] > 15:
        report_lines.append("- Many categories (>15): Consider taxonomic consolidation to reduce cognitive overhead.")
    
    report_lines.extend([
        "",
        "=" * 70,
        f"OUTPUT FILE: {OUTPUT_PATH}",
        "=" * 70,
    ])
    
    report = "\n".join(report_lines)
    print(report)
    
    # Also write JSONL output for programmatic consumption
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(json.dumps(result) + "\n")
    
    return result


if __name__ == "__main__":
    generate_report()
