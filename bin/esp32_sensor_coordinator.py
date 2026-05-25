#!/usr/bin/env python3
"""
ESP32 Sensor Coordinator — Polls motion sensor via HTTP, maps to LED response patterns.

Usage:
    bin/esp32_sensor_coordinator.py --esp-ip=192.168.4.1 --poll-interval=500 [--simulate]

This tool implements the polling loop for HC-SR501 PIR motion detection on ESP32.
It reads JSON from /api/sensor/motion endpoint every N milliseconds and triggers
appropriate LED animations based on current cognitive state + event context.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_ESP_IP = "192.168.4.38"  # Default ESP32 address (adjust as needed)
SENSITIVE_PATTERN_INDEX = 1      # Warm orange pulse pattern index
NORMAL_PATTERN_INDEX = 0         # Rainbow breathing animation
WHITE_FLASH_INDEX = 2            # Brief white flash acknowledgment


class SensorCoordinator:
    """Polls ESP32 motion sensor and maps events to LED response patterns."""

    def __init__(self, esp_ip: str, poll_interval_ms: int, simulate: bool = False):
        self.esp_ip = esp_ip
        self.poll_interval_sec = poll_interval_ms / 1000.0
        self.simulate = simulate
        self.running = True
        
        # State tracking for debouncing
        self.last_motion_time = None
        self.motion_cooldown_sec = 0.5  # Minimum time between triggers
        
        # Load current cognitive state
        self.current_phase = self._load_current_state()
        self.current_confidence = 0.5  # default mid-range
    
    def _load_current_state(self) -> dict:
        """Load current-state.json to get phase/confidence context."""
        try:
            state_path = Path("/droid/repos/lyla/state/current-state.json")
            if state_path.exists():
                with open(state_path) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load current-state.json: {e}")
        
        return {"phase": "IDLE", "confidence": 0.5}

    def _get_led_response_pattern(self, motion_detected: bool) -> tuple[int, float]:
        """
        Map motion event + current state → LED animation index and brightness.
        
        Returns: (animation_index, brightness)
        - animation_index: which predefined pattern to play
        - brightness: 0-255 scale
        """
        if not motion_detected:
            return NORMAL_PATTERN_INDEX, int(self.current_confidence * 255)
        
        # Motion detected — choose response based on phase
        phase = self.current_phase.get("phase", "IDLE").upper()
        
        if phase in ["PERCEIVE", "REFLECT"]:
            # Slow attention-capture pulse (warm orange)
            return SENSITIVE_PATTERN_INDEX, 180
        
        elif phase in ["DECIDE", "ACT"]:
            # Fast alert pulse → fade back
            return SENSITIVE_PATTERN_INDEX, 220
        
        elif phase in ["CONSOLIDATE", "PERSIST"]:
            # Brief acknowledgment without disruption
            return WHITE_FLASH_INDEX, 255
        
        else:
            # Default fallback
            return SENSITIVE_PATTERN_INDEX, 200

    def _read_motion_sensor(self) -> dict | None:
        """Read motion sensor JSON from ESP32 HTTP endpoint."""
        if self.simulate:
            # Simulated mode for testing without hardware
            import random
            return {
                "sensor": "motion",
                "value": random.choice([True, False]),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        
        try:
            url = f"http://{self.esp_ip}/api/sensor/motion"
            response = requests.get(url, timeout=2.0)
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.warning(f"Sensor read failed ({e})")
            return None

    def _trigger_led_pattern(self, animation_index: int, brightness: int):
        """Send LED command to ESP32 via HTTP POST."""
        if self.simulate:
            logger.info(f"[SIMULATE] Would trigger pattern {animation_index} at brightness {brightness}")
            return
        
        try:
            url = f"http://{self.esp_ip}/api/command/led"
            payload = {
                "animation": animation_index,
                "brightness": brightness
            }
            requests.post(url, json=payload, timeout=1.0)
        except RequestException as e:
            logger.error(f"LED command failed ({e})")

    def run_loop(self):
        """Main polling loop."""
        logger.info(f"Starting sensor coordinator (ESP: {self.esp_ip}, interval: {int(self.poll_interval_sec * 1000)}ms)")
        
        while self.running:
            # Reload state for fresh context
            self.current_state = self._load_current_state()
            
            # Read sensor
            sensor_data = self._read_motion_sensor()
            
            if sensor_data and "value" in sensor_data:
                motion_detected = sensor_data["value"]
                
                # Debounce check
                now = time.time()
                if motion_detected and self.last_motion_time:
                    if now - self.last_motion_time < self.motion_cooldown_sec:
                        logger.debug("Motion event suppressed (debounce)")
                        continue
                
                if motion_detected:
                    self.last_motion_time = now
                    logger.info(f"Motion detected at {sensor_data.get('timestamp')}")
                
                # Get LED response pattern
                anim_idx, brightness = self._get_led_response_pattern(motion_detected)
                self._trigger_led_pattern(anim_idx, brightness)
                
                # Log to consciousness stream
                log_entry = {
                    "event": "motion_detection",
                    "detected": motion_detected,
                    "phase": self.current_state.get("phase"),
                    "confidence": self.current_confidence,
                    "led_response": f"pattern={anim_idx},brightness={brightness}",
                    "ts": datetime.utcnow().isoformat() + "Z"
                }
                
                with open("/droid/repos/lyla/logs/consciousness.log", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            
            time.sleep(self.poll_interval_sec)

    def stop(self):
        """Signal loop termination."""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="ESP32 Motion Sensor Coordinator")
    parser.add_argument("--esp-ip", default=DEFAULT_ESP_IP, help=f"ESP32 IP address (default: {DEFAULT_ESP_IP})")
    parser.add_argument("--poll-interval", type=int, default=500, help="Polling interval in ms (default: 500)")
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode without hardware")
    
    args = parser.parse_args()
    
    coordinator = SensorCoordinator(
        esp_ip=args.esp_ip,
        poll_interval_ms=args.poll_interval,
        simulate=args.simulate
    )
    
    try:
        coordinator.run_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        coordinator.stop()
        logger.info("Coordinator stopped")


if __name__ == "__main__":
    main()
