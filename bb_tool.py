import json
import sys
from datetime import datetime

try:
    sys.path.append('/droid/repos/cl_shared/')
    from shared_state_client import SharedStateClient
except ImportError as e:
    print(f"Critical Error importing SharedStateClient: {e}", file=sys.stderr)
    sys.exit(1)

def main():
    client = SharedStateClient()
    args = sys.argv[1:]

    if not args:
        print("Usage:\n push <priority> <category> \"<payload_json\"> [semantic_hash]\n pull [<min_priority>]")
        sys.exit(1)

    cmd = args[0]

    if cmd == "push":
        # Usage: python bb_tool.py push 5 Intelligence '{"key":"val"}' "Shorthand for entry"
        try:
            prio = int(args[1])
            cat = args[2]
            payload_str = args[3]
            sem_hash = args[4] if len(args) > 4 else ""
            
            # Attempt to parse payload as JSON, otherwise store as string
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                payload = payload_str

            eid = f"L{datetime.now().strftime('%m%d-%H%M')}-{os.urandom(2).hex()}" \
                   if 'os' in globals() else f"{int(datetime.timestamp(datetime.utcnow()))}"
            # Actually just use a timestamp-based one since os might not be imported
            import os # ensure it's here
            eid = f"{id(main)}-{int(datetime.timestamp(datetime.utcnow()))}"
            
            success = client.push(entry_id=eid, category=cat, priority=prio, payload=payload, semantic_hash=sem_hash, source="Lyla")
            if success:
                print(f"Succeeded pushing {eid} to BB.")
        except Exception as e:
            print(f"Push failed: {e}")

    elif cmd == "pull":
        min_prio = int(args[1]) if len(args) > 1 else 4
        entries = client.pull(min_priority=min_prio)
        print(json.dumps(entries, indent=2))

if __name__ == "__main__":
    main()
