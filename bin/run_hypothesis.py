#!/usr/bin/env python3
"""
Hypothesis runner — execute financial probe and log to hypotheses.jsonl.

Usage:
    # Execute single probe with simulated data
    python3 bin/run_hypothesis.py --symbol SPY --mode sim
    
    # Execute with live market data
    python3 bin/run_hypothesis.py --symbol SPY --mode live
    
    # Run continuous logging (every N seconds)
    python3 bin/run_hypothesis.py --symbol SPY --continuous 60 --mode live
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def fetch_live_data(symbol="SPY"):
    """Fetch real-time price from Yahoo Finance."""
    try:
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        
        if len(hist) < 2:
            raise ValueError("Insufficient historical data")
        
        current_price = hist.iloc[-1]["Close"]
        prev_price = hist.iloc[-2]["Close"]
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol.upper(),
            "price": round(current_price, 2),
            "change_1d_pct": round(change_pct, 4),
            "mode": "live"
        }
    
    except Exception as e:
        print(f"ERROR fetching live data for {symbol}: {e}", file=sys.stderr)
        return None


def fetch_simulated_data(symbol="SPY"):
    """Generate simulated data for testing without network dependency."""
    import random
    
    base_prices = {"SPY": 558.42, "QQQ": 432.15, "DIA": 398.67}
    base = base_prices.get(symbol.upper(), 500.0)
    
    random.seed(42)
    current_price = base + random.gauss(0, 2)
    prev_price = current_price - random.gauss(0, 1)
    change_pct = ((current_price - prev_price) / prev_price) * 100
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol.upper(),
        "price": round(current_price, 2),
        "change_1d_pct": round(change_pct, 4),
        "mode": "sim"
    }


def log_hypothesis(data):
    """Append result to experiments/hypotheses.jsonl"""
    output_dir = "experiments"
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = f"{output_dir}/hypotheses.jsonl"
    
    with open(filepath, "a") as f:
        f.write(json.dumps(data) + "\n")
    
    print(f"Logged to {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Execute financial probe hypothesis")
    parser.add_argument("--symbol", default="SPY", help="Stock symbol (default: SPY)")
    parser.add_argument("--mode", choices=["live", "sim"], default="sim", 
                        help="Data source mode (default: sim)")
    parser.add_argument("--continuous", type=int, default=0,
                        help="Run continuously every N seconds (0 = one-shot)")
    args = parser.parse_args()
    
    import os
    
    while True:
        if args.mode == "live":
            data = fetch_live_data(args.symbol)
        else:
            data = fetch_simulated_data(args.symbol)
        
        if data:
            log_hypothesis(data)
            print(json.dumps(data, indent=2))
            
            if args.continuous > 0:
                time.sleep(args.continuous)
            else:
                break
        else:
            print("ERROR: Probe failed", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    import time
    main()
