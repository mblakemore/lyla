import json
from tools.semantic_paging import SemanticPageManager

def query(path, keywords):
    sm = SemanticPageManager(path)
    res = sm.retrieve(keywords=keywords, limit=5)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    import sys
    q_path = "/droid/repos/lyla/state/memories/patterns.jsonl"
    kws = sys.argv[1:] if len(sys.argv)>1 else ["blackboard"]
    query(q_path, kws)
