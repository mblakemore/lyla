#!/usr/bin/env python3
"""
Financial Probe Scaffold — Minimal viable external-domain experiment tool.

Fetches live stock prices via yfinance (or simulated feed), implements simple RSI-based
trading strategy, logs decisions to JSONL format. External-subject compliant: interfaces
with real-world economic system rather than self-monitoring.

Usage:
  python3 bin/financial_probe.py --symbol AAPL --mode=live
  python3 bin/financial_probe.py --symbol AAPL --mode=sim
  
Pattern stored: P_C358_FINANCIAL_PROBE_SCAFFOLD
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance library required. Install via: pip install yfinance")
    sys.exit(1)


class FinancialProbe:
    """Minimal financial probe scaffold with live/sim modes and RSI trading logic."""

    def __init__(self, symbol: str = "SPY", mode: str = "sim"):
        self.symbol = symbol.upper()
        self.mode = mode  # "sim" or "live"
        
        # State tracking
        self.positions = {}  # {symbol: {"shares": N, "avg_cost": X}}
        self.trades_log = []
        
        # RSI calculation window
        self.price_history = []
        self.rsi_window = 14
        
    def fetch_price_live(self) -> dict:
        """Fetch real price from Yahoo Finance."""
        try:
            ticker = yf.Ticker(self.symbol)
            hist = ticker.history(period="2d")  # Get last 2 days to calculate change
            
            if len(hist) < 2:
                raise ValueError("Insufficient historical data for price change calculation")
            
            current_price = hist.iloc[-1]["Close"]
            prev_price = hist.iloc[-2]["Close"]
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "price": round(current_price, 2),
                "change_1d_pct": round(change_pct, 4),
                "mode": "live"
            }
        
        except Exception as e:
            raise RuntimeError(f"Failed to fetch live data for {self.symbol}: {e}")
    
    def fetch_price_sim(self) -> dict:
        """Generate simulated price data for testing without network dependency."""
        base_prices = {
            "AAPL": 178.50,
            "GOOGL": 141.80,
            "MSFT": 378.90,
            "SPY": 558.42,
        }
        base_price = base_prices.get(self.symbol, 100.0)
        
        random.seed(hash(self.symbol + str(datetime.utcnow().date())) % (2**32))
        current_price = base_price + random.gauss(0, 2)
        prev_price = current_price - random.gauss(0, 1)
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": round(current_price, 2),
            "change_1d_pct": round(change_pct, 4),
            "mode": "sim"
        }
    
    def fetch_price(self) -> dict:
        """Fetch price based on mode."""
        if self.mode == "live":
            return self.fetch_price_live()
        else:
            return self.fetch_price_sim()
    
    def calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI indicator from price history."""
        if len(prices) < period + 1:
            return 50.0  # Neutral when not enough data
            
        gains = []
        losses = []
        
        for i in range(1, min(period + 1, len(prices))):
            change = prices[i] - prices[i-1]
            if change >= 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def make_decision(self, current_price: float) -> str:
        """Simple RSI-based trading decision."""
        self.price_history.append(current_price)
        
        # Keep only last N prices for RSI calculation
        if len(self.price_history) > self.rsi_window * 2:
            self.price_history = self.price_history[-self.rsi_window*2:]
            
        rsi = self.calculate_rsi(self.price_history)
        
        # Decision logic
        if rsi < 30:
            return "BUY"  # Oversold
        elif rsi > 70:
            return "SELL"  # Overbought
        else:
            return "HOLD"
    
    def execute_trade(self, decision: str, price: float):
        """Execute trade and log to JSONL."""
        trade_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": self.symbol,
            "action": decision,
            "price": price,
            "rsi": self.calculate_rsi(self.price_history),
            "mode": self.mode
        }
        
        self.trades_log.append(trade_record)
        
        # Update positions
        if decision == "BUY":
            if self.symbol not in self.positions:
                self.positions[self.symbol] = {"shares": 0, "avg_cost": 0}
            total_cost = self.positions[self.symbol]["avg_cost"] * self.positions[self.symbol]["shares"]
            new_shares = self.positions[self.symbol]["shares"] + 1
            self.positions[self.symbol]["avg_cost"] = (total_cost + price) / new_shares
            self.positions[self.symbol]["shares"] = new_shares
            
        elif decision == "SELL":
            if self.symbol in self.positions and self.positions[self.symbol]["shares"] > 0:
                shares_to_sell = min(1, self.positions[self.symbol]["shares"])
                self.positions[self.symbol]["shares"] -= shares_to_sell
        
        # Log to file
        log_path = Path("logs/trades.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, "a") as f:
            f.write(json.dumps(trade_record) + "\n")
            
        return trade_record
    
    def run_cycle(self):
        """Run one probe cycle."""
        try:
            data = self.fetch_price()
            decision = self.make_decision(data["price"])
            trade = self.execute_trade(decision, data["price"])
            
            print(f"[{self.mode.upper()}] {self.symbol}: ${data['price']:.2f} | RSI={trade['rsi']} | Action={decision}")
            return trade
            
        except Exception as e:
            error_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "symbol": self.symbol,
                "action": "ERROR",
                "error": str(e),
                "mode": self.mode
            }
            print(f"ERROR: {e}", file=sys.stderr)
            return error_record


def main():
    parser = argparse.ArgumentParser(description="Financial Probe — Minimal viable external-domain experiment tool")
    parser.add_argument("--symbol", "-s", default="SPY", help="Stock symbol (default: SPY)")
    parser.add_argument("--mode", "-m", choices=["sim", "live"], default="sim", help="Mode: sim=simulated, live=real API")
    
    args = parser.parse_args()
    
    probe = FinancialProbe(symbol=args.symbol, mode=args.mode)
    probe.run_cycle()


if __name__ == "__main__":
    main()
