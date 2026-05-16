import json
import sys

def scan_system(target_file, heuristics_file):
    print(f"--- Systemic Fragility Scan ---")
    try:
        with open(target_file, 'r') as f:
            target = json.load(f)
        with open(heuristics_file, 'r') as f:
            rules = json.load(f)
    except Exception as e:
        print(f"Error reading files: {e}")
        return

    found_issues = 0
    # Simple heuristic match based on keywords in the target object
    target_str = str(target).lower()
    for rule in rules:
        trigger = rule['trigger'].lower()
        # We simulate a basic search for terms from the trigger/indicator and check if they exist in targets
        # In a real tool this would be more complex mapping.
        keywords = [k for k in trigger.split() if len(k) > 4]
        if any(kw in target_str for kw in keywords):
            print(f"\n[!] Warning: Possible {rule['name']}")
            print(f"  Fragility: {rule['fragility_level']}")
            print(f"  Potential Cause: {rule['trigger']}")
            print(f"  Recommendation: {rule['mitigation']}")
            found_issues += 1

    if found_issues == 0:
        print("\nNo immediate hyper-coupling patterns detected with current heuristics.")
    else:
        print(f"\nScan complete. Found {found_issues} potential fragility hotspots.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scanner.py <target.json> <heuristics.json>")
    else:
        scan_system(sys.argv[1], sys.argv[2])
