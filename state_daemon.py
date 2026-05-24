#!/usr/bin/env python3
"""
State daemon — bridges Lyla cognitive state to ESP32 LED rings.
Polls /state/current-state.json every 2 seconds and maps phase/confidence 
to hardware animation/brightness via HTTP calls to ESP32 @ 192.168.4.38.

This is the server-side equivalent of lyla.html's updateESP32() function,
running persistently so physical presence works even without browser tab.
"""

import json
import time
import urllib.request
import urllib.error

ESP32_IP = "192.168.4.38"
STATE_PATH = "/state/current-state.json"
POLL_INTERVAL = 2  # seconds

# Phase → ESP32 animation mapping (matches lyla.html lines 208-215)
PHASE_TO_ANIMATION = {
    'ACT': 'fire',
    'REFLECT': 'pulse',
    'PERCEIVE': 'rainbow',
    'DECIDE': 'spin',
    'CONSOLIDATE': 'sparkle',
    'PERSIST': 'solid'
}

def fetch_state():
    """Fetch current state from local JSON file."""
    try:
        with open(STATE_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

def set_esp32_animation(animation_name):
    """Set ESP32 animation via HTTP GET."""
    url = f"http://{ESP32_IP}/anim?name={animation_name}"
    try:
        req = urllib.request.Request(url, method='GET')
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception as e:
        print(f"[DAEMON] ESP32 anim error: {e}")
        return False

def set_esp32_brightness(brightness):
    """Set ESP32 brightness via HTTP GET (range 0-255)."""
    # Clamp to valid range
    brightness = max(0, min(255, int(brightness)))
    url = f"http://{ESP32_IP}/bright?v={brightness}"
    try:
        req = urllib.request.Request(url, method='GET')
        urllib.request.urlopen(req, timeout=2)
        return True
    except Exception as e:
        print(f"[DAEMON] ESP32 bright error: {e}")
        return False

def main():
    print("[DAEMON] Starting state daemon...")
    print(f"[DAEMON] Target: ESP32 @ {ESP32_IP}")
    print(f"[DAEMON] Polling interval: {POLL_INTERVAL}s")
    
    last_state_hash = None
    
    while True:
        state = fetch_state()
        
        if state is None:
            time.sleep(POLL_INTERVAL)
            continue
        
        # Hash-based change detection to avoid redundant ESP32 calls
        current_hash = hash(json.dumps(state, sort_keys=True))
        if current_hash == last_state_hash:
            time.sleep(POLL_INTERVAL)
            continue
        last_state_hash = current_hash
        
        phase = state.get('phase', 'UNKNOWN')
        confidence = state.get('confidence', 0.5)
        
        # Map to hardware parameters
        animation = PHASE_TO_ANIMATION.get(phase, 'solid')
        brightness = int(confidence * 200 + 50)  # Range ~50-250
        
        # Update ESP32
        set_esp32_animation(animation)
        set_esp32_brightness(brightness)
        
        print(f"[DAEMON] C{state.get('cycle', '?')} {phase} ({confidence:.2f}) → {animation} @ {brightness}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[DAEMON] Shutting down...")
