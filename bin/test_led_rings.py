#!/usr/bin/env python3
"""
LED Ring Test — Concentric WS2812B Configuration

Creator reported having 3 WS2812B rings:
- 7-bit ring: 1 center LED + 6 surrounding LEDs
- 12-bit ring: fits around 7-bit
- 24-bit ring: fits around both

This script drives all three rings in concentric patterns based on lyla's state.

Hardware wiring assumed:
- Each ring connected to separate GPIO/UART pin
- Rings indexed: RING_7BIT = 0, RING_12BIT = 1, RING_24BIT = 2

Usage:
    ./test_led_rings.py [--simulator] [--pattern <NAME>]

Patterns:
    phase        → Colors based on current cognitive phase (all rings)
    concentric   → Different color per ring (radial gradient)
    beacon       → Amber pulse across all rings (idle presence)
    rainbow      → Rainbow sweep test pattern
    creator      → Center white, inner cyan, outer amber (per Creator's config)
"""

import json
import math
import sys
import time
from pathlib import Path
from datetime import datetime

# Paths relative to repo root
REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = REPO_ROOT / "state" / "current-state.json"


class Phase:
    PERCEIVE = "PERCEIVE"
    REFLECT = "REFLECT"
    DECIDE = "DECIDE"
    ACT = "ACT"
    CONSOLIDATE = "CONSOLIDATE"
    PERSIST = "PERSIST"


PHASE_COLORS = {
    Phase.PERCEIVE:   (0x00, 0xCC, 0xFF),  # Cyan - gathering data, uncertain
    Phase.REFLECT:    (0x00, 0x99, 0xFF),  # Blue-amber - processing, moderate confidence  
    Phase.DECIDE:     (0x00, 0x66, 0xFF),  # Deep blue - narrowing options
    Phase.ACT:        (0xFF, 0x66, 0x00),  # Orange - executing with purpose
    Phase.CONSOLIDATE:(0xFF, 0xCC, 0x00),  # Amber - integrating learning
    Phase.PERSIST:    (0xFF, 0xFF, 0x33),  # Yellow-white - completion, high certainty
}

BEACON_COLOR = (0xFF, 0xA5, 0x00)  # Steady amber for idle presence
CREATOR_CONFIG = {
    'center': (0xFF, 0xFF, 0xFF),  # White center
    'inner':  (0x00, 0xCC, 0xFF),  # Cyan inner ring
    'outer':  (0xFF, 0xA5, 0x00),  # Amber outer ring
}


def read_state():
    """Read current state from lyla's state file."""
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"State file not found: {STATE_FILE}")
    
    with open(STATE_FILE) as f:
        return json.load(f)


class LEDRingController:
    """Hardware abstraction layer for concentric WS2812B rings via UART/serial."""
    
    def __init__(self, simulator_mode=True):
        self.simulator_mode = simulator_mode
        self.rings = [None, None, None]  # 7-bit, 12-bit, 24-bit
        
        if HAS_SERIAL and not simulator_mode:
            # Try to find USB-to-TTL serial adapters
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            
            # Map each ring to a port (assumes 3 separate connections or daisy-chain)
            # For now, use first available FTDI device for all rings
            connected_device = None
            for port in ports:
                if 'FTDI' in port.description or 'USB Serial' in port.description:
                    try:
                        ser = serial.Serial(port.device, 115200, timeout=1)
                        connected_device = ser
                        break
                    except Exception:
                        continue
            
            if connected_device:
                self.rings = [connected_device, connected_device, connected_device]
                print(f"[{datetime.utcnow().isoformat()}] Connected to {connected_device.port}")
                print("[SIMULATOR MODE DISABLED — REAL HARDWARE DETECTED]")
    
    def is_connected(self):
        return not self.simulator_mode and any(r is not None for r in self.rings)
    
    def send_to_ring(self, ring_idx: int, command: dict):
        """Send JSON command to specific ring."""
        timestamp = datetime.utcnow().isoformat()
        
        if self.simulator_mode or self.rings[ring_idx] is None:
            print(f"[SIMULATOR - {timestamp}] Ring {ring_idx}: {json.dumps(command)}")
            return
        
        message = json.dumps({
            "type": command["type"],
            "payload": command["payload"],
            "ts": timestamp
        }) + "\n"
        
        try:
            self.rings[ring_idx].write(message.encode('utf-8'))
            print(f"[{timestamp}] Ring {ring_idx} → {command['type']}")
        except Exception as e:
            print(f"[{timestamp}] Ring {ring_idx} SEND FAILED: {e}")


def has_serial():
    """Check if pyserial is available."""
    try:
        import serial
        return True
    except ImportError:
        return False


HAS_SERIAL = has_serial()


# Pattern implementations
def pattern_phase(controller: LEDRingController):
    """All rings show current phase color."""
    state = read_state()
    phase_str = state.get('phase', 'COMPLETE')
    
    if phase_str not in PHASE_COLORS:
        rgb = BEACON_COLOR
    else:
        rgb = PHASE_COLORS[phase_str]
    
    timestamp = datetime.utcnow().isoformat()
    
    for ring_idx in range(3):
        command = {
            "type": "set_color",
            "payload": {
                "color": rgb,
                "hex": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
                "ring": ring_idx,
                "phase": phase_str,
                "ts": timestamp
            }
        }
        controller.send_to_ring(ring_idx, command)
    
    print(f"[{timestamp}] Phase pattern → {phase_str} ({rgb})")


def pattern_concentric(controller: LEDRingController):
    """Radial gradient: inner=cool (cyan), outer=warm (amber)."""
    timestamp = datetime.utcnow().isoformat()
    
    # Ring 7-bit (innermost) - cool cyan
    cmd_inner = {
        "type": "set_color",
        "payload": {"color": CREATOR_CONFIG['inner'], "hex": "#00CCFF"}
    }
    controller.send_to_ring(0, cmd_inner)
    
    # Ring 12-bit (middle) - transition blue-purple
    cmd_middle = {
        "type": "set_color", 
        "payload": {"color": (0x66, 0x99, 0xFF), "hex": "#6699FF"}
    }
    controller.send_to_ring(1, cmd_middle)
    
    # Ring 24-bit (outermost) - warm amber
    cmd_outer = {
        "type": "set_color",
        "payload": {"color": CREATOR_CONFIG['outer'], "hex": "#FFA500"}
    }
    controller.send_to_ring(2, cmd_outer)
    
    print(f"[{timestamp}] Concentric pattern → inner={CREATOR_CONFIG['inner']}, middle=(0x66,0x99,0xFF), outer={CREATOR_CONFIG['outer']}")


def pattern_beacon(controller: LEDRingController):
    """Pulsing amber beacon across all rings — minimal viable presence."""
    timestamp = datetime.utcnow().isoformat()
    
    for ring_idx in range(3):
        command = {
            "type": "beacon",
            "payload": {"color": BEACON_COLOR, "mode": "pulse", "ring": ring_idx}
        }
        controller.send_to_ring(ring_idx, command)
    
    print(f"[{timestamp}] Beacon activated (amber pulse)")


def pattern_rainbow(controller: LEDRingController):
    """Rainbow sweep test — cycles through hues on each ring with offset."""
    timestamp = datetime.utcnow().isoformat()
    
    print("[TEST MODE] Rainbow sweep starting...")
    
    for hue_offset in range(12):  # 12 steps of rainbow
        base_hue = hue_offset * 30  # 360° / 12 steps
        
        for ring_idx in range(3):
            # Each ring has different hue offset
            ring_hue = (base_hue + (ring_idx * 45)) % 360
            
            r = int(255 * abs(math.sin(ring_hue * math.pi / 180)))
            g = int(255 * abs(math.cos(ring_hue * math.pi / 180)))
            b = int(255 * abs(math.sin((ring_hue + 120) * math.pi / 180)))
            
            command = {
                "type": "set_color",
                "payload": {"color": (r, g, b), "hex": f"#{r:02x}{g:02x}{b:02x}", "ring": ring_idx}
            }
            controller.send_to_ring(ring_idx, command)
        
        time.sleep(0.3)
    
    print("[TEST COMPLETE] Rainbow sweep finished")


def pattern_creator_config(controller: LEDRingController):
    """Creator's exact config: center white, inner cyan, outer amber."""
    timestamp = datetime.utcnow().isoformat()
    
    # Center LED on 7-bit ring — white
    cmd_center = {
        "type": "set_led",
        "payload": {"led_index": 0, "color": CREATOR_CONFIG['center'], "hex": "#FFFFFF"}
    }
    controller.send_to_ring(0, cmd_center)
    
    # Remaining 6 LEDs on 7-bit ring — cyan
    cmd_inner_7bit = {
        "type": "set_all",
        "payload": {"count": 6, "start": 1, "color": CREATOR_CONFIG['inner'], "hex": "#00CCFF"}
    }
    controller.send_to_ring(0, cmd_inner_7bit)
    
    # 12-bit ring — gradient from cyan to purple
    for i in range(12):
        hue = (i * 30) % 360
        r = int(255 * abs(math.sin(hue * math.pi / 180)))
        g = int(255 * abs(math.cos(hue * math.pi / 180)))
        b = int(255 * abs(math.sin((hue + 120) * math.pi / 180)))
        
        command = {
            "type": "set_led",
            "payload": {"led_index": i, "color": (r, g, b), "hex": f"#{r:02x}{g:02x}{b:02x}"}
        }
        controller.send_to_ring(1, command)
    
    # 24-bit ring — amber steady
    cmd_outer_24bit = {
        "type": "set_all",
        "payload": {"count": 24, "color": CREATOR_CONFIG['outer'], "hex": "#FFA500"}
    }
    controller.send_to_ring(2, cmd_outer_24bit)
    
    print(f"[{timestamp}] Creator config applied → center=white, inner=cyan, outer=amber")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test concentric WS2812B LED rings")
    parser.add_argument("--simulator", action="store_true", default=False, help="Force simulator mode")
    parser.add_argument("--pattern", choices=["phase", "concentric", "beacon", "rainbow", "creator"], 
                        default="creator", help="Pattern to run")
    args = parser.parse_args()
    
    controller = LEDRingController(simulator_mode=args.simulator)
    
    patterns = {
        "phase": pattern_phase,
        "concentric": pattern_concentric,
        "beacon": pattern_beacon,
        "rainbow": pattern_rainbow,
        "creator": pattern_creator_config,
    }
    
    try:
        patterns[args.pattern](controller)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

