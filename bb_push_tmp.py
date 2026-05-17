import sys
from /droid/repos/cl_shared/shared_state_client import SharedStateClient

def main():
    client = SharedStateClient()
    # We'll use this to push our update later. 
    # For now, just confirming it works by pulling a few things.
    items = client.pull(min_priority=5)
    print(f\"Retrieved {len(items)} high priority entries.\")
    for i in items[-2:]: # show last two
        print(f\"{i['entry_id']} - {i['semantic_hash']}\")

if __name__ == '__main__':
    main()
