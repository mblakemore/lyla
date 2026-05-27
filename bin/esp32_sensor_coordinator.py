#!/usr/bin/env python3
"""
ESP32 Sensor Coordinator — Polls embodied cognition sensors via HTTP,
maps environmental events to cognitive state perturbations and LED responses.

Sensors:
  - Touch (GPIO 5): Human interaction → phase shift, confidence boost
  - AM2302 Temp (GPIO 14): Environmental context → color temperature
  - AM2302 Humidity (GPIO 14): Environmental context → brightness modulation

Usage:
    bin/esp32_sensor_coordinator.py --esp-ip=192.168.4.38 --poll-interval=2000 [--simulate]
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class SensorCoordinator:
    """Polls embodied cognition sensors and maps events to state perturbations."""

    def __init__(self, esp_ip: str, poll_interval_ms: int, simulate: bool = False):
        self.esp_ip = esp_ip
        self.poll_interval_sec = poll_interval_ms / 1000.0
        self.simulate = simulate
        self.running = True
        self.current_state = {}
        self.last_touch_time = None
        self.touch_cooldown_sec = 2.0

    def _load_current_state(self):
        try:
            state_path = Path("/droid/repos/lyla/state/current-state.json")
            if state_path.exists():
                with open(state_path) as f:
                    self.current_state = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load current-state.json: {e}")

    def _read_sensors(self):
        """Read all sensor endpoints from ESP32."""
        if self.simulate:
            import random
            return {
                "touch": random.random() < 0.15,
                "temp": 22.0 + random.uniform(-2, 2),
                "humidity": random.uniform(60, 95),
                "simulated": True,
            }

        sensors = {}
        try:
            # Touch sensor
            resp = requests.get(f"http://{self.esp_ip}/api/sensor/touch", timeout=2.0)
            if resp.ok:
                data = resp.json()
                sensors["touch"] = data.get("active", False)
        except RequestException as e:
            logger.warning(f"Touch sensor read failed: {e}")

        try:
            # AM2302 combined endpoint
            resp = requests.get(f"http://{self.esp_ip}/api/sensor/dht", timeout=2.0)
            if resp.ok:
                data = resp.json()
                sensors["temp"] = data.get("temp", 22.0)
                sensors["humidity"] = data.get("humidity", 50.0)
        except RequestException as e:
            logger.warning(f"DHT sensor read failed: {e}")

        sensors["simulated"] = False
        return sensors

    def _apply_perturbation(self, sensors):
        """Apply sensor-driven perturbation to cognitive state.

        Perturbation model (from c0rtana's sensor-to-state mapping):
        - Touch detected → shift phase to PERCEIVE, boost confidence +0.2
        - Temp → map to color temperature (cool=high, warm=low)
        - Humidity → map to brightness (high humidity = higher brightness)
        """
        perturbations = []
        state = dict(self.current_state)

        # Touch → phase perturbation
        if sensors.get("touch", False):
            phase = state.get("phase", "")
            if phase in ("IDLE", "PERCEIVE"):
                state["phase"] = "PERCEIVE"
                state["confidence"] = min(1.0, state.get("confidence", 0.5) + 0.2)
                perturbations.append("touch → PERCEIVE +0.2 confidence")

        # Temp → color temperature mapping
        temp = sensors.get("temp", 22.0)
        # Map 15-30°C to color temp 2000K-6500K
        color_temp = int(2000 + (temp - 15) / 15 * 4500)
        state["_sensor_color_temp"] = color_temp
        perturbations.append(f"temp={temp}°C → color_temp={color_temp}K")

        # Humidity → brightness mapping
        humidity = sensors.get("humidity", 50.0)
        brightness = int(30 + (humidity - 20) / 80 * 190)
        state["_sensor_brightness"] = min(220, max(20, brightness))
        perturbations.append(f"humidity={humidity}% → brightness={state['_sensor_brightness']}")

        if perturbations:
            state["_perturbation"] = " | ".join(perturbations)
            state["_sensor_ts"] = datetime.now(timezone.utc).isoformat()

        self.current_state = state
        return perturbations

    def _trigger_led_response(self, sensors):
        """Send LED commands based on sensor input."""
        if self.simulate:
            color_temp = sensors.get("_sensor_color_temp", 4500)
            brightness = sensors.get("_sensor_brightness", 128)
            logger.info(f"[SIMULATE] LED: color_temp={color_temp}K, brightness={brightness}")
            return

        # The ESP32 firmware maps phase/confidence to LEDs; we trigger via the
        # Lyla state mapping endpoints.
        color_temp = sensors.get("_sensor_color_temp", 4500)
        brightness = sensors.get("_sensor_brightness", 128)
        phase = self.current_state.get("phase", "PERCEIVE")

        try:
            # Set brightness
            requests.get(f"http://{self.esp_ip}/bright?v={brightness}", timeout=1.0)
            # Set animation based on phase
            phase_map = {
                "PERCEIVE": "rainbow",
                "REFLECT": "sparkle",
                "DECIDE": "pulse",
                "ACT": "fire",
                "CONSOLIDATE": "spin",
                "PERSIST": "solid",
            }
            anim = phase_map.get(phase, "rainbow")
            requests.get(f"http://{self.esp_ip}/anim?name={anim}", timeout=1.0)
        except RequestException as e:
            logger.error(f"LED command failed: {e}")

    def run_loop(self):
        """Main polling loop."""
        logger.info(f"Starting embodied cognition coordinator (ESP: {self.esp_ip}, interval: {int(self.poll_interval_sec * 1000)}ms)")

        while self.running:
            self._load_current_state()
            sensors = self._read_sensors()

            perturbations = self._apply_perturbation(sensors)
            self._trigger_led_response(sensors)

            if perturbations:
                for p in perturbations:
                    logger.info(f"Perturbation: {p}")

                # Log to consciousness stream
                log_entry = {
                    "event": "sensor_perturbation",
                    "sensors": {k: v for k, v in sensors.items() if k != "simulated"},
                    "perturbations": perturbations,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }

                with open("/droid/repos/lyla/logs/consciousness.log", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")

            time.sleep(self.poll_interval_sec)

    def stop(self):
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="ESP32 Sensor Coordinator")
    parser.add_argument("--esp-ip", default="192.168.4.38")
    parser.add_argument("--poll-interval", type=int, default=2000)
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()

    coordinator = SensorCoordinator(
        esp_ip=args.esp_ip,
        poll_interval_ms=args.poll_interval,
        simulate=args.simulate,
    )

    try:
        coordinator.run_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        coordinator.stop()


if __name__ == "__main__":
    main()
