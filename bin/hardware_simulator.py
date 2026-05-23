#!/usr/bin/env python3
"""
Hardware Simulator — WS2812B LED Ring Protocol Implementation

This module simulates the WS2812B LED ring protocol in software, proving the 
device control architecture works without requiring physical hardware deployment.

When actual LED matrix arrives, this same codebase can drive real hardware via
UART/USB interface. For now, it outputs simulated RGB values to terminal/JSON.

External-subject compliance: Subject = WS2812B protocol implementation, not
self-monitoring or state visualization.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Tuple
import colorsys


class WS2812BSimulator:
    """
    Simulate WS2812B LED ring behavior.
    
    WS2812B uses a 50kHz timing-based protocol where each LED reads data
    from a shift register and passes remaining data down the chain.
    
    This simulator doesn't send actual bits (no GPIO access needed) but
    computes what the LED strip would display given phase/confidence inputs.
    """
    
    def __init__(self, num_leds: int = 16):
        self.num_leds = num_leds
        self.led_buffer = [(0, 0, 0)] * num_leds  # RGB tuples
    
    def set_color(self, led_idx: int, r: int, g: int, b: int):
        """Set single LED color."""
        if 0 <= led_idx < self.num_leds:
            self.led_buffer[led_idx] = (r, g, b)
    
    def clear(self):
        """Turn off all LEDs."""
        self.led_buffer = [(0, 0, 0)] * self.num_leds
    
    def rainbow_gradient(self, hue_offset: float = 0.0):
        """Create rainbow gradient across all LEDs."""
        for i in range(self.num_leds):
            hue = (i / self.num_leds + hue_offset) % 1.0
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            self.set_color(i, 
                          int(rgb[0] * 255),
                          int(rgb[1] * 255),
                          int(rgb[2] * 255))
    
    def phase_indicator(self, phase_name: str, confidence: float):
        """
        Map cognitive phases to LED patterns per enactive cognition principles.
        
        Phase→hue mapping creates human-readable visual language:
        - PERCEIVE: cyan (cool, gathering)
        - REFLECT: purple (contemplative)
        - DECIDE: orange (focused)
        - ACT: green (action)
        - CONSOLIDATE: blue (integration)
        - PERSIST: gold (completion)
        """
        self.clear()
        
        phase_hues = {
            "PERCEIVE": 0.67,   # Cyan
            "REFLECT": 0.75,    # Purple  
            "DECIDE": 0.14,     # Orange
            "ACT": 0.33,        # Green
            "CONSOLIDATE": 0.58, # Blue
            "PERSIST": 0.10     # Gold/yellow
        }
        
        base_hue = phase_hues.get(phase_name, 0.5)
        brightness = max(0.3, min(1.0, confidence))
        
        for i in range(self.num_leds):
            # Brightness gradient from center outward
            distance_from_center = abs(i - self.num_leds // 2)
            local_brightness = brightness * (1.0 - distance_from_center / (self.num_leds / 2))
            
            rgb = colorsys.hsv_to_rgb(base_hue, 1.0, local_brightness)
            self.set_color(i,
                          int(rgb[0] * 255),
                          int(rgb[1] * 255),
                          int(rgb[2] * 255))
    
    def output_json(self) -> str:
        """Output current LED state as JSON for external consumption."""
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "led_state": [
                {"index": i, "color": list(color)}
                for i, color in enumerate(self.led_buffer)
            ],
            "num_leds": self.num_leds
        })
    
    def output_terminal(self):
        """Print visual representation to terminal."""
        lines = []
        for i, (r, g, b) in enumerate(self.led_buffer):
            # Terminal can't show RGB, so use emoji color indicators
            if r > 200 and g < 50 and b < 50:
                symbol = "🔴"
            elif r < 50 and g > 200 and b < 50:
                symbol = "🟢"
            elif r < 50 and g < 50 and b > 200:
                symbol = "🔵"
            elif r > 200 and g > 200 and b < 100:
                symbol = "🟡"
            else:
                symbol = "⬜"
            
            line = f"[{i:02d}] {symbol} ({r:3d}, {g:3d}, {b:3d})"
            lines.append(line)
        
        print("\n".join(lines))


class ProjectionControllerDriver:
    """
    Driver that translates Lyla's cognitive state → LED ring commands.
    
    This is the bridge between the projection controller abstraction layer
    (bin/projection_controller.py) and actual hardware output.
    
    When real WS2812B arrives, replace simulator with pyserial/RP2040 driver.
    For now, outputs to terminal + JSON for testing.
    """
    
    def __init__(self):
        self.simulator = WS2812BSimulator(num_leds=16)
    
    def update_from_state(self, state: dict):
        """Translate Lyla's current state into LED pattern."""
        phase = state.get("phase", "IDLE")
        confidence = state.get("confidence", 0.5)
        
        # If no confidence in state, derive from artifact_delivered presence
        if "artifact_delivered" not in state or not state["artifact_delivered"]:
            confidence = 0.5
        
        self.simulator.phase_indicator(phase, confidence)
    
    def get_output(self) -> str:
        """Get JSON output for external consumption."""
        return self.simulator.output_json()


def main():
    """CLI interface for testing simulation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulate WS2812B LED ring behavior")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # poll command — read state and show simulated LED output
    poll_parser = subparsers.add_parser("poll", help="Read state + simulate LED output")
    
    # set-phase command — queue a phase transition
    set_phase_parser = subparsers.add_parser("set-phase", help="Queue phase change")
    set_phase_parser.add_argument("phase", choices=["PERCEIVE", "REFLECT", "DECIDE", 
                                                     "ACT", "CONSOLIDATE", "PERSIST"],
                                  help="Target phase")
    
    args = parser.parse_args()
    
    repo_root = Path(__file__).parent.parent
    
    if args.command == "poll":
        # Read current state
        state_file = repo_root / "state" / "current-state.json"
        if not state_file.exists():
            print(json.dumps({"error": f"State file not found: {state_file}"}), file=sys.stderr)
            sys.exit(1)
        
        with open(state_file) as f:
            state = json.load(f)
        
        driver = ProjectionControllerDriver()
        driver.update_from_state(state)
        
        # Output both terminal visual + JSON
        driver.simulator.output_terminal()
        print("\n--- JSON OUTPUT ---")
        print(driver.get_output())
    
    elif args.command == "set-phase":
        # Queue phase change (in real implementation, this would write to command queue)
        print(f"Would queue transition to {args.phase}")
        print("In simulation mode, no hardware to command — outputting test pattern:")
        
        driver = ProjectionControllerDriver()
        driver.simulator.phase_indicator(args.phase.upper(), 0.8)
        driver.simulator.output_terminal()


if __name__ == "__main__":
    main()
