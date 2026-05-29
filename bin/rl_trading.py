#!/usr/bin/env python3
"""RL Trading Agent — Q-learning on historical price data.

Applies the RL toolkit (C527-C533) to a real financial problem: learning
a buy/hold/sell policy from historical OHLCV data. Benchmarks against
buy-and-hold baseline.

State: discretized features (recent returns, momentum, volatility)
Actions: BUY (1), HOLD (0), SELL (-1)
Reward: return of held asset minus return of cash (opportunity cost)

Usage:
    python3 bin/rl_trading.py --symbol AAPL
    python3 bin/rl_trading.py --symbol SPY --start 2023-01-01
    python3 bin/rl_trading.py --json
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    print("ERROR: pip install yfinance numpy")
    sys.exit(1)


def discretize_value(value, bins, low, high):
    """Clip and bin a continuous value to a discrete index."""
    clamped = max(low, min(high, value))
    bucket = (clamped - low) / (high - low) * (bins - 1)
    return int(round(bucket))


def make_state(features, in_position, n_bins=5):
    """Convert continuous features to discrete state tuple.

    Features: [return_1d, return_5d, volatility_10d, rsi_14]
    State includes position status so agent knows if it can sell.
    Ranges: returns [-0.05, 0.05], volatility [0, 0.1], rsi [0, 100]
    """
    ret_1 = discretize_value(features[0], n_bins, -0.05, 0.05)
    ret_5 = discretize_value(features[1], n_bins, -0.05, 0.05)
    vol = discretize_value(features[2], n_bins, 0, 0.1)
    rsi = discretize_value(features[3], n_bins, 0, 100)
    return (ret_1, ret_5, vol, rsi, 1 if in_position else 0)


def compute_features(prices, volumes=None):
    """Compute trading features from price history.

    Returns list of feature vectors, one per timestamp (None for warmup).
    """
    n = len(prices)
    returns = [0.0]
    for i in range(1, n):
        returns.append((prices[i] - prices[i - 1]) / prices[i - 1])

    features = []
    for i in range(n):
        if i < 14:
            features.append(None)  # Warmup
            continue

        ret_1d = returns[i]
        ret_5d = (prices[i] - prices[i - 5]) / prices[i - 5] if i >= 5 else 0

        # Rolling volatility (10-day)
        window = prices[max(0, i - 10):i]
        if len(window) >= 2:
            window_returns = [(window[j] - window[j - 1]) / window[j - 1]
                              for j in range(1, len(window))]
            vol = (sum(r ** 2 for r in window_returns) / len(window_returns)) ** 0.5
        else:
            vol = 0.0

        # RSI (14-day)
        if i >= 14:
            gains = []
            losses = []
            for j in range(i - 13, i + 1):
                r = returns[j]
                if r > 0:
                    gains.append(r)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(r))
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
        else:
            rsi = 50

        features.append([ret_1d, ret_5d, vol, rsi])

    return features


class QLearningTrader:
    """Q-learning agent for trading with position management."""

    def __init__(self, alpha=0.1, gamma=0.9, epsilon=1.0, epsilon_decay=0.995,
                 epsilon_min=0.05, n_bins=5):
        self.q_table = {}
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.n_bins = n_bins
        self.actions = [0, 1, 2]  # HOLD, BUY, SELL

    def get_q(self, state, action):
        return self.q_table.get((state, action), 0.0)

    def best_action(self, state):
        return max(self.actions, key=lambda a: self.get_q(state, a))

    def choose_action(self, state):
        if np.random.random() < self.epsilon:
            return np.random.choice(self.actions)
        return self.best_action(state)

    def update(self, state, action, reward, next_state):
        best_next = max(self.actions, key=lambda a: self.get_q(next_state, a))
        target = reward + self.gamma * self.get_q(next_state, best_next)
        current = self.get_q(state, action)
        self.q_table[(state, action)] = current + self.alpha * (target - current)

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

def run_trading_simulation(prices, agent, features):
    """Simulate trading with the RL agent over historical prices.

    Returns: equity curve, trades log, final equity
    """
    initial_capital = 10000.0
    cash = initial_capital
    position = 0  # shares held
    equity_curve = [initial_capital]
    trades = []

    for t in range(1, len(prices)):
        if features[t - 1] is None:
            equity_curve.append(cash + position * prices[t])
            continue
        in_pos = position > 0
        state = make_state(features[t - 1], in_pos, agent.n_bins)
        next_features = features[t]
        if next_features is None:
            equity_curve.append(cash + position * prices[t])
            continue
        next_state = make_state(next_features, in_pos, agent.n_bins)

        action = agent.choose_action(state)
        price = prices[t]
        prev_price = prices[t - 1]
        ret = (price - prev_price) / prev_price

        # Execute action
        if action == 1:  # BUY
            if cash >= price and position == 0:
                shares = int(cash / price)
                if shares > 0:
                    position = shares
                    cash -= shares * price
                    trades.append({"t": t, "action": "BUY", "price": price})
        elif action == 2:  # SELL
            if position > 0:
                cash += position * price
                trades.append({"t": t, "action": "SELL", "price": price})
                position = 0

        # Reward: return relative to buy-and-hold
        # If holding: you gain ret. If flat: you miss ret.
        # This incentivizes being in the market when it goes up.
        if position > 0:
            reward = ret
        else:
            reward = -ret * 0.5  # Mild penalty for being flat

        agent.update(state, action, reward, next_state)
        equity = cash + position * prices[t]
        equity_curve.append(equity)

    # Force close at end
    if position > 0:
        cash += position * prices[-1]

    return equity_curve, trades, cash


def compute_metrics(equity_curve, label=""):
    """Compute performance metrics from equity curve."""
    if len(equity_curve) < 2:
        return {"label": label, "total_return_pct": 0, "sharpe_ratio": 0,
                "max_drawdown_pct": 0, "final_equity": equity_curve[-1] if equity_curve else 0}

    returns = [(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
               for i in range(1, len(equity_curve))]
    returns_arr = np.array(returns)

    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100

    sharpe = 0
    if np.std(returns_arr) > 0:
        sharpe = np.sqrt(252) * np.mean(returns_arr) / np.std(returns_arr)

    # Max drawdown
    running_max = np.maximum.accumulate(np.array(equity_curve))
    drawdown = (np.array(equity_curve) - running_max) / running_max
    max_dd = abs(np.min(drawdown)) * 100

    return {
        "label": label,
        "final_equity": round(equity_curve[-1], 2),
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd, 2),
    }


def buy_and_hold_equity(prices, initial_capital=10000.0):
    """Compute equity curve for buy-and-hold strategy."""
    shares = initial_capital / prices[0]
    return [shares * p for p in prices]


def main():
    parser = argparse.ArgumentParser(description="RL Trading Agent — Q-learning on price data")
    parser.add_argument("--symbol", default="AAPL", help="Stock symbol")
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default=None, help="End date (default: today)")
    parser.add_argument("--episodes", type=int, default=50, help="Training episodes")
    parser.add_argument("--alpha", type=float, default=0.15, help="Learning rate")
    parser.add_argument("--gamma", type=float, default=0.95, help="Discount factor")
    parser.add_argument("--epsilon-decay", type=float, default=0.99, help="Epsilon decay per episode")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    # Fetch data
    end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticker = yf.Ticker(args.symbol)
    df = ticker.history(start=args.start, end=end_date)

    if df.empty:
        print(f"No data for {args.symbol}")
        sys.exit(1)

    prices = df["Close"].values.tolist()
    n_days = len(prices)

    if not args.json:
        print(f"RL Trading Agent — {args.symbol} ({n_days} trading days)")
        print(f"Period: {args.start} to {end_date}")
        print(f"Price range: ${min(prices):.2f} — ${max(prices):.2f}")
        print()

    features = compute_features(prices)

    # Train one agent over multiple episodes (Q-learning accumulates across episodes)
    agent = QLearningTrader(
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=1.0,
        epsilon_decay=args.epsilon_decay,
        epsilon_min=0.01,
    )

    best_equity = None

    for episode in range(args.episodes):
        equity, trades, _ = run_trading_simulation(prices, agent, features)
        agent.decay_epsilon()

        if best_equity is None or equity[-1] > best_equity[-1]:
            best_equity = equity

        if not args.json and (episode + 1) % 10 == 0:
            metrics = compute_metrics(equity, f"Episode {episode + 1}")
            print(f"  Episode {episode + 1}: Equity=${metrics['final_equity']:,.2f} "
                  f"Return={metrics['total_return_pct']:+.1f}% "
                  f"Sharpe={metrics['sharpe_ratio']:.2f} "
                  f"Epsilon={agent.epsilon:.3f} "
                  f"Q-size={len(agent.q_table)}")

    # Baseline: buy and hold
    bh_equity = buy_and_hold_equity(prices)
    bh_metrics = compute_metrics(bh_equity, "Buy & Hold")

    # Best training episode
    rl_metrics = compute_metrics(best_equity, "RL Best Ep")

    # Evaluation: greedy policy (no exploration) on trained agent
    eval_agent = QLearningTrader(alpha=0, gamma=0.95, epsilon=0, n_bins=agent.n_bins)
    eval_agent.q_table = agent.q_table.copy()
    eval_equity, _, _ = run_trading_simulation(prices, eval_agent, features)
    eval_metrics = compute_metrics(eval_equity, "RL Greedy")

    # Print results
    if not args.json:
        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"{'Strategy':<15} {'Final Equity':>14} {'Return':>10} {'Sharpe':>8} {'Max DD':>8}")
        print("-" * 60)
        for m in [bh_metrics, rl_metrics, eval_metrics]:
            print(f"{m['label']:<15} ${m['final_equity']:>12,.2f} {m['total_return_pct']:>9.1f}% "
                  f"{m['sharpe_ratio']:>7.2f} {m['max_drawdown_pct']:>7.1f}%")
        print("=" * 60)

        if eval_metrics["total_return_pct"] > bh_metrics["total_return_pct"]:
            improvement = eval_metrics["total_return_pct"] - bh_metrics["total_return_pct"]
            print(f"\nRL outperformed buy-and-hold by {improvement:+.1f} percentage points")
        else:
            gap = bh_metrics["total_return_pct"] - eval_metrics["total_return_pct"]
            print(f"\nBuy-and-hold outperformed RL by {gap:.1f} percentage points")
            print("  (RL learned from {0} state-action pairs in Q-table)".format(
                len(agent.q_table)))

        print(f"\nQ-table size: {len(agent.q_table)} state-action pairs")
        print(f"State space: {args.episodes} episodes of exploration")

    # JSON output
    result = {
        "cycle": "C534",
        "symbol": args.symbol,
        "period": f"{args.start} to {end_date}",
        "trading_days": n_days,
        "episodes_trained": args.episodes,
        "q_table_size": len(agent.q_table),
        "buy_and_hold": bh_metrics,
        "rl_best_episode": rl_metrics,
        "rl_eval_no_exploration": eval_metrics,
        "beat_baseline": eval_metrics["total_return_pct"] > bh_metrics["total_return_pct"],
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Save to reports
        import os
        os.makedirs("reports", exist_ok=True)
        with open("reports/rl_trading.jsonl", "a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"\nResults saved to reports/rl_trading.jsonl")


if __name__ == "__main__":
    main()
