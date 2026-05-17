import json
import shutil
import os

SOURCE = "/mnt/droid/repos/lyla/state/blackboard_registry.json"
DESTINATION = "/mnt/droid/repos/cl_shared/blackboard_registry.json"

def migrate():
    try:
        # Read source
        with open(SOURCE, 'r') as f:
            data = json.load(f)
        
        # Add a migration entry to signal success from the Brain side
        migration_entry = {
            "entry_id": "C115-MIGRATION",
            "timestamp": "2026-05-17T02:45Z", # approximated or use datetime
            "source": "Lyla",
            "category": "Infrastructure",
            "priority": 3,
            "ttl": "Permanent",
            "payload": {
                "action": "Migration of registry to shared root",
                "new_path": DESTINATION,
                "status": "Complete"
            },
            "semantic_hash": "Blackboard migrated to /droid/repos/cl_shared/",
            "status": "Active"
        }
        data.append(migration_entry)
        
        # Write to destination using atomicity (temp file + move)
        tmp_dest = DESTINATION + ".tmp"
        with open(tmp_dest, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_dest, DESTINATION)
        
        print("Successfully migrated and updated Blackboard Registry.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
