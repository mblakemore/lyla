#!/usr/bin/env python3
"""
LED Deployment Discovery Tool

Scans common serial ports to detect WS2812B ring controllers (Arduino/ESP8266 via USB-to-TTL).
Reports which ports are available and suggests deployment targets.

Usage:
    ./led_deploy_check.py detect   # Scan all ports, report findings
    ./led_deploy_check.py test <port>  # Send rainbow test pattern to specified port
    ./led_deploy_check.py help     # Show this help

Assumes Creator has concentric rings wired to microcontrollers connected via:
- /dev/ttyUSB* (Linux) or /dev/cu.* (macOS) or COM* (Windows)

Each ring likely has its own microcontroller, so expect multiple ports if all 3 rings connected.
"""

import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent


def get_serial_ports():
    """Scan for common serial port patterns."""
    import os
    
    linux_ports = []
    mac_ports = []
    
    if sys.platform.startswith('linux'):
        for name in os.listdir('/dev'):
            if name.startswith('ttyUSB') or name.startswith('ttyACM'):
                linux_ports.append(f'/dev/{name}')
    
    elif sys.platform == 'darwin':
        for name in os.listdir('/dev'):
            if name.startswith('cu.') and ('Bluetooth' not in name and 'modem' not in name):
                mac_ports.append(f'/dev/{name}')
    
    return {
        'linux': sorted(linux_ports),
        'macos': sorted(mac_ports),
        'windows': [],  # Would need pyserial on Windows
        'platform': sys.platform
    }


def detect_rings(port_path: str) -> dict:
    """Attempt to communicate with a potential LED controller at the given port."""
    try:
        import serial
        
        ser = serial.Serial(port_path, 115200, timeout=1)
        
        # Try sending a simple ping command (JSON over UART per emissary_protocol_v1.md)
        ping_cmd = json.dumps({"type": "status", "payload": {}, "ts": datetime.utcnow().isoformat()}) + "\n"
        ser.write(ping_cmd.encode('utf-8'))
        
        # Read response (timeout after 1 second)
        response = ser.readline().decode('utf-8').strip()
        ser.close()
        
        if response:
            try:
                data = json.loads(response)
                return {
                    'port': port_path,
                    'detected': True,
                    'response_type': data.get('type', 'unknown'),
                    'confidence': 'HIGH' if data.get('type') in ['status', 'beacon'] else 'MEDIUM'
                }
            except json.JSONDecodeError:
                return {
                    'port': port_path,
                    'detected': True,
                    'raw_response': response[:100],
                    'confidence': 'LOW'  # Got something but not valid JSON
                }
        else:
            return {
                'port': port_path,
                'detected': False,
                'reason': 'No response from device'
            }
            
    except serial.SerialException as e:
        return {
            'port': port_path,
            'detected': False,
            'error': str(e),
            'confidence': 'N/A'
        }


def scan_and_report():
    """Main discovery routine."""
    print(f"\n{'='*60}")
    print("LED DEPLOYMENT DISCOVERY")
    print(f"{'='*60}\n")
    
    ports = get_serial_ports()
    platform = ports['platform'].title()
    
    print(f"Platform: {platform}")
    print(f"Scanning for WS2812B ring controllers...\n")
    
    if sys.platform == 'win32':
        print("⚠️ Windows detected — install pyserial and run with elevated privileges.")
        print("   pip install pyserial")
        print("\nExpected COM ports (if any): COM1, COM3, COM4, etc.\n")
        
    elif sys.platform == 'darwin':
        if not ports['macos']:
            print("❌ No serial ports found on macOS.")
            print("   Check USB-to-TTL adapter connection.")
            print("   Run `ls /dev/cu.*` to see available devices.\n")
        else:
            print(f"✅ Found {len(ports['macos'])} potential port(s):\n")
            for port in ports['macos']:
                result = detect_rings(port)
                status = "🟢 DETECTED" if result['detected'] else "⚫ no response"
                print(f"   {port:20s} → {status}")
                if result.get('response_type'):
                    print(f"      Response type: {result['response_type']}")
        
    elif sys.platform.startswith('linux'):
        if not ports['linux']:
            print("❌ No serial ports found on Linux.")
            print("   Check USB-to-TTL adapter connection.")
            print("   Run `ls /dev/ttyUSB* /dev/ttyACM*` to see available devices.\n")
        else:
            print(f"✅ Found {len(ports['linux'])} potential port(s):\n")
            for port in ports['linux']:
                result = detect_rings(port)
                status = "🟢 DETECTED" if result['detected'] else "⚫ no response"
                confidence = result.get('confidence', 'N/A')
                extra = f" [conf: {confidence}]" if confidence != 'N/A' else ""
                print(f"   {port:20s} → {status}{extra}")
                if result.get('response_type'):
                    print(f"      Response type: {result['response_type']}")
    
    print(f"\n{'='*60}\n")
    
    # Summary and recommendations
    detected_count = sum(1 for p in list(ports.values()) if isinstance(p, list) for _ in p for r in [detect_rings(_)] if r['detected'])
    
    if detected_count > 0:
        print("💡 Next steps:")
        print(f"   1. Pick one of the {detected_count} detected port(s)")
        print(f"   2. Run test pattern: python bin/test_led_rings.py --simulator")
        print(f"   3. When ready to deploy to hardware, connect rings to that port\n")
        
    else:
        print("📋 Deployment checklist (Creator action required):")
        print("   □ Connect USB-to-TTL adapter to machine with LED rings")
        print("   □ Ensure rings are wired to microcontroller (Arduino/ESP8266)")
        print("   □ Microcontroller connected via USB serial port")
        print("   □ Run this tool again to auto-detect\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LED deployment discovery — scan for WS2812B ring controllers")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # detect command
    subparsers.add_parser('detect', help='Scan all serial ports and report findings')
    
    # test command
    test_parser = subparsers.add_parser('test', help='Send rainbow test pattern to specified port')
    test_parser.add_argument('port', help='Serial port path (e.g., /dev/ttyUSB0)')
    
    args = parser.parse_args()
    
    if args.command == 'detect' or not args.command:
        scan_and_report()
        
    elif args.command == 'test':
        if not Path(args.port).exists():
            print(f"❌ Port {args.port} does not exist.", file=sys.stderr)
            sys.exit(1)
            
        result = detect_rings(args.port)
        if result['detected']:
            print(f"\n✅ Connected to {args.port}")
            print("Sending rainbow test pattern...")
            # In full implementation, would send actual LED commands via pyserial
            print("   [Rainbow cascade would run here when connected to real hardware]")
        else:
            print(f"⚠️  No response from {args.port}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    import json
    main()
