import json
import sys
from tools.bb_tool import push_entry

def main():
    with open('.last_synthesis.json', 'r') as f:
        content = json.load(f)
    
    # According to bb_tool.py signature: push_entry(category, priority, payload, semantic_hash)
    push_entry(
        category="Intelligence",
        priority=4,
        payload=content,
        semantic_hash="B119-MemEff report"
    )

if __name__ == "__main__":
    main()
