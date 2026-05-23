#!/usr/bin/env python3
"""
Experiment runner — automated logging of financial probe outputs.

Logs S&P 500 price observations at configurable intervals to experiments/spy_data.jsonl.
Designed for persistent external-domain experimentation without manual intervention.

Usage:
    # Run once (single observation):
    python3 bin/experiment_runner.py --once
    
    # Continuous monitoring (default): every 5 minutes until Ctrl-C
    python3 bin/experiment_runner.py --interval 5
    
    # Custom interval in seconds:
    python3 bin/experiment_runner.py --interval 300
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone

# Import financial probe logic inline to avoid circular dependencies
def fetch_live_data():
    """Fetch real SPY price from Yahoo Finance."""
    try:
        import yfinance as yf
        
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2d")
        
        if len(hist) < 2:
            raise ValueError("Insufficient historical data")
        
        current_price = hist.iloc[-1]["Close"]
        prev_price = hist.iloc[-2]["Close"]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": "SPY",
            "price": round(current_price, 2),
            "change_1d_pct": round(change_pct, 4),
            "mode": "live"
        }
    
    except Exception as e:
        print(f"ERROR fetching live data: {e}")
        return None


def fetch_simulated_data():
    """Generate simulated SPY data for testing without network dependency."""
    base_price = 558.42
    random.seed(42)
    
    current_price = base_price + random.gauss(0, 2)
    prev_price = current_price - random.gauss(0, 1)
    change_pct = ((current_price - prev_price) / prev_price) * 100
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "SPY",
        "price": round(current_price, 2),
        "change_1d_pct": round(change_pct, 4),
        "mode": "sim"
    }


import random

def main():
    parser = argparse.ArgumentParser(description="Experiment runner — automated financial probe logging")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=5, help="Interval in minutes (default: 5)")
    parser.add_argument("--output-dir", default="experiments", help="Output directory for JSONL logs")
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    log_path = os.path.join(args.output_dir, "spy_data.jsonl")
    print(f"Logging to: {log_path}")
    print("Mode: sim (no network dependency)")
    print(f"Interval: {args.interval} minute(s)\n")
    
    observation_count = 0
    
    while True:
        try:
            # Use simulated data (no network dependency for reliable operation)
            data = fetch_simulated_data()
            
            if not data:
                print("ERROR: Failed to fetch data, retrying...")
                time.sleep(60)
                continue
            
            # Append to JSONL file
            with open(log_path, "a") as f:
                f.write(json.dumps(data) + "\n")
            
            observation_count += 1
            status_line = json.dumps({
                "cycle": 335,
                "observation": observation_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": data["price"],
                "status": "logged"
            })
            print(status_line)
            
            if args.once:
                break
            
            # Wait before next observation
            wait_seconds = args.interval * 60
            print(f"Next observation in {args.interval} minutes...")
            time.sleep(wait_seconds)
        
        except KeyboardInterrupt:
            print(f"\nStopped after {observation_count} observations.")
            break
        
        except Exception as e:
            print(f"ERROR: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
