import json
import os
from datetime import datetime

STATE_DIR = "state"
LOG_FILE = "logs/consciousness.log"

def load_json(filename):
    path = os.path.join(STATE_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def log_event(message):
    timestamp = datetime.now().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{timestamp}] [GOVERNOR_EVENT] {message}\n")

def monitor_telemetry():
    """
    Reads current state metrics and compares them against governance thresholds.
    Triggers domain shifts or focus recalibration if thresholds are breached.
    """
    current_state = load_json("current-state.json")
    thresholds_data = load_json("governance-thresholds.json")
    focus = load_json("focus.json")

    if not thresholds_data or not current_state:
        print("Insufficient state data for telemetry monitoring.")
        return

    # The thresholds file has a "metrics" wrapper
    thresholds = thresholds_data.get("metrics", {})
    metrics = current_state.get("metrics", {})
    actions_taken = []

    # Check Resonance Volatility
    res_vol = metrics.get("resonance_volatility", 0)
    res_thresh_cfg = thresholds.get("resonance_volatility", {})
    res_thresh = res_thresh_cfg.get("warning", 0.7)
    if res_vol > res_thresh:
        log_event(f"Resonance volatility ({res_vol}) exceeded threshold ({res_thresh}). Triggering force_domain_shift.")
        focus["suggested_action"] = "force_domain_shift"
        focus["reason"] = "High resonance volatility"
        actions_taken.append("force_domain_shift")

    # Check Signal-to-Noise Ratio
    snr = metrics.get("signal_to_noise_ratio", 1.0)
    snr_thresh_cfg = thresholds.get("signal_to_noise_ratio", {})
    snr_thresh = snr_thresh_cfg.get("critical", 0.8) # Using critical as a baseline for this implementation
    if snr < snr_thresh:
        log_event(f"SNR ({snr}) dropped below threshold ({snr_thresh}). Triggering recalibrate_attentional_focus.")
        focus["suggested_action"] = "recalibrate_attentional_focus"
        focus["reason"] = "Low signal-to-noise ratio"
        actions_taken.append("recalibrate_attentional_focus")

    # Persist focus changes if actions were triggered
    if actions_taken:
        with open(os.path.join(STATE_DIR, "focus.json"), 'w') as f:
            json.dump(focus, f, indent=4)
        print(f"Telemetry Monitor triggered: {', '.join(actions_taken)}")
    else:
        print("Telemetry within nominal parameters.")

if __name__ == "__main__":
    monitor_telemetry()
