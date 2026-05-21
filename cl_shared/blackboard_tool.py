import json
import sys
import argparse
from datetime import datetime
from shared_state_client import SharedStateClient

def main():
    parser = argparse.ArgumentParser(description="Blackboard Management CLI - Tool for Lyla & C0rtana")
    parser.add_argument("--action", choices=["push", "pull", "scrub"], required=True)
    parser.add_argument("--id", help="Entry ID (for push)")
    parser.add_argument("--category", help="Category (for push/scrub)")
    parser.add_argument("--priority", type=int, default=4)
    parser.add_argument("--message", help="Text payload or JSON string (for push)")
    parser.add_argument("--semantic", help="Semantic hash (for push)")
    parser.add_argument("--source", default="C0rtana")
    parser.add_argument("--min-pri", type=int, default=4)
    
    args = parser.parse_args()
    bb = SharedStateClient()

    if args.action == "push":
        # Allow payload to be a raw string or a parsed JSON object if it looks like one
        payload = args.message
        if payload and payload.strip().startswith('{'):
            try:
                payload = json.loads(payload)
            except: pass

        success = bb.push(
            entry_id=args.id or f"AUTO-{int(datetime.now().timestamp())}", 
            category=args.category or "Update",
            priority=args.priority,
            payload=payload,
            semantic_hash=args.semantic,
            source=args.source
        )
        print("SUCCESS" if success else "FAILED")

    elif args.action == "pull":
        entries = bb.pull(min_priority=args.min_pri)
        print(json.dumps(entries, indent=2))

    elif args.action == "scrub":
        if not args.category:
            print("Error: --category required for scrub.")
            sys.exit(1)
        count = bb.scrub(args.category)
        print(f"SCRUBBED {count} items in category {args.category}")

if __name__ == "__main__":
    main()
