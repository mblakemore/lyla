#!/usr/bin/env python3
"""
Lyla State → ESP32 LED Ring Mapper

Maps internal state (phase, confidence, cycle_count) to LED control commands.
Target: ESP32 @ http://192.168.4.38
"""

import json
import argparse
import time
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error


# Paths
STATE_FILE = Path(__file__).parent.parent / "state" / "current-state.json"
ESP32_BASE = "http://192.168.4.38"

# Phase → animation mapping (ESP32 anim indices: 0=solid, 1=rainbow, 2=spin, 3=pulse, 4=sparkle, 5=fire)
PHASE_ANIMATION = {
    "PERCEIVE": {"anim": 0, "name": "solid", "color": (0, 191, 255)},      # deep sky blue
    "REFLECT": {"anim": 3, "name": "pulse", "color": (135, 206, 250)},     # light cyan pulse
    "DECIDE": {"anim": 2, "name": "spin", "color": (255, 165, 0)},         # amber spin
    "ACT": {"anim": 4, "name": "sparkle", "color": (50, 205, 50)},         # lime green sparkle
    "CONSOLIDATE": {"anim": 1, "name": "rainbow", "color": None},          # full rainbow slow
    "PERSIST": {"anim": 5, "name": "fire", "color": (255, 165, 0)},        # orange fire fade
}

# Confidence → brightness mapping (0.0-1.0 → 0-255)
def confidence_to_brightness(confidence: float) -> int:
    """Map confidence to brightness: <0.3=cyan dim, 0.7-1.0=gold bright"""
    if confidence < 0.3:
        return int(64 + (confidence / 0.3) * 64)  # 64-128 (dim cyan)
    elif confidence < 0.7:
        return int(128 + ((confidence - 0.3) / 0.4) * 64)  # 128-192 (mid-range)
    else:
        return int(192 + ((confidence - 0.7) / 0.3) * 63)  # 192-255 (bright gold)


def get_state() -> dict:
    """Read current-state.json"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {STATE_FILE} not found")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {STATE_FILE}: {e}")
        exit(1)


def set_color(ring: int, r: int, g: int, b: int) -> bool:
    """Set color on specific ring (0=all, 1=inner/7bit, 2=middle/12bit, 3=outer/24bit)"""
    url = f"{ESP32_BASE}/color?ring={ring}&r={r}&g={g}&b={b}"
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.URLError as e:
        print(f"ERROR setting color: {e}")
        return False


def set_brightness(value: int) -> bool:
    """Set global brightness (0-255)"""
    url = f"{ESP32_BASE}/bright?v={value}"
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.URLError as e:
        print(f"ERROR setting brightness: {e}")
        return False


def set_animation(name: str) -> bool:
    """Set animation by name"""
    url = f"{ESP32_BASE}/anim?name={name}"
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except urllib.error.URLError as e:
        print(f"ERROR setting animation: {e}")
        return False


def derive_current_phase(state: dict) -> str:
    """Derive current active phase from phase_status or return IDLE"""
    status = state.get("phase_status", {})
    
    # Check in order - first incomplete phase is active
    if not status.get("persist"):
        return "PERSIST"
    elif not status.get("consolidate"):
        return "CONSOLIDATE"
    elif not status.get("act"):
        return "ACT"
    elif not status.get("decide"):
        return "DECIDE"
    elif not status.get("reflect"):
        return "REFLECT"
    elif not status.get("perceive"):
        return "PERCEIVE"
    
    return "IDLE"


def map_state_to_leds(state: dict):
    """Main mapping logic"""
    phase = derive_current_phase(state)
    confidence = state.get("confidence", 0.5)
    
    # Get phase-specific settings
    phase_settings = PHASE_ANIMATION.get(phase, PHASE_ANIMATION["PERCEIVE"])
    
    # Calculate brightness from confidence
    brightness = confidence_to_brightness(confidence)
    
    # Ring color assignment based on cycle_count % 6 for radial encoding
    ring_offset = state.get("cycle_count", 1) % 6
    
    # Apply mapping
    if phase_settings["color"]:
        r, g, b = phase_settings["color"]
        
        # Dim outer rings proportionally to create depth effect
        colors_per_ring = [
            (int(r * 0.8), int(g * 0.8), int(b * 0.8)),   # inner ring (slightly dimmer)
            (r, g, b),                                     # middle ring (full)
            (int(r * 0.9), int(g * 0.9), int(b * 0.9))    # outer ring (medium)
        ]
        
        print(f"Mapping: {phase} → {phase_settings['name']} @ brightness {brightness}")
        print(f"  Inner (7-bit): RGB{colors_per_ring[0]}")
        print(f"  Middle (12-bit): RGB{colors_per_ring[1]}")
        print(f"  Outer (24-bit): RGB{colors_per_ring[2]}")
        
        # Set each ring with offset based on cycle rhythm
        for i in range(3):
            ring_idx = (i + ring_offset) % 3
            set_color(ring_idx + 1, *colors_per_ring[i])
    
    set_brightness(brightness)
    set_animation(phase_settings["name"])


def test_connection() -> bool:
    """Test ESP32 connectivity"""
    try:
        status = urllib.request.urlopen(f"{ESP32_BASE}/status", timeout=2).read().decode()
        print(f"ESP32 online: {status}")
        return True
    except urllib.error.URLError as e:
        print(f"ERROR: Cannot reach ESP32 at {ESP32_BASE}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Map Lyla state to ESP32 LED rings")
    parser.add_argument("--test", action="store_true", help="Test connection only")
    parser.add_argument("--daemon", action="store_true", help="Run continuously every 5 seconds")
    args = parser.parse_args()
    
    if args.test:
        if not test_connection():
            exit(1)
        state = get_state()
        map_state_to_leds(state)
        print("✓ Test complete - LEDs updated")
        return
    
    # Continuous daemon mode
    print(f"Starting LED mapper daemon (target: {ESP32_BASE})")
    while True:
        try:
            state = get_state()
            map_state_to_leds(state)
            timestamp = datetime.now().isoformat()
            print(f"[{timestamp}] Mapped {state.get('phase', 'UNKNOWN')} ({state.get('confidence', '?'):.2f} conf)")
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(5)


if __name__ == "__main__":
    main()
