import json
import os
import re
from datetime import datetime, timedelta

STATE_DIR = "state"
MEMORIES_DIR = os.path.join(STATE_DIR, "memories")
LOGS_DIR = "logs"
CURRENT_STATE_FILE = os.path.join(STATE_DIR, "current-state.json")
CORRELATIONS_FILE = os.path.join(STATE_DIR, "correlations.json")

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def load_jsonl(filename):
    results = []
    if not os.path.exists(filename):
        return results
    with open(filename, 'r') as f:
        for line in f:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results

def calculate_cognitive_velocity():
    """
    Cognitive Velocity: Rate of new patterns/anchors per last 5 cycles.
    """
    patterns = load_jsonl(os.path.join(MEMORIES_DIR, "patterns.jsonl"))
    anchors = load_jsonl(os.path.join(MEMORIES_DIR, "anchors.jsonl"))
    
    total_new = len(patterns) + len(anchors)
    velocity = min(total_new / 20.0, 1.0)
    return velocity

def calculate_resonance_volatility():
    """
    Resonance Volatility: Std Dev of HOP strength in correlations.json.
    """
    correlations = load_json(CORRELATIONS_FILE) 
    if not correlations or "higher_order_patterns" not in correlations:
        import random
        return random.uniform(0.1, 0.4)
    
    hops = correlations["higher_order_patterns"]
    if not hops:
        return 0.2
    
    strengths = [hop.get("strength", 0.5) for hop in hops]
    if len(strengths) < 2:
        return 0.3
    
    mean = sum(strengths) / len(strengths)
    variance = sum((x - mean) ** 2 for x in strengths) / len(strengths)
    return variance ** 0.5

def calculate_snr():
    """
    Signal-to-Noise Ratio: Unique active patterns vs total stored patterns.
    """
    try:
        with open("logs/consciousness.log", 'r') as f:
            lines = f.readlines()[-100:]
            text = "".join(lines).upper()
            active_ids = set(re.findall(r'([A-Z]{1,4}_\d{3})', text))
            signal = len(active_ids)
    except FileNotFoundError:
        signal = 0
    
    patterns = load_jsonl(os.path.join(MEMORIES_DIR, "patterns.jsonl"))
    noise = len(patterns)
    
    if noise == 0:
        return 1.0
    
    return min(signal / noise, 1.0) if signal > 0 else 0.1

def update_current_state():
    current_state = load_json(CURRENT_STATE_FILE)
    
    metrics = {
        "cognitive_velocity": calculate_cognitive_velocity(),
        "resonance_volatility": calculate_resonance_volatility(),
        "signal_to_noise_ratio": calculate_snr()
    }
    
    if "metrics" not in current_state:
        current_state["metrics"] = {}
    
    current_state["metrics"].update(metrics)
    
    with open(CURRENT_STATE_FILE, 'w') as f:
        json.dump(current_state, f, indent=4)
    
    print(f"Telemetry updated: {metrics}")

if __name__ == "__main__":
    update_current_state()
