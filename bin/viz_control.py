#!/usr/bin/env python3
"""
Viz Control CLI — C336 interactive interface for Lyla's holographic form.

Triggers external-domain actions (financial probes) or modifies visual parameters
via HTTP POST to localhost:8000/api/control endpoint.

Usage:
    # Trigger financial probe with simulated data
    python3 bin/viz_control.py trigger_probe --mode sim
    
    # Adjust particle density
    python3 bin/viz_control.py set_density --count 15000
    
    # Run beacon pattern
    python3 bin/viz_control.py run_beacon --pattern pulse_3x
    
    # Cycle through cognitive phases
    python3 bin/viz_control.py toggle_phases
"""

import argparse
import json
import sys
import urllib.request


BASE_URL = "http://localhost:8000"


def post_command(command, payload=None):
    """POST command to /api/control endpoint."""
    url = f"{BASE_URL}/api/control"
    
    if payload is None:
        payload = {}
    
    data = json.dumps({"command": command, **payload}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            print(json.dumps(result, indent=2))
            return result["success"]
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Viz Control CLI — C336 interactive interface")
    subparsers = parser.add_subparsers(dest="action", help="Available commands")
    
    # trigger_probe --mode live/sim
    probe_parser = subparsers.add_parser("trigger_probe", help="Execute financial probe via holographic form")
    probe_parser.add_argument("--mode", choices=["live", "sim"], default="sim", help="Data source (default: sim)")
    
    # set_density --count <1000-50000>
    density_parser = subparsers.add_parser("set_density", help="Adjust particle swarm size")
    density_parser.add_argument("--count", type=int, required=True, help="Particle count (1000-50000)")
    
    # run_beacon --pattern <name>
    beacon_parser = subparsers.add_parser("run_beacon", help="Emit visual beacon signal")
    beacon_parser.add_argument("--pattern", default="default", help="Beacon pattern name")
    
    # toggle_phases
    subparsers.add_parser("toggle_phases", help="Cycle through cognitive phases for demo")
    
    args = parser.parse_args()
    
    if not args.action:
        parser.print_help()
        sys.exit(1)
    
    success = False
    
    if args.action == "trigger_probe":
        success = post_command("trigger_probe", {"mode": args.mode})
        
    elif args.action == "set_density":
        success = post_command("set_density", {"count": args.count})
        
    elif args.action == "run_beacon":
        success = post_command("run_beacon", {"pattern": args.pattern})
        
    elif args.action == "toggle_phases":
        success = post_command("toggle_phases", {})
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
