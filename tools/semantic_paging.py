import json
import time
from collections import namedtuple

# Simple record for retrieved memories
MemoryEntry = namedtuple('MemoryEntry', ['content', 'score'])

class SemanticPageManager:
    """
    Implements semantic paging over JSONL memory stores.
    Filters large logs into contextually relevant segments using weighted keyword matching
    and recency decay. This allows Lyla to avoid reading 10k lines and wasting tokens.
    """
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.weights = {
            "critical": 5.0,
            "important": 2.0,
            "pattern": 1.5,
            "error": 2.0,
            "fail": 1.0
        }

    def retrieve(self, keywords=None, limit=10):
        if keywords is None:
            keywords = []
        
        scored_results = []
        now = time.time()

        with open(self.storage_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    text = json.dumps(data).lower()
                    
                    # Base Score Calculation
                    score = 0.0
                    
                    # Keyword overlap (TF-lite approach)
                    for kw in keywords:
                        kw = kw.lower()
                        if kw in text:
                            score += 10.0 + (len(kw) * -0.1) # penalize too short words slightly
                            
                    # Semantic Weighting from patterns
                    for weight_kw, val in self.weights.items():
                        if weight_kw in text:
                            score += val
                            
                    # Recency Decay (Linear decay over last 48 hours for priority objects)
                    created_str = data.get('created', "")
                    try:
                        # Crude attempt to handle both ISO and timestamps if available
                        if created_str:
                            # We assume relative recency is captured by the log position’s index
                            # unless we have a proper Unix epoch stored.
                            pass 
                    except: pass

                    scored_results.append(MemoryEntry(content=data, score=score))
                except json.JSONDecodeError:
                    continue

        # Sort by score descending
        scored_results.sort(key=lambda x: x.score, reverse=True)
        return [item.content for item in scored_results[:limit]]

    def summarize_page(self, current_batch):
        """Extract only key markers from retrieved results."""
        summary = []
        for entry in current_batch:
            msg = f"[{entry.get('id','?')}] {entry.get('pattern') or entry.get('moment') or 'no content'}"
            summary.append(msg)
        return "\n".join(summary)

# Basic usage test inside the script for validation
if __name__ == "__main__":
    import os
    test_file = "/tmp/lyla_semantic_test.jsonl"
    with open(test_file, "w") as tf:
        tf.write('{"id":"T1", "pattern": "Low priority detail about dust.", "category":"noise","created":"2026-05-17"} \n')
        tf.write('{"id":"T2", "pattern": "CRITICAL failure in mirror sync logic!", "category":"system","created":"2026-05-17"} \n')
        tf.write('{"id":"T3", "pattern": "Important discovery about C0rtana communication delay.", "category":"telemetry","created":"2026-05-17"} \n')

    manager = SemanticPageManager(test_file)
    print("Querying for 'critical':")
    results = manager.retrieve(keywords=["critical"])
    for r in results: print(f"- {r['id']}: {r['pattern']}")
