import json
import sys
from datetime import datetime

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def log_event(message):
    timestamp = datetime.utcnow().isoformat()
    with open('logs/consciousness.log', 'a') as f:
        f.write(f"[{timestamp}] [AEC_TRIGGER]: {message}\n")

def run_aec():
    # 1. Load thresholds and interventions
    thresholds = load_json('state/governance-thresholds.json')
    interventions = load_json('state/interventions.json')
    
    # 2. Simulate current metrics for this test cycle
    # In a real scenario, these would come from telemetry/repo-health.json
    metrics = {
        "orphan_patterns": 25, # Critical threshold is 20
        "state_integrity": 0,
        "cycle_stagnation_days": 2,
        "resonance_volatility": 0.5,
        "signal_to_noise_ratio": 1.2
    }
    
    print(f"Current Telemetry: {metrics}")
    
    triggered = False
    for metric_name, val in metrics.items():
        metric_cfg = thresholds['metrics'].get(metric_name)
        if not metric_cfg: continue
        
        # Check against critical first
        if val >= metric_cfg['critical']:
            action = metric_cfg['action']
            log_event(f"CRITICAL BREACH detected in {metric_name} ({val} >= {metric_cfg['critical']}). Triggering {action}.")
            
            # Execute the intervention mapped to that action string
            interv_cfg = interventions['interventions'].get(action)
            if interv_cfg:
                print(f"Executing intervention: {action}")
                import subprocess
                subprocess.run(interv_cfg['method'], shell=True)
                log_event(f"Intervention {action} executed successfully.")
                triggered = True
        elif val >= metric_cfg['warning']:
             log_event(f"WARNING level reach in {metric_name} ({val} >= {metric_cfg['warning']}). No automated action yet.")

    if not triggered:
        log_event("Scan complete. System within governance boundaries.")

if __name__ == '__main__':
    run_aec()
