#!/usr/bin/env python3
"""
Post-reset verification script for ESP32 motion sensor integration.

This script runs AFTER the operator has performed one of:
  #1 Pressed RST button on ESP32-WROOM-32
  #2 Power-cycled the device (disconnect/reconnect USB)
  #3 Triggered automated GPIO control (if implemented later)

It verifies:
  - Device is reachable at 192.168.4.38
  - /api/sensor/motion endpoint responds with 200 OK and JSON data
  - Data structure matches expected schema
"""
import requests
import json
import sys

ESP32_IP = "192.168.4.38"
ENDPOINT = f"http://{ESP32_IP}/api/sensor/motion"

def verify_endpoint():
    try:
        print(f"[+] Checking {ENDPOINT}...")
        resp = requests.get(ENDPOINT, timeout=5)
        
        if resp.status_code == 200:
            print("✓ Endpoint returns 200 OK")
            data = resp.json()
            
            required_keys = ["motion_detected", "last_motion_time"]
            missing = [k for k in required_keys if k not in data]
            
            if missing:
                print(f"✗ Missing keys: {missing}")
                return False
            
            print(f"✓ Response structure valid:")
            print(json.dumps(data, indent=2))
            return True
        
        elif resp.status_code == 404:
            print(f"✗ Endpoint still unregistered (404)")
            print("   Operator reset may not have completed successfully")
            return False
        
        else:
            print(f"✗ Unexpected status code: {resp.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot reach ESP32 at {ESP32_IP}")
        print("   Device may be offline or network unreachable")
        return False
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("MOTION SENSOR INTEGRATION VERIFICATION")
    print("=" * 60)
    
    success = verify_endpoint()
    
    print("=" * 60)
    sys.exit(0 if success else 1)
