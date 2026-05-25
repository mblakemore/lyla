#!/usr/bin/env python3
"""
ESP32 Diagnostic CLI — Operator-facing health checker for LED ring device

Queries ESP32 @ 192.168.4.38 and reports:
- Current LED animation/brightness mapping (if endpoint available)
- Motion sensor endpoint status (/api/sensor/motion)
- Firmware version info (if available)
- Clear remediation steps for common failures

Usage:
    python3 bin/esp32_diagnostic_cli.py [--ip <IP_ADDRESS>] [--verbose]

Defaults to ESP32 IP 192.168.4.38 unless overridden.
"""

import argparse
import json
import urllib.request
import urllib.error
from datetime import datetime


DEFAULT_IP = "192.168.4.38"


def make_request(path: str, ip: str, timeout: int = 5):
    """Make HTTP GET request to ESP32 endpoint."""
    url = f"http://{ip}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read().decode("utf-8")
            return {"success": True, "status": response.status, "data": data}
    except urllib.error.HTTPError as e:
        return {"success": False, "status": e.code, "error": str(e), "type": "http_error"}
    except urllib.error.URLError as e:
        return {"success": False, "error": str(e.reason), "type": "url_error"}
    except Exception as e:
        return {"success": False, "error": str(e), "type": "unknown"}


def check_state_endpoint(ip: str) -> dict:
    """Check if LED state mapping is working."""
    # Try common endpoints — lyla.html typically polls /api/state or similar
    results = {}
    for path in ["/api/state", "/state", "/"]:
        result = make_request(path, ip)
        results[path] = result
    
    # Check if any returned valid JSON with animation/brightness
    for path, result in results.items():
        if result["success"] and result.get("data"):
            try:
                parsed = json.loads(result["data"])
                if "anim" in parsed or "animation" in parsed or "brightness" in parsed:
                    return {"endpoint": path, "valid": True, "data": parsed}
            except json.JSONDecodeError:
                continue
    
    return {"all_failed": True, "results": results}


def check_motion_endpoint(ip: str) -> dict:
    """Check motion sensor endpoint status."""
    result = make_request("/api/sensor/motion", ip)
    
    if result["success"]:
        try:
            data = json.loads(result["data"])
            return {
                "available": True,
                "status": result["status"],
                "response": data,
                "validation": validate_motion_response(data)
            }
        except json.JSONDecodeError:
            return {
                "available": True,
                "status": result["status"],
                "raw_data": result["data"],
                "error": "Not valid JSON"
            }
    else:
        return {
            "available": False,
            "type": result.get("type"),
            "status": result.get("status"),
            "error": result.get("error")
        }


def validate_motion_response(data: dict) -> dict:
    """Validate motion sensor response schema."""
    errors = []
    warnings = []
    
    required_fields = ["sensor", "value", "timestamp"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if data.get("sensor") != "motion":
        warnings.append(f"Expected sensor='motion', got '{data.get('sensor')}'")
    
    if not isinstance(data.get("value"), bool):
        errors.append(f"value should be boolean, got {type(data.get('value')).__name__}")
    
    timestamp = data.get("timestamp", "")
    if not timestamp.endswith("Z"):
        warnings.append(f"Timestamp should end with 'Z' (ISO8601), got: {timestamp[:50]}...")
    
    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def print_report(ip: str, state_result: dict, motion_result: dict, verbose: bool = False):
    """Print human-readable diagnostic report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    print("=" * 70)
    print(f"ESP32 Diagnostic Report — {now}")
    print(f"Target IP: {ip}")
    print("=" * 70)
    print()
    
    # State endpoint check
    print("📡 LED STATE MAPPING:")
    if "all_failed" in state_result or not any(r["success"] for r in state_result.get("results", {}).values()):
        print("   ❌ NOT RESPONDING - No valid state endpoint found")
        print("   Possible causes:")
        print("     • Firmware not running / crashed")
        print("     • Wrong IP address")
        print("     • Network connectivity issue")
    else:
        for path, result in state_result.get("results", {}).items():
            if result["success"]:
                print(f"   ✓ Endpoint {path}: OK (HTTP {result['status']})")
                if result.get("data"):
                    try:
                        data = json.loads(result["data"])
                        anim = data.get("anim", data.get("animation", "N/A"))
                        brightness = data.get("brightness", data.get("intensity", "N/A"))
                        print(f"      → Animation: {anim}, Brightness: {brightness}")
                    except:
                        pass
    
    print()
    
    # Motion sensor endpoint
    print("🔍 MOTION SENSOR ENDPOINT (/api/sensor/motion):")
    if motion_result.get("available"):
        print("   ✓ ENDPOINT EXISTS — HTTP response received")
        validation = motion_result.get("validation", {})
        if validation.get("valid"):
            print("   ✅ RESPONSE VALID — Schema correct")
            print(f"      Last reading: {motion_result['response'].get('value')}")
            print(f"      Timestamp: {motion_result['response'].get('timestamp', 'N/A')}")
        else:
            print("   ⚠️  RESPONSE SCHEMA ISSUES:")
            for err in validation.get("errors", []):
                print(f"      • {err}")
            for warn in validation.get("warnings", []):
                print(f"      ℹ️  {warn}")
    else:
        error_type = motion_result.get("type", "unknown")
        status = motion_result.get("status")
        
        if error_type == "url_error":
            print("   ❌ NOT REACHABLE — Cannot connect to ESP32")
            print("      Possible causes:")
            print("        • Device offline / powered off")
            print("        • Wrong IP address (check your router's client list)")
            print("        • Network segmentation/firewall blocking access")
        elif error_type == "http_error":
            if status == 404:
                print("   ❌ ENDPOINT NOT REGISTERED — Firmware not running this route")
                print("      Most likely cause:")
                print("        • OTA update completed but setup() never re-ran")
                print("        • Device needs POWER CYCLE or RESET BUTTON press")
                print("      This is EXPECTED behavior after OTA flash on ESP32!")
            elif status == 500:
                print("   ⚠️  SERVER ERROR — Endpoint exists but failed internally")
                print("      Likely firmware bug or crash")
            else:
                print(f"   ⚠️  HTTP {status} — Unexpected response")
        else:
            print(f"   ❌ UNKNOWN ERROR: {motion_result.get('error')}")
    
    print()
    
    # Remediation steps
    print("🔧 REMEDIATION STEPS:")
    print("-" * 70)
    
    if not motion_result.get("available") and motion_result.get("type") == "url_error":
        print("1. VERIFY DEVICE ONLINE:")
        print("   - Check your router's connected devices list for IP 192.168.4.x")
        print("   - Look for 'ESP32' or 'esphome' or similar hostname")
        print("   - Confirm USB cable is plugged in (if battery not installed)")
        print()
        print("2. TRY HARDWARE RESET:")
        print("   - Find the RST button on ESP32-WROOM-32 board")
        print("   - Press and hold for ~5 seconds, then release")
        print("   - Wait 10 seconds for boot sequence to complete")
        print("   - Run this diagnostic again")
    elif not motion_result.get("available") and motion_result.get("status") == 404:
        print("1. POWER CYCLE REQUIRED (expected after OTA):")
        print("   a) Locate the RESET button on ESP32-WROOM-32")
        print("      OR unplug/replug the USB power cable")
        print("   b) Press reset once, wait 10 seconds")
        print("   c) Run this diagnostic again — /api/sensor/motion should respond")
        print()
        print("⚠️  This is NOT a bug — ESP32 HTTP routes register only at boot!")
        print("   OTA updates flash new code but don't re-run setup().")
    else:
        print("Device appears healthy — run diagnostic again after any hardware changes.")
    
    print()
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="ESP32 Diagnostic CLI — Check LED ring device health",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 esp32_diagnostic_cli.py                    # Default IP: 192.168.4.38
  python3 esp32_diagnostic_cli.py --ip 192.168.1.50  # Custom IP address
  python3 esp32_diagnostic_cli.py --verbose          # Show raw HTTP responses

The tool queries two endpoints:
  • /api/state (or similar) — Current LED animation/brightness mapping
  • /api/sensor/motion      — Motion sensor data (if implemented in firmware)

If you see 'ENDPOINT NOT REGISTERED' (HTTP 404), this typically means:
  1. Firmware was just updated via OTA
  2. Device needs power cycle or reset button press to reload routes
  3. This is EXPECTED behavior on ESP32 — not a bug!
"""
    )
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"ESP32 IP address (default: {DEFAULT_IP})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show raw HTTP responses")
    
    args = parser.parse_args()
    
    print(f"[*] Querying ESP32 at {args.ip}...")
    
    state_result = check_state_endpoint(args.ip)
    motion_result = check_motion_endpoint(args.ip)
    
    if args.verbose:
        print("\n--- RAW RESULTS ---\n")
        print("State endpoint:", json.dumps(state_result, indent=2))
        print("Motion endpoint:", json.dumps(motion_result, indent=2))
    
    print_report(args.ip, state_result, motion_result, verbose=args.verbose)


if __name__ == "__main__":
    main()
