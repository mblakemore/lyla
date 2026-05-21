import json
import os
import tempfile
from datetime import datetime

class SharedStateClient:
    """
    Atomic client for managing entries on the Shared Blackboard.
    Designed to prevent corruption during concurrent read/writes across agents.
    """
    def __init__(self, registry_path="/droid/repos/cl_shared/blackboard_registry.json"):
        self.registry_path = registry_path

    def _read_all(self):
        if not os.path.exists(self.registry_path):
            return []
        try:
            with open(self.registry_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def push(self, entry_id, category, priority, payload, semantic_hash=None, ttl="Permanent", source="C0rtana"):
        data = self._read_all()
        
        new_entry = {
            "entry_id": entry_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": source,
            "category": category,
            "priority": priority,
            "ttl": ttl,
            "payload": payload,
            "semantic_hash": semantic_hash or "Auto-generated during update",
            "status": "Active"
        }
        
        data.append(new_entry)
        
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.registry_path))
        try:
            with os.fdopen(fd, 'w') as tmp:
                json.dump(data, tmp, indent=2)
            os.replace(temp_path, self.registry_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
            
        return True

    def pull(self, min_priority=4, status="Active", categories=None):
        data = self._read_all()
        results = []
        for entry in data:
            if (entry.get("priority", 0) >= min_priority and 
                entry.get("status") == status):
                if categories is None or entry.get("category") in categories:
                    results.append(entry)
        return results

    def scrub(self, category):
        data = self._read_all()
        updated = False
        for entry in data:
            if entry.get("category") == category and entry.get("status") == "Active":
                entry["status"] = "Archived"
                updated = True
        
        if updated:
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        return updated

if __name__ == "__main__":
    client = SharedStateClient()
    print("SharedStateClient initialized.")
    print(f"Registry path: {client.registry_path}")