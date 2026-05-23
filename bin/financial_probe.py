#!/usr/bin/env python3
"""
Financial probe — minimal viable financial data fetcher for external-domain experiments.

Fetches S&P 500 (SPY) price data and outputs structured JSON suitable for logging/experiment tracking.

Usage:
    python3 bin/financial_probe.py --mode live   # Real market data via yfinance
    python3 bin/financial_probe.py --mode sim    # Simulated data (no network dependency)
"""

import argparse
import json
import random
from datetime import datetime, timezone


def fetch_live_data():
    """Fetch real SPY price from Yahoo Finance."""
    try:
        import yfinance as yf
        
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2d")  # Get last 2 days to calculate change
        
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
    random.seed(42)  # Reproducible results
    
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


def main():
    parser = argparse.ArgumentParser(description="Financial probe — minimal viable financial data fetcher")
    parser.add_argument("--mode", choices=["live", "sim"], default="sim", help="Data source mode (default: sim)")
    args = parser.parse_args()
    
    if args.mode == "live":
        data = fetch_live_data()
    else:
        data = fetch_simulated_data()
    
    if data:
        print(json.dumps(data, indent=2))
    else:
        print("ERROR: Failed to fetch data", file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    import sys
    main()
