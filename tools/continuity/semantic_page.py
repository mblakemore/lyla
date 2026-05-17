import json

def get_compact_context(cycle_index):
    """
    Example implementation of Semantic Paging:
    Instead of loading all history, we filter patterns by high confidence or recent tags.
    """
    relevant = []
    try:
        with open("state/memories/patterns.jsonl", "r") as f:
            for line in f:
                data = json.loads(line)
                # Heuristic: only pull patterns that are highly confident and not stale
                if data.get("confidence", 0) > 0.8:
                    relevant.append(data)
    except FileNotFoundError:
        pass
    
    return {
        "active_cycle": cycle_index,
        "compressed_knowledge": relevant[-5:], # Last 5 high-signal items
        "summary": "Context pruned via semantic paging to preserve LLM attention window."
    }

if __name__ == "__main__":
    print(json.dumps(get_compact_context(112), indent=2))
