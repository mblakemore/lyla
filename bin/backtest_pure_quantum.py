#!/usr/bin/env python3
"""
Pure Quantum Backtesting Engine — Quantum signals only (no classical indicators).

This script runs a backtest using exclusively quantum-derived trading signals,
with no RSI, MA, or other classical technical indicators. This enables direct
comparison against the classical-only baseline to test P_C406_PREDICTION_HYPOTHESIS:
"Quantum strategies outperform classical baseline."

Usage:
    python bin/backtest_pure_quantum.py --symbol AAPL --start 2024-01-01 --mode simulator
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"ERROR: Required libraries not installed")
    print("Install via: pip install yfinance pandas numpy qiskit")
    sys.exit(1)

# Import our quantum signal generator
sys.path.insert(0, str(Path(__file__).parent))
from quantum_signal_generator import QuantumSignalGenerator


class PureQuantumBacktestEngine:
    """Backtester using ONLY quantum signals — no classical indicators."""
    
    def __init__(self, symbol: str = "AAPL", start_date: str = None, end_date: str = None):
        self.symbol = symbol.upper()
        self.start_date = start_date or "2024-01-01"
        self.end_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        self.df = self._download_data()
        self.positions = {}
        self.trades_log = []
        self.equity_curve = []
        
        # Strategy parameters
        self.position_size_pct = 0.30
        
        # Quantum configuration
        self.quantum_mode = None
        self.quantum_api_key = None
        self.quantum_instance_id = None
    
    def _download_data(self) -> pd.DataFrame:
        try:
            ticker = yf.Ticker(self.symbol)
            df = ticker.history(start=self.start_date, end=self.end_date)
            
            if df.empty:
                raise ValueError(f"No data found for {self.symbol} in date range")
                
            print(f"[INFO] Loaded {len(df)} days of OHLCV data for {self.symbol}")
            return df
            
        except Exception as e:
            print(f"[ERROR] Failed to download data: {e}")
            sys.exit(1)
    
    def generate_quantum_signal(self, timestamp: str, price_change: float, rsi: float) -> dict:
        """Generate pure quantum signal (no classical indicators used)."""
        if not hasattr(self, '_quantum_gen'):
            self._quantum_gen = QuantumSignalGenerator(
                mode=self.quantum_mode,
                api_key=self.quantum_api_key,
                instance_id=self.quantum_instance_id
            )
        
        result = self._quantum_gen.generate_signal(
            timestamp=timestamp,
            symbol=self.symbol,
            price_change=price_change,
            rsi=rsi  # RSI is passed to quantum generator but NOT used by this backtester's logic
        )
        
        return result
    
    def execute_backtest(self):
        """Run backtest using ONLY quantum signals."""
        initial_capital = 10000.0
        cash = initial_capital
        
        print(f"\n{'='*60}")
        print(f"PURE QUANTUM BACKTEST: {self.symbol} | {self.start_date} to {self.end_date}")
        print(f"Mode: {'Quantum-only' if self.quantum_mode else 'Simulator fallback'}")
        print(f"Initial capital: ${initial_capital:,.2f}")
        print(f"Position size: {self.position_size_pct*100:.0%}")
        print(f"{'='*60}\n")
        
        for i, (idx, row) in enumerate(self.df.iterrows()):
            timestamp = row.name.strftime("%Y-%m-%d %H:%M:%S") if hasattr(row.name, 'strftime') else str(row.name)
            
            # Calculate rolling price change for quantum input
            if len(self.df) > 1:
                prev_row = self.df.iloc[max(0, self.df.index.get_loc(row.name) - 1)]
                price_change = (row['Close'] - prev_row['Close']) / prev_row['Close']
            else:
                price_change = 0
            
            # Generate pure quantum signal (no classical indicators involved)
            quantum_result = self.generate_quantum_signal(
                timestamp=timestamp,
                price_change=price_change,
                rsi=row.get('RSI', 50)  # RSI not used by this engine, just passed through
            )
            
            signal = quantum_result['signal']
            confidence = quantum_result['confidence']
            price = row['Close']
            current_equity = cash + sum(p["shares"] * p["avg_cost"] for p in self.positions.values())
            
            # Execute trades based on quantum signal only
            if signal in ["BUY", "STRONG_BUY"] and cash >= price:
                if self.symbol in self.positions and self.positions[self.symbol]["shares"] > 0:
                    shares_to_sell = self.positions[self.symbol]["shares"]
                    revenue = shares_to_sell * price
                    cash += revenue
                    
                    profit_loss = (price - self.positions[self.symbol]["avg_cost"]) * shares_to_sell
                    
                    trade = {
                        "timestamp": timestamp,
                        "symbol": self.symbol,
                        "action": "SELL",
                        "price": round(price, 2),
                        "shares": shares_to_sell,
                        "profit_loss": round(profit_loss, 2),
                        "signal_reason": f"Position closed before re-entry"
                    }
                    self.trades_log.append(trade)
                    
                    del self.positions[self.symbol]
                
                max_shares = int((cash * self.position_size_pct) / price)
                if max_shares > 0:
                    cost = max_shares * price
                    cash -= cost
                    
                    total_cost = cost
                    avg_cost = price
                    
                    self.positions[self.symbol] = {"shares": max_shares, "avg_cost": avg_cost}
                    
                    print(f"[{timestamp}] BUY {max_shares} @ ${price:.2f} | Q:{signal}@{confidence:.1%}")
            
            elif signal in ["SELL", "STRONG_SELL"] and self.symbol in self.positions and self.positions[self.symbol]["shares"] > 0:
                shares_to_sell = self.positions[self.symbol]["shares"]
                revenue = shares_to_sell * price
                cash += revenue
                
                profit_loss = (price - self.positions[self.symbol]["avg_cost"]) * shares_to_sell
                
                trade = {
                    "timestamp": timestamp,
                    "symbol": self.symbol,
                    "action": "SELL",
                    "price": round(price, 2),
                    "shares": shares_to_sell,
                    "profit_loss": round(profit_loss, 2),
                    "signal_reason": f"Quantum signal={signal}"
                }
                self.trades_log.append(trade)
                
                del self.positions[self.symbol]
            
            # Record equity
            position_value = sum(p["shares"] * p["avg_cost"] for p in self.positions.values())
            equity = cash + position_value
            self.equity_curve.append({
                "date": timestamp,
                "equity": equity,
                "cash": cash,
                "position_value": position_value
            })
        
        return self._calculate_metrics(initial_capital)
    
    def _calculate_metrics(self, initial_capital: float) -> dict:
        final_equity = self.equity_curve[-1]["equity"] if self.equity_curve else initial_capital
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_eq = self.equity_curve[i-1]["equity"]
            curr_eq = self.equity_curve[i]["equity"]
            ret = (curr_eq - prev_eq) / prev_eq if prev_eq > 0 else 0
            returns.append(ret)
        
        if not returns:
            returns = [0]
        
        returns_arr = np.array(returns)
        
        sharpe_ratio = np.sqrt(252) * np.mean(returns_arr) / np.std(returns_arr) if np.std(returns_arr) > 0 else 0
        
        equity_arr = np.array([e["equity"] for e in self.equity_curve])
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        winning_trades = [t for t in self.trades_log if t.get("action") == "SELL" and t.get("profit_loss", 0) > 0]
        losing_trades = [t for t in self.trades_log if t.get("action") == "SELL" and t.get("profit_loss", 0) <= 0]
        total_trades = len(winning_trades) + len(losing_trades)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        metrics = {
            "symbol": self.symbol,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "trading_days": len(self.df),
            "initial_capital": initial_capital,
            "final_equity": final_equity,
            "total_return_pct": ((final_equity - initial_capital) / initial_capital) * 100,
            "sharpe_ratio": round(sharpe_ratio, 3),
            "max_drawdown_pct": round(abs(max_drawdown) * 100, 2),
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate_pct": round(win_rate * 100, 1),
            "avg_trade_pnl": round(np.mean([t.get("profit_loss", 0) for t in self.trades_log if t.get("action") == "SELL"]), 2),
            "signal_mode": f"Pure Quantum ({self.quantum_mode or 'simulator'})"
        }
        
        return metrics
    
    def save_results(self, metrics: dict):
        log_path = Path("reports/backtests.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        result_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **metrics,
            "equity_curve_sample": self.equity_curve[-10:] if self.equity_curve else []
        }
        
        with open(log_path, "a") as f:
            f.write(json.dumps(result_record) + "\n")
        
        print(f"\n[INFO] Results saved to {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Pure Quantum Backtesting Engine — quantum signals only")
    parser.add_argument("--symbol", "-s", default="AAPL", help="Stock symbol (default: AAPL)")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--quantum-mode", choices=["simulator", "ibm_quantum"], default="simulator",
                       help="Quantum execution mode (default: simulator)")
    parser.add_argument("--api-key", default=None, help="IBM Quantum API key (for real device)")
    
    args = parser.parse_args()
    
    engine = PureQuantumBacktestEngine(
        symbol=args.symbol,
        start_date=args.start or "2024-01-01",
        end_date=args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    
    # Initialize quantum generator
    if args.quantum_mode in ["simulator", "ibm_quantum"]:
        gen_kwargs = {"mode": args.quantum_mode}
        if args.api_key:
            gen_kwargs["api_key"] = args.api_key
            
        engine.quantum_mode = args.quantum_mode
        engine.quantum_api_key = args.api_key
        print(f"[INFO] Pure quantum backtester initialized (mode: {args.quantum_mode})")
    
    metrics = engine.execute_backtest()
    engine.save_results(metrics)
    
    print("\n" + "="*60)
    print("PURE QUANTUM PERFORMANCE SUMMARY")
    print("="*60)
    for key, value in metrics.items():
        if not isinstance(value, (dict, list)):
            print(f"{key}: {value}")
    print("="*60)


if __name__ == "__main__":
    main()
