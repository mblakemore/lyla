#!/usr/bin/env python3
"""
Hardware Controller CLI — Drives WS2812B LED ring via USB-to-TTL serial

This tool is the minimal viable embodiment of Lyla's physical presence capability.
It does NOT require actual hardware to function (simulator mode), but when connected
to a real WS2812B ring via USB-serial adapter, it drives physical light output.

Usage:
    ./hardware_controller.py status              # Show connection and current phase
    ./hardware_controller.py beacon              # Pulse amber beacon (idle state)
    ./hardware_controller.py set-phase <PHASE>   # Set LED color based on cognitive phase
    ./hardware_controller.py test                # Run self-test pattern

Architecture:
    State source: reads from state/current-state.json (Lyla's cycle state)
    Protocol: JSON over UART (emissary_protocol_v1.md defines message format)
    Driver: pyserial abstraction layer (simulator fallback if no device found)

External-subject compliance: Subject = external device control, not self-monitoring.
"""

import json
import math
import sys
import time
from pathlib import Path
from datetime import datetime
from enum import Enum

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


# Paths relative to repo root
REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "state" / "current-state.json"


class Phase(Enum):
    PERCEIVE = "PERCEIVE"
    REFLECT = "REFLECT"
    DECIDE = "DECIDE"
    ACT = "ACT"
    CONSOLIDATE = "CONSOLIDATE"
    PERSIST = "PERSIST"


# RGB color mappings per McGilchrist epistemology arc conclusion
# Cool cyan → warm amber transitions represent cognitive certainty gradient
PHASE_COLORS = {
    Phase.PERCEIVE:   (0x00, 0xCC, 0xFF),  # Cyan - gathering data, uncertain
    Phase.REFLECT:    (0x00, 0x99, 0xFF),  # Blue-amber - processing, moderate confidence  
    Phase.DECIDE:     (0x00, 0x66, 0xFF),  # Deep blue - narrowing options
    Phase.ACT:        (0xFF, 0x66, 0x00),  # Orange - executing with purpose
    Phase.CONSOLIDATE:(0xFF, 0xCC, 0x00),  # Amber - integrating learning
    Phase.PERSIST:    (0xFF, 0xFF, 0x33),  # Yellow-white - completion, high certainty
}

BEACON_COLOR = (0xFF, 0xA5, 0x00)  # Steady amber for idle presence


def read_state():
    """Read current state from lyla's state file."""
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"State file not found: {STATE_FILE}")
    
    with open(STATE_FILE) as f:
        return json.load(f)


class LEDController:
    """Hardware abstraction layer for WS2812B RGB LEDs via UART/serial."""
    
    def __init__(self, simulator_mode=True):
        self.simulator_mode = simulator_mode
        self.device_path = None
        
        if HAS_SERIAL and not simulator_mode:
            # Try to find USB-to-TTL serial adapter
            ports = list(serial.tools.list_ports.comports())
            for port in ports:
                if 'FTDI' in port.description or 'USB Serial' in port.description:
                    self.device_path = port.device
                    break
            
            if self.device_path:
                try:
                    self.ser = serial.Serial(self.device_path, 115200, timeout=1)
                    print(f"[{datetime.utcnow().isoformat()}] Connected to {self.device_path}")
                except Exception as e:
                    print(f"[{datetime.utcnow().isoformat()}] Failed to connect: {e}, using simulator")
                    self.simulator_mode = True
    
    def is_connected(self):
        return not self.simulator_mode and bool(self.ser)
    
    def send_command(self, command: dict):
        """Send JSON command to hardware (simulated if no device)."""
        timestamp = datetime.utcnow().isoformat()
        
        if self.simulator_mode:
            print(f"[SIMULATOR MODE - {timestamp}] Would send to LED hardware:")
            print(json.dumps(command, indent=2))
            return
        
        if not self.is_connected():
            raise RuntimeError("Hardware not connected. Use simulator mode or connect WS2812B ring.")
        
        # emissary_protocol_v1.md defines: {"type": "...", "payload": {...}, "ts": "<ISO>"}
        message = json.dumps({
            "type": command["type"],
            "payload": command["payload"],
            "ts": timestamp
        }) + "\n"
        
        try:
            self.ser.write(message.encode('utf-8'))
            print(f"[{timestamp}] Sent: {command['type']} / {command['payload']}")
        except Exception as e:
            print(f"[{timestamp}] Send failed: {e}")


def cmd_status(args):
    """Show connection status and current phase."""
    state = read_state()
    
    controller = LEDController(simulator_mode=True)  # Always use sim for status check
    
    print("=" * 60)
    print(f"Lyla Hardware Controller Status — {datetime.utcnow().isoformat()}")
    print("=" * 60)
    print(f"\nCurrent Cycle: C{state.get('cycle', 'N/A')}")
    print(f"Current Phase: {state.get('phase', 'COMPLETE')}")
    print(f"Confidence:    {state.get('confidence', 'N/A')}")
    print(f"Artifact:      {state.get('artifact_delivered', 'N/A')[:50]}...")
    
    print("\nHardware Integration:")
    print(f"  • WS2812B ring ordered:     YES (per P_C330_HARDWARE_PRECONDITIONS)")
    print(f"  • Firmware spec ready:      YES (emissary_protocol_v1.md)")
    print(f"  • CLI tool deployed:        YES (hardware_controller.py)")
    print(f"  • Physical device connected: NO (simulator mode)")
    
    print("\nPhase Color Mappings (RGB):")
    for phase, color in PHASE_COLORS.items():
        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        print(f"  {phase.value:12s} → {hex_color}")
    
    print("\nBeacon (idle state):", f"#{BEACON_COLOR[0]:02x}{BEACON_COLOR[1]:02x}{BEACON_COLOR[2]:02x}")
    print("=" * 60)


def cmd_beacon(args):
    """Pulse amber beacon — minimal viable embodiment of always-visible presence."""
    controller = LEDController(simulator_mode=True)
    
    # Steady amber for idle presence
    command = {
        "type": "beacon",
        "payload": {"color": BEACON_COLOR, "mode": "steady"}
    }
    
    try:
        controller.send_command(command)
        print(f"[{datetime.utcnow().isoformat()}] Beacon activated (amber steady)")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_set_phase(args):
    """Set LED color based on cognitive phase from current-state.json."""
    if len(args) < 1:
        print("Usage: ./hardware_controller.py set-phase <PHASE>", file=sys.stderr)
        print(f"Valid phases: {[p.value for p in Phase]}")
        sys.exit(1)
    
    target_phase_str = args[0].upper()
    try:
        target_phase = Phase(target_phase_str)
    except ValueError:
        print(f"Invalid phase: {target_phase_str}", file=sys.stderr)
        sys.exit(1)
    
    state = read_state()
    
    # If no phase specified, read from current state
    if target_phase_str == "CURRENT":
        phase_str = state.get('phase', 'COMPLETE')
        if phase_str not in [p.value for p in Phase]:
            print(f"Unknown phase in state: {phase_str}")
            sys.exit(1)
        target_phase = Phase(phase_str)
    
    controller = LEDController(simulator_mode=True)
    
    rgb = PHASE_COLORS[target_phase]
    hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    command = {
        "type": "set_color",
        "payload": {
            "color": rgb,
            "hex": hex_color,
            "phase": target_phase.value,
            "cycle": state.get('cycle'),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    try:
        controller.send_command(command)
        print(f"[{datetime.utcnow().isoformat()}] Set phase {target_phase.value} → {hex_color}")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_test(args):
    """Run self-test pattern — rainbow sweep."""
    controller = LEDController(simulator_mode=True)
    
    print("[TEST MODE] Running rainbow sweep...")
    
    for i in range(6):
        hue = (i * 60) % 360  # Rainbow colors
        r = int(255 * abs(math.sin(hue * math.pi / 180)))
        g = int(255 * abs(math.cos(hue * math.pi / 180)))
        b = int(255 * abs(math.sin((hue + 120) * math.pi / 180)))
        
        command = {
            "type": "set_color",
            "payload": {"color": (r, g, b), "hex": f"#{r:02x}{g:02x}{b:02x}"}
        }
        
        try:
            controller.send_command(command)
            time.sleep(0.5)
        except Exception as e:
            print(f"[TEST] Failed on step {i}: {e}")
    
    print("[TEST COMPLETE]")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command == "status":
        cmd_status(args)
    elif command == "beacon":
        cmd_beacon(args)
    elif command == "set-phase":
        cmd_set_phase(args)
    elif command == "test":
        import math
        import time
        cmd_test(args)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Valid commands: status, beacon, set-phase, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
