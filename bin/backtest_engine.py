#!/usr/bin/env python3
"""
Backtesting Engine — Replay historical price data with trading strategy,
compute performance metrics including Sharpe ratio.

Architecture pattern from C403 research:
- Signal generation layer (RSI + MA crossover)
- Execution engine (position management)
- Performance analyzer (Sharpe, drawdown, win rate)

External-subject artifact: interfaces with real market history, produces
objectively measurable outcomes per P_C403_FALSIFIABILITY pattern.
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
    print("Install via: pip install yfinance pandas numpy")
    sys.exit(1)

# Optional QAE integration for volatility regime detection
QAE_AVAILABLE = False
try:
    from bin.qae_volatility_estimator import QAEVolatilityEstimator
    QAE_AVAILABLE = True
except ImportError:
    pass  # Will run without quantum signals if QAE unavailable


class BacktestEngine:
    """Historical backtesting with RSI + MA crossover signals."""
    
    def __init__(self, symbol: str = "AAPL", start_date: str = None, end_date: str = None, use_qae_regimes: bool = False):
        self.symbol = symbol.upper()
        self.start_date = start_date or "2024-01-01"
        self.end_date = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.use_qae_regimes = use_qae_regimes
        
        # Download historical data
        self.df = self._download_data()
        
        # QAE volatility estimator (if enabled)
        if self.use_qae_regimes and QAE_AVAILABLE:
            self.qae_estimator = QAEVolatilityEstimator(use_simulator=True)
            print(f"[INFO] QAE volatility regime detection ENABLED")
        else:
            self.qae_estimator = None
            if self.use_qae_regimes and not QAE_AVAILABLE:
                print("[WARNING] QAE requested but unavailable - running classical mode")
        
        # Strategy state
        self.positions = {}  # {symbol: {"shares": N, "avg_cost": X}}
        self.trades_log = []
        self.equity_curve = []  # [timestamp, equity]
        
        # Parameters
        self.rsi_window = 14
        self.ma_short_window = 20
        self.ma_long_window = 50
        
    def _download_data(self) -> pd.DataFrame:
        """Download OHLCV data from Yahoo Finance."""
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
    
    def calculate_indicators(self):
        """Calculate RSI and moving averages."""
        df = self.df
        
        # RSI calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_window).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Moving averages
        df['MA_short'] = df['Close'].rolling(window=self.ma_short_window).mean()
        df['MA_long'] = df['Close'].rolling(window=self.ma_long_window).mean()
        
        self.df = df
    
    def _compute_volatility_features(self, current_idx: int, window: int = 20) -> np.ndarray:
        """Compute features for QAE volatility regime detection.
        
        Returns a feature vector [rolling_vol, volume_change] normalized to [0,1].
        These are the same features used in qae_volatility_estimator.py test cases.
        """
        if self.qae_estimator is None or current_idx < window:
            # Fallback: low volatility regime if insufficient data
            return np.array([0.1, 0.1])
        
        recent_data = self.df.iloc[max(0, current_idx - window):current_idx + 1]['Close']
        
        # Rolling volatility (standard deviation of returns)
        returns = recent_data.pct_change().dropna()
        rolling_vol = returns.std() * np.sqrt(252)  # Annualized
        
        # Volume change (if available, else use price momentum as proxy)
        if 'Volume' in self.df.columns:
            vol_changes = self.df.iloc[max(0, current_idx - window):current_idx + 1]['Volume'].pct_change().dropna()
            volume_change = abs(vol_changes.mean()) if len(vol_changes) > 0 else 0.1
        else:
            # Use price momentum as fallback
            price_momentum = recent_data.pct_change().mean()
            volume_change = abs(price_momentum)
        
        # Normalize to [0,1] range based on typical market ranges
        normalized_vol = min(rolling_vol / 0.5, 1.0)  # Cap at 50% annual vol
        normalized_volume = min(volume_change / 0.2, 1.0)  # Cap at 20% volume change
        
        return np.array([normalized_vol, normalized_volume])
    
    def generate_signal(self, row) -> str:
        """Generate trading signal based on RSI + MA crossover, optionally filtered by QAE volatility regimes."""
        if pd.isna(row['RSI']) or pd.isna(row['MA_short']):
            return "HOLD"  # Not enough data yet
        
        rsi = row['RSI']
        ma_short = row['MA_short']
        ma_long = row['MA_long']
        price = row['Close']
        
        # Classical signal (unconditional)
        bullish_trend = ma_short > ma_long * 1.001  # Short above long by >0.1%
        bearish_trend = ma_short < ma_long * 0.999   # Short below long by >0.1%
        
        classical_signal = None
        if rsi < 40 and bullish_trend:
            classical_signal = "BUY"
        elif rsi > 60:
            classical_signal = "SELL"
        elif bearish_trend:
            classical_signal = "SELL"
        else:
            classical_signal = "HOLD"
        
        # If QAE enabled, apply regime filter at current index position
        if self.qae_estimator is not None and hasattr(self, '_current_idx'):
            vol_features = self._compute_volatility_features(self._current_idx)
            
            qae_result = self.qae_estimator.estimate(vol_features, target_prob=0.5)
            high_vol_prob = qae_result['estimate']
            
            # Regime-aware adjustment: reduce exposure in high-vol regimes
            # Threshold: if P(high vol) > 0.6, be more conservative on buys
            if high_vol_prob > 0.6 and classical_signal == "BUY":
                # Upgrade to HOLD - don't buy into potential volatility spike
                signal = "HOLD (high vol regime)"
                print(f"[QAE REGIME] High vol warning (P={high_vol_prob:.2f}) — suppressing BUY")
            elif high_vol_prob < 0.3 and classical_signal == "SELL":
                # Low vol regime may allow holding through temporary dips
                if rsi < 50:  # Not overbought yet
                    signal = "HOLD (low vol regime)"
                    print(f"[QAE REGIME] Low vol regime (P={high_vol_prob:.2f}) — allowing hold")
                else:
                    signal = classical_signal
            else:
                signal = classical_signal
            
            # Log regime info for comparison runs
            if hasattr(self, '_qae_log'):
                self._qae_log.append({
                    'timestamp': row.name.strftime("%Y-%m-%d") if hasattr(row.name, 'strftime') else str(row.name),
                    'vol_features': vol_features.tolist(),
                    'high_vol_prob': round(high_vol_prob, 3),
                    'classical_signal': classical_signal,
                    'adjusted_signal': signal
                })
        else:
            signal = classical_signal
        
        return signal
    
    def execute_backtest(self):
        """Run backtest over historical data."""
        self.calculate_indicators()
        
        initial_capital = 10000.0
        cash = initial_capital
        
        # Position sizing: use fixed fraction of capital per trade
        position_size_pct = 0.30  # 30% of equity per trade
        
        # Initialize QAE logging if enabled
        if self.qae_estimator is not None:
            self._qae_log = []
            self._current_idx = 0
            print(f"\n[QAE REGIME DETECTION ENABLED]")
        
        print(f"\n{'='*60}")
        print(f"BACKTEST: {self.symbol} | {self.start_date} to {self.end_date}")
        print(f"Initial capital: ${initial_capital:,.2f}")
        print(f"Position size: ~{position_size_pct*100}% of equity")
        print(f"{'='*60}\n")
        
        for i, (idx, row) in enumerate(self.df.iterrows()):
            timestamp = row.name.strftime("%Y-%m-%d %H:%M:%S") if hasattr(row.name, 'strftime') else str(row.name)
            
            # Store previous MA values for crossover detection
            if i > 0:
                prev_row = self.df.iloc[i - 1]
                row['MA_short_prev'] = prev_row['MA_short']
                row['MA_long_prev'] = prev_row['MA_long']
            
            # Set current index for QAE feature computation
            if hasattr(self, '_current_idx'):
                self._current_idx = i
            
            signal = self.generate_signal(row)
            price = row['Close']
            
            current_equity = cash + sum(p["shares"] * p["avg_cost"] for p in self.positions.values())
            position_value = sum(p["shares"] * p["avg_cost"] for p in self.positions.values())
            
            # Execute trades
            if signal == "BUY" and cash >= price:
                # If we have a position, sell it first (close before reopening)
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
                        "rsi": round(row['RSI'], 2),
                        "profit_loss": round(profit_loss, 2),
                        "signal_reason": f"Position closed before re-entry"
                    }
                    self.trades_log.append(trade)
                    
                    del self.positions[self.symbol]
                
                # Open new position with fixed sizing
                max_shares = int((cash * position_size_pct) / price)
                if max_shares > 0:
                    cost = max_shares * price
                    cash -= cost
                    
                    total_cost = cost
                    avg_cost = price
                    
                    self.positions[self.symbol] = {"shares": max_shares, "avg_cost": avg_cost}
                    
                    trade = {
                        "timestamp": timestamp,
                        "symbol": self.symbol,
                        "action": "BUY",
                        "price": round(price, 2),
                        "shares": max_shares,
                        "rsi": round(row['RSI'], 2),
                        "signal_reason": f"RSI <40 + bullish MA, size={max_shares} shares (${cost:.0f})"
                    }
                    self.trades_log.append(trade)
                    print(f"[{timestamp}] BUY {max_shares} @ ${price:.2f} | RSI={row['RSI']:.1f}")
            
            elif signal == "SELL" and self.symbol in self.positions and self.positions[self.symbol]["shares"] > 0:
                # Close entire position
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
                    "rsi": round(row['RSI'], 2),
                    "profit_loss": round(profit_loss, 2),
                    "signal_reason": f"RSI >60 / bearish trend"
                }
                self.trades_log.append(trade)
                print(f"[{timestamp}] SELL {shares_to_sell} @ ${price:.2f} | P/L=${profit_loss:+.2f}")
                
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
        
        # Log QAE regime analysis if enabled
        if hasattr(self, '_qae_log') and self._qae_log:
            print(f"\n{'='*60}")
            print(f"QAE REGIME ANALYSIS ({len(self._qae_log)} data points)")
            print(f"{'='*60}")
            
            high_vol_count = sum(1 for entry in self._qae_log if entry['high_vol_prob'] > 0.5)
            low_vol_count = sum(1 for entry in self._qae_log if entry['high_vol_prob'] < 0.3)
            
            print(f"High vol regime periods (P>0.5): {high_vol_count} ({100*high_vol_count/len(self._qae_log):.1f}%)")
            print(f"Low vol regime periods (P<0.3):  {low_vol_count} ({100*low_vol_count/len(self._qae_log):.1f}%)")
            
            # Show first few regime decisions
            print("\nSample regime-filtered signals:")
            for entry in self._qae_log[:5]:
                print(f"  {entry['timestamp']}: classical={entry['classical_signal']} → adjusted={entry['adjusted_signal']} (P(high vol)={entry['high_vol_prob']:.2f})")
            
            if len(self._qae_log) > 5:
                print(f"... and {len(self._qae_log) - 5} more points logged")
        
        return self._calculate_metrics(initial_capital)
    
    def _calculate_metrics(self, initial_capital: float) -> dict:
        """Calculate performance metrics."""
        final_equity = self.equity_curve[-1]["equity"] if self.equity_curve else initial_capital
        
        # Simple returns calculation
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_eq = self.equity_curve[i-1]["equity"]
            curr_eq = self.equity_curve[i]["equity"]
            ret = (curr_eq - prev_eq) / prev_eq if prev_eq > 0 else 0
            returns.append(ret)
        
        if not returns:
            returns = [0]
        
        returns_arr = np.array(returns)
        
        # Sharpe ratio (annualized, assuming 252 trading days, risk-free rate = 0)
        sharpe_ratio = np.sqrt(252) * np.mean(returns_arr) / np.std(returns_arr) if np.std(returns_arr) > 0 else 0
        
        # Max drawdown
        equity_arr = np.array([e["equity"] for e in self.equity_curve])
        running_max = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        # Win rate
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
            "avg_trade_pnl": round(np.mean([t.get("profit_loss", 0) for t in self.trades_log if t.get("action") == "SELL"]), 2)
        }
        
        return metrics
    
    def save_results(self, metrics: dict):
        """Save backtest results to JSONL."""
        log_path = Path("reports/backtests.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        result_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **metrics,
            "equity_curve_sample": self.equity_curve[-10:]  # Last 10 points
        }
        
        with open(log_path, "a") as f:
            f.write(json.dumps(result_record) + "\n")
        
        print(f"\n[INFO] Results saved to {log_path}")


def main():
    parser = argparse.ArgumentParser(description="Backtesting Engine — Historical market data analysis")
    parser.add_argument("--symbol", "-s", default="AAPL", help="Stock symbol (default: AAPL)")
    parser.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD, defaults to today)")
    parser.add_argument("--use-qae-regimes", action="store_true", help="Enable QAE volatility regime detection")
    parser.add_argument("--compare", action="store_true", help="Run both with and without QAE for comparison")
    
    args = parser.parse_args()
    
    use_qae = args.use_qae_regimes and QAE_AVAILABLE
    
    if use_qae and not QAE_AVAILABLE:
        print("WARNING: --use-qae-regimes requested but QAEVolatilityEstimator unavailable. Running without quantum signals.")
        use_qae = False
    
    engine = BacktestEngine(
        symbol=args.symbol,
        start_date=args.start or "2024-01-01",
        end_date=args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        use_qae_regimes=use_qae
    )
    
    metrics = engine.execute_backtest()
    engine.save_results(metrics)
    
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    for key, value in metrics.items():
        if not isinstance(value, (dict, list)):
            print(f"{key}: {value}")
    print("="*60)
    
    # Check prediction target
    if metrics["sharpe_ratio"] > 1.0:
        print("\n✅ SHARPE RATIO TARGET MET (>1.0)")
    else:
        print(f"\n⏳ Sharpe ratio: {metrics['sharpe_ratio']:.3f} (target: >1.0)")


if __name__ == "__main__":
    main()
