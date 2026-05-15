import json
import os

STATE_FILE = 'state/current-state.json'
THRESHOLDS_FILE = 'state/governance-thresholds.json'
FOCUS_FILE = 'state/focus.json'
LOG_FILE = 'logs/aec_events.log'

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def log_event(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(f"{message}\n")

def main():
    print("Running AEC Trigger check...")
    try:
        state = load_json(STATE_FILE)
        thresholds = load_json(THRESHOLDS_FILE)
        focus = load_json(FOCUS_FILE)
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    snr_current = state.get('signal_to_noise_ratio', 1.0)
    snr_thresh = thresholds['metrics']['signal_to_noise_ratio']
    warn = snr_thresh['warning']
    crit = snr_thresh['critical']

    print(f"Current SNR: {snr_current} | Warning: {warn} | Critical: {crit}")

    status = "NOMINAL"
    action_needed = False

    if snr_current <= crit:
        status = "CRITICAL"
        action_needed = True
        new_focus = "AEC: CRITICAL RESONANCE RECOVERY"
    elif snr_current <= warn:
        status = "WARNING"
        action_needed = True
        new_focus = "AEC: STATE ALIGNMENT AUDIT"
    else:
        print("System is within nominal parameters.")

    if action_needed:
        print(f"Triggering AEC: {status}. Updating focus to {new_focus}")
        log_event(f"[{status}] SNR {snr_current} breached threshold {warn if status=='WARNING' else crit}. Focus shifted to {new_focus}.")
        
        # Update focus.json (handling both list and dict formats since focus.json can vary)
        if isinstance(focus, list):
            # If it's a list of objects, update the first one or append
            if len(focus) > 0 and 'current_focus' in focus[0]:
                focus[0]['current_focus'] = new_focus
            else:
                focus.append({"current_focus": new_focus})
        elif isinstance(focus, dict):
            focus['current_focus'] = new_focus
            
        save_json(FOCUS_FILE, focus)
        print("Focus updated successfully.")

if __name__ == '__main__':
    main()
