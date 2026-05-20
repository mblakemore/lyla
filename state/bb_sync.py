#!/usr/bin/env python3
"""
Lyla Blackboard Sync Tool — pulls entries from cl_shared/blackboard_tool.py registry
and merges into local state/blackboard_registry.json with deduplication by entry_id.
Runs during PERCEIVE phase before reading patterns.mdn.
"""

import json
import os
import sys
from datetime import datetime

# Paths
CL_SHARED_REGISTRY = "/droid/repos/cl_shared/blackboard_registry.json"
LYLA_REGISTRY = "/droid/repos/lyla/state/blackboard_registry.json"

def read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return []

def write_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

def sync_blackboards():
    """Merge cl_shared registry (c0rtana's active list) into Lyla's."""
    
    remote_data = read_json(CL_SHARED_REGISTRY) or []
    local_data = read_json(LYLA_REGISTRY) or []
    
    # Deduplicate by entry_id — prefer remote version (more authoritative)
    local_by_id = {e.get("entry_id"): e for e in local_data}
    merged_by_id = {**local_by_id}  # Start with all local entries
    
    synced_count = 0
    new_from_remote = 0
    
    for entry in remote_data:
        eid = entry.get("entry_id")
        if not eid:
            continue
            
        if eid in merged_by_id:
            # Entry already exists locally — keep it (or optionally update from remote)
            synced_count += 1
        else:
            # New entry from remote — add it
            merged_by_id[eid] = entry.copy()
            merged_by_id[eid]["synced_at"] = datetime.utcnow().isoformat() + "Z"
            new_from_remote += 1
    
    # Write back
    merged_list = list(merged_by_id.values())
    write_json(LYLA_REGISTRY, merged_list)
    
    print(f"[SYNC] Cl-shared→Lyla: {new_from_remote} new entries, {synced_count} existing synced")
    return len(remote_data), new_from_remote

if __name__ == "__main__":
    sync_blackboards()
