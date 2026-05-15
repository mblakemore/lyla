import json
import os

MEM_DIR = "state/memories"
INDEX_FILE = os.path.join(MEM_DIR, "index.json")

def build_index():
    """
    Scans all .jsonl files in state/memories and builds a map of tags/categories 
    to specific line numbers for O(1) retrieval.
    """
    if not os.path.exists(MEM_DIR):
        return f"Error: {MEM_DIR} does not exist."
        
    index = {"pages": {}, "metadata": {"last_updated": None, "total_entries": 0}}
    
    # Iterate through all .jsonl files in memory directory
    for filename in os.listdir(MEM_DIR):
        if filename.endswith(".jsonl"):
            file_path = os.path.join(MEM_DIR, filename)
            try:
                with open(file_path, 'r') as f:
                    for line_no, line in enumerate(f):
                        line = line.strip()
                        if not line: continue
                        
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                            
                        # Extract indexing keys
                        tags = entry.get("tags", [])
                        category = entry.get("category") # Can be None
                        id_val = entry.get("id", f"{filename}:{line_no}")

                        # Map category if it exists
                        if category:
                            cat_key = f"cat:{category}"
                            if cat_key not in index["pages"]:
                                index["pages"][cat_key] = []
                            index["pages"][cat_key].append({"file": filename, "line": line_no, "id": id_val})
                        
                        # Map individual tags
                        for tag in tags:
                            tag_key = f"tag:{tag}"
                            if tag_key not in index["pages"]:
                                index["pages"][tag_key] = []
                            index["pages"][tag_key].append({"file": filename, "line": line_no, "id": id_val})
            except Exception as e:
                print(f"Could not open {filename}: {e}")

    import datetime
    index["metadata"]["last_updated"] = datetime.datetime.utcnow().isoformat() + 'Z'
    index["metadata"]["total_entries"] = sum(len(v) for v in index["pages"].values())
    
    with open(INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=4)
    
    return f"Index built successfully. {len(index['pages'])} pages mapped."

if __name__ == "__main__":
    print(build_index())
