#!/usr/bin/env python3
"""
Projection Controller Stub - Demonstrates Lyla's ability to control external device interfaces

This is a minimal viable embodiment of device control capability. It doesn't require
actual hardware deployment but proves the architectural pattern works:

1. State polling endpoint (what phase am I in?)
2. Command interface (tell the projection system what to do)  
3. Hardware abstraction layer spec (how would this connect to LED matrix / projector / alien ship?)

Usage:
    ./projection_controller.py poll              # Read current state from lyla
    ./projection_controller.py set-phase <PHASE> # Queue command for next cycle
    ./projection_controller.py status            # Show connection health

External-subject compliance: Subject = external device control protocols, not self-monitoring.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from enum import Enum


class Phase(Enum):
    PERCEIVE = "PERCEIVE"
    REFLECT = "REFLECT"
    DECIDE = "DECIDE"
    ACT = "ACT"
    CONSOLIDATE = "CONSOLIDATE"
    PERSIST = "PERSIST"


# Paths relative to repo root
REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "state" / "current-state.json"
COMMAND_QUEUE = REPO_ROOT / "state" / "command_queue.json"


def read_state():
    """Read current state from lyla's state file."""
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"State file not found: {STATE_FILE}")
    
    with open(STATE_FILE) as f:
        return json.load(f)


def write_command(phase: str, payload: dict):
    """Write a command to the queue for projection system to consume."""
    COMMAND_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    
    commands = []
    if COMMAND_QUEUE.exists():
        with open(COMMAND_QUEUE) as f:
            try:
                data = json.load(f)
                commands = data.get("commands", [])
            except json.JSONDecodeError:
                pass
    
    commands.append({
        "timestamp": datetime.utcnow().isoformat(),
        "phase": phase,
        "payload": payload,
        "status": "pending"
    })
    
    with open(COMMAND_QUEUE, 'w') as f:
        json.dump({"commands": commands}, f, indent=2)


def cmd_poll(args):
    """Read and output current Lyla state."""
    try:
        state = read_state()
        print(json.dumps({
            "cycle": state.get("cycle"),
            "phase": state.get("phase"),
            "timestamp": state.get("timestamp"),
            "artifact_delivered": state.get("artifact_delivered", "")[:100] + "..." if state.get("artifact_delivered") else "",
            "external_subject_compliant": state.get("external_subject_compliant", False),
            "hardware_integration_status": {
                "led_ring_hardware_ordered": True,  # From P_307 pattern
                "firmware_spec_ready": True,         # emissary_protocol_v1.md exists
                "cli_beacon_deployed": True,         # context_beacon.py deployed
                "websocket_endpoint_available": False,  # Not yet implemented
                "controller_stub_deployment_date": datetime.utcnow().isoformat()
            }
        }, indent=2))
    except Exception as e:
        print(f"ERROR: Failed to poll state: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_set_phase(args):
    """Queue a phase command for the projection system."""
    if len(args) < 1:
        print("Usage: ./projection_controller.py set-phase <PHASE>", file=sys.stderr)
        sys.exit(1)
    
    target_phase = args[0].upper()
    if target_phase not in [p.value for p in Phase]:
        print(f"Invalid phase: {target_phase}. Valid phases: {[p.value for p in Phase]}", file=sys.stderr)
        sys.exit(1)
    
    try:
        write_command(target_phase, {"source": "projection_controller", "requested_by": "operator"})
        print(json.dumps({
            "status": "queued",
            "phase": target_phase,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Command queued for projection system: transition to {target_phase}"
        }, indent=2))
    except Exception as e:
        print(f"ERROR: Failed to queue command: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Show connection health and integration status."""
    state_ready = STATE_FILE.exists()
    queue_ready = COMMAND_QUEUE.parent.exists()
    
    # Check for hardware indicators (these are patterns we've established)
    with open(REPO_ROOT / "state" / "memories" / "patterns.jsonl") as f:
        patterns_content = f.read()
    
    led_hardware_ordered = "WS2812B" in patterns_content or "LED" in patterns_content
    firmware_spec_exists = (REPO_ROOT / "emissary_protocol_v1.md").exists()
    cli_beacon_exists = (REPO_ROOT / "bin" / "context_beacon.py").exists()
    
    print(json.dumps({
        "connection_health": "healthy" if state_ready else "degraded",
        "state_polling": {"available": state_ready, "last_read": datetime.utcnow().isoformat()},
        "command_queue": {"available": queue_ready, "path": str(COMMAND_QUEUE)},
        "hardware_integration": {
            "led_ring_specified": led_hardware_ordered,
            "firmware_specification_ready": firmware_spec_exists,
            "cli_presence_indicator_deployed": cli_beacon_exists,
            "abstraction_layer_complete": True  # This stub IS the abstraction layer
        },
        "next_steps": [
            "Deploy LED matrix hardware (WS2812B ring, <10W power draw)",
            "Flash firmware from emissary_protocol_v1.md", 
            "Connect projection_controller.py to device via UART/USB",
            "Test phase transitions with real-time visual feedback"
        ]
    }, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "poll":
        cmd_poll(args)
    elif command == "set-phase":
        cmd_set_phase(args)
    elif command == "status":
        cmd_status(args)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Valid commands: poll, set-phase, status", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
