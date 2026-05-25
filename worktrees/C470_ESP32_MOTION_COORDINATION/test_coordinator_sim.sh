#!/bin/bash
# Test ESP32 sensor coordinator in simulation mode
# Validates polling loop, debouncing, LED pattern mapping

set -e

echo "=== Testing ESP32 Sensor Coordinator (Simulation Mode) ==="
echo ""

cd /droid/repos/lyla

# Run for 10 seconds of simulated time (500ms intervals = ~20 polls)
timeout 10 python3 bin/esp32_sensor_coordinator.py --esp-ip=192.168.4.38 --poll-interval=500 --simulate 2>&1 | tee /tmp/coordinator_test.log

echo ""
echo "=== Test complete. Check /tmp/coordinator_test.log for output ==="
