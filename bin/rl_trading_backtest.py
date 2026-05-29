#!/usr/bin/env python3
"""RL Trading Walk-Forward Backtest — Validates Q-learning under realistic conditions.

Extends C534 (rl_trading.py) with:
1. Transaction costs (bid-ask spread + commission)
2. Walk-forward validation (train on window, evaluate on out-of-sample)
3. Benchmark comparison (buy-and-hold, MA crossover)
4. Trade frequency analysis (does RL overtrade?)

Usage:
    python3 bin/rl_trading_backtest.py --symbol TSLA
    python3 bin/rl_trading_backtest.py --symbol SPY --windows 3
    python3 bin/rl_trading_backtest.py --json
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


# ── Feature computation (from C534, unchanged) ──────────────────────────

def discretize_value(value, bins, low, high):
    clamped = max(low, min(high, value))
    bucket = (clamped - low) / (high - low) * (bins - 1)
    return int(round(bucket))


def make_state(features, in_position, n_bins=5):
    ret_1 = discretize_value(features[0], n_bins, -0.05, 0.05)
    ret_5 = discretize_value(features[1], n_bins, -0.05, 0.05)
    vol = discretize_value(features[2], n_bins, 0, 0.1)
    rsi = discretize_value(features[3], n_bins, 0, 100)
    return (ret_1, ret_5, vol, rsi, 1 if in_position else 0)


def compute_features(prices):
    n = len(prices)
    returns = [0.0]
    for i in range(1, n):
        returns.append((prices[i] - prices[i - 1]) / prices[i - 1])

    features = []
    for i in range(n):
        if i < 14:
            features.append(None)
            continue

        ret_1d = returns[i]
        ret_5d = (prices[i] - prices[i - 5]) / prices[i - 5] if i >= 5 else 0

        window = prices[max(0, i - 10):i]
        if len(window) >= 2:
            window_returns = [(window[j] - window[j - 1]) / window[j - 1]
                              for j in range(1, len(window))]
            vol = (sum(r ** 2 for r in window_returns) / len(window_returns)) ** 0.5
        else:
            vol = 0.0

        if i >= 14:
            gains = [r if r > 0 else 0 for r in returns[i - 13:i + 1]]
            losses = [abs(r) if r < 0 else 0 for r in returns[i - 13:i + 1]]
            avg_gain = sum(gains) / len(gains)
            avg_loss = sum(losses) / len(losses)
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 100
        else:
            rsi = 50

        features.append([ret_1d, ret_5d, vol, rsi])

    return features


# ── Q-learning agent (from C534) ────────────────────────────────────────

class QLearningTrader:
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


# ── Simulation with transaction costs ───────────────────────────────────

def run_simulation_with_costs(prices, agent, features, cost_model=None):
    """Simulate trading with transaction costs.

    cost_model: dict with keys 'spread_bps' (bid-ask in basis points) and
                'commission_bps' (commission in basis points).
                Default: 10 bps spread + 2 bps commission = 12 bps per trade.
                Round trip: ~24 bps = 0.24%.
    """
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}

    spread = cost_model['spread_bps'] / 10000  # e.g., 10 bps = 0.001
    commission = cost_model['commission_bps'] / 10000

    initial_capital = 10000.0
    cash = initial_capital
    position = 0
    equity_curve = [initial_capital]
    trades = []
    total_cost = 0.0

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

        # Execute with costs
        if action == 1:  # BUY
            if cash >= price and position == 0:
                effective_price = price * (1 + spread)
                shares = int(cash / effective_price)
                if shares > 0:
                    cost = shares * effective_price * commission
                    position = shares
                    cash -= shares * effective_price + cost
                    total_cost += cost
                    trades.append({"t": t, "action": "BUY", "price": price,
                                   "shares": shares, "cost": cost})
        elif action == 2:  # SELL
            if position > 0:
                effective_price = price * (1 - spread)
                cost = position * effective_price * commission
                cash += position * effective_price - cost
                total_cost += cost
                trades.append({"t": t, "action": "SELL", "price": price,
                               "shares": position, "cost": cost})
                position = 0

        # Reward includes cost impact
        if position > 0:
            reward = ret
        else:
            reward = -ret * 0.5

        agent.update(state, action, reward, next_state)
        equity = cash + position * prices[t]
        equity_curve.append(equity)

    if position > 0:
        cash += position * prices[-1] * (1 - spread)

    return equity_curve, trades, cash, total_cost


# ── Benchmark: MA Crossover ────────────────────────────────────────────

def ma_crossover_equity(prices, short=10, long=30, initial_capital=10000.0,
                        cost_model=None):
    """Simple MA crossover strategy as benchmark."""
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}
    spread = cost_model['spread_bps'] / 10000
    commission = cost_model['commission_bps'] / 10000

    cash = initial_capital
    position = 0
    equity = [initial_capital]

    for t in range(len(prices)):
        if t < long:
            equity.append(cash + position * prices[t])
            continue

        short_ma = sum(prices[t - short:t]) / short
        long_ma = sum(prices[t - long:t]) / long

        if short_ma > long_ma and position == 0 and cash >= prices[t]:
            effective_price = prices[t] * (1 + spread)
            shares = int(cash / effective_price)
            if shares > 0:
                cost = shares * effective_price * commission
                position = shares
                cash -= shares * effective_price + cost
        elif short_ma <= long_ma and position > 0:
            effective_price = prices[t] * (1 - spread)
            cost = position * effective_price * commission
            cash += position * effective_price - cost
            position = 0

        equity.append(cash + position * prices[t])

    if position > 0:
        cash += position * prices[-1]

    return equity


# ── Walk-Forward Validation ────────────────────────────────────────────

def walk_forward_backtest(prices, features, n_windows, train_ratio=0.7,
                          episodes_per_window=50, cost_model=None):
    """Walk-forward validation: train on window, evaluate on out-of-sample.

    Splits data into n_windows segments. For each segment:
    - Train RL agent on the training portion (train_ratio of segment)
    - Evaluate on the remaining test portion (greedy policy, no exploration)
    - Agent starts fresh each window (no knowledge carryover)

    Returns list of per-window results and combined equity curve.
    """
    n = len(prices)
    window_size = n // n_windows

    window_results = []
    combined_equity = [10000.0]
    running_capital = 10000.0

    for w in range(n_windows):
        start = w * window_size
        end = start + window_size if w < n_windows - 1 else n
        train_end = start + int(window_size * train_ratio)

        train_prices = prices[start:train_end]
        train_features = features[start:train_end]
        test_prices = prices[train_end:end]
        test_features = features[train_end:end]

        # Train agent on training window
        agent = QLearningTrader(alpha=0.15, gamma=0.95, epsilon=1.0,
                                epsilon_decay=0.99, epsilon_min=0.01)

        for episode in range(episodes_per_window):
            _, _, _ = run_simulation_with_costs(
                train_prices, agent, train_features, cost_model)[:3]
            agent.decay_epsilon()

        # Evaluate on test window (greedy policy)
        eval_agent = QLearningTrader(alpha=0, gamma=0.95, epsilon=0, n_bins=5)
        eval_agent.q_table = agent.q_table.copy()

        test_equity, test_trades, _, test_cost = run_simulation_with_costs(
            test_prices, eval_agent, test_features, cost_model)

        if len(test_equity) > 1:
            test_return = (test_equity[-1] - test_equity[0]) / test_equity[0] * 100
        else:
            test_return = 0

        # Buy-and-hold on test window
        if len(test_prices) > 1:
            bh_return = (test_prices[-1] - test_prices[0]) / test_prices[0] * 100
        else:
            bh_return = 0

        window_results.append({
            "window": w + 1,
            "train_days": len(train_prices),
            "test_days": len(test_prices),
            "rl_return_pct": round(test_return, 2),
            "bh_return_pct": round(bh_return, 2),
            "spread_pct": round(test_return - bh_return, 2),
            "num_trades": len(test_trades),
            "total_cost": round(test_cost, 2),
            "q_table_size": len(agent.q_table),
            "beat_bh": test_return > bh_return,
        })

        # Update running capital for combined curve
        if len(test_equity) > 1:
            window_return = test_equity[-1] / test_equity[0]
            running_capital *= window_return

        # Extend combined equity curve
        if len(test_equity) > 1:
            scale = running_capital / test_equity[-1]
            combined_equity.extend([e * scale for e in test_equity[1:]])

    return window_results, combined_equity


# ── Metrics ─────────────────────────────────────────────────────────────

def compute_metrics(equity_curve, label=""):
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
    shares = initial_capital / prices[0]
    return [shares * p for p in prices]


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RL Trading Walk-Forward Backtest with Transaction Costs")
    parser.add_argument("--symbol", default="TSLA", help="Stock symbol")
    parser.add_argument("--start", default="2024-01-01", help="Start date")
    parser.add_argument("--end", default=None, help="End date")
    parser.add_argument("--windows", type=int, default=3, help="Walk-forward windows")
    parser.add_argument("--episodes", type=int, default=50, help="Episodes per window")
    parser.add_argument("--spread-bps", type=int, default=10, help="Bid-ask spread (bps)")
    parser.add_argument("--commission-bps", type=int, default=2, help="Commission (bps)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticker = yf.Ticker(args.symbol)
    df = ticker.history(start=args.start, end=end_date)

    if df.empty:
        print(f"No data for {args.symbol}")
        sys.exit(1)

    prices = df["Close"].values.tolist()
    features = compute_features(prices)
    n_days = len(prices)

    cost_model = {
        'spread_bps': args.spread_bps,
        'commission_bps': args.commission_bps,
    }
    round_trip_bps = (args.spread_bps + args.commission_bps) * 2

    if not args.json:
        print(f"RL Trading Walk-Forward Backtest — {args.symbol}")
        print(f"Period: {args.start} to {end_date} ({n_days} trading days)")
        print(f"Walk-forward: {args.windows} windows, {args.episodes} episodes/window")
        print(f"Transaction costs: {args.spread_bps} bps spread + {args.commission_bps} bps commission")
        print(f"Round trip cost: ~{round_trip_bps} bps ({round_trip_bps/100:.2f}%)")
        print()

    # Full dataset: train+eval on entire period (baseline)
    agent = QLearningTrader(alpha=0.15, gamma=0.95, epsilon=1.0,
                            epsilon_decay=0.99, epsilon_min=0.01)
    for ep in range(args.episodes):
        _, _, _ = run_simulation_with_costs(prices, agent, features, cost_model)[:3]
        agent.decay_epsilon()

    eval_agent = QLearningTrader(alpha=0, gamma=0.95, epsilon=0, n_bins=5)
    eval_agent.q_table = agent.q_table.copy()
    rl_equity, rl_trades, _, rl_total_cost = run_simulation_with_costs(
        prices, eval_agent, features, cost_model)

    bh_equity = buy_and_hold_equity(prices)
    ma_equity = ma_crossover_equity(prices, cost_model=cost_model)

    rl_metrics = compute_metrics(rl_equity, "RL (w/ costs)")
    bh_metrics = compute_metrics(bh_equity, "Buy & Hold")
    ma_metrics = compute_metrics(ma_equity, "MA Crossover")

    if not args.json:
        print("=" * 70)
        print("FULL DATASET — With Transaction Costs")
        print("=" * 70)
        print(f"{'Strategy':<18} {'Final Equity':>14} {'Return':>10} {'Sharpe':>8} {'Max DD':>8} {'Trades':>7}")
        print("-" * 70)
        for m in [bh_metrics, ma_metrics, rl_metrics]:
            trades_str = ""
            if m['label'] == rl_metrics['label']:
                trades_str = f"{len(rl_trades):>7}"
            print(f"{m['label']:<18} ${m['final_equity']:>12,.2f} {m['total_return_pct']:>9.1f}% "
                  f"{m['sharpe_ratio']:>7.2f} {m['max_drawdown_pct']:>7.1f}%{trades_str}")
        print("=" * 70)
        print(f"Total transaction costs (RL): ${rl_total_cost:.2f}")
        print(f"Q-table size: {len(agent.q_table)} state-action pairs")
        print()

        # Without costs comparison
        rl_equity_no_cost, _, _, _ = run_simulation_with_costs(
            prices, eval_agent, features, {'spread_bps': 0, 'commission_bps': 0})
        rl_no_cost_metrics = compute_metrics(rl_equity_no_cost, "RL (no costs)")
        print("COST IMPACT:")
        print(f"  RL return (no costs):  {rl_no_cost_metrics['total_return_pct']:+.1f}%")
        print(f"  RL return (w/ costs):  {rl_metrics['total_return_pct']:+.1f}%")
        cost_drag = rl_no_cost_metrics['total_return_pct'] - rl_metrics['total_return_pct']
        print(f"  Cost drag:             {cost_drag:+.1f} pp")
        print()

    # Walk-forward validation
    window_results, wf_equity = walk_forward_backtest(
        prices, features, args.windows, train_ratio=0.7,
        episodes_per_window=args.episodes, cost_model=cost_model)

    wf_metrics = compute_metrics(wf_equity, "WF RL (w/ costs)")

    if not args.json:
        print("=" * 70)
        print("WALK-FORWARD VALIDATION — Out-of-Sample Performance")
        print("=" * 70)
        print(f"{'Window':>7} {'Train':>7} {'Test':>7} {'RL Ret%':>9} {'B&H Ret%':>9} {'Spread':>8} {'Trades':>7} {'Beat?':>6}")
        print("-" * 70)
        for wr in window_results:
            beat = "YES" if wr['beat_bh'] else "no "
            print(f"{wr['window']:>7} {wr['train_days']:>7} {wr['test_days']:>7} "
                  f"{wr['rl_return_pct']:>8.1f}% {wr['bh_return_pct']:>8.1f}% "
                  f"{wr['spread_pct']:>+7.1f}pp {wr['num_trades']:>7} {beat:>6}")
        print("=" * 70)

        windows_beat = sum(1 for w in window_results if w['beat_bh'])
        print(f"Windows beating buy-and-hold: {windows_beat}/{len(window_results)}")
        print(f"Walk-forward combined return: {wf_metrics['total_return_pct']:+.1f}%")
        print(f"Walk-forward Sharpe: {wf_metrics['sharpe_ratio']:.2f}")
        print(f"Walk-forward Max DD: {wf_metrics['max_drawdown_pct']:.1f}%")
        print()

        # Key insight
        avg_spread = np.mean([w['spread_pct'] for w in window_results])
        if windows_beat >= len(window_results) * 0.5:
            print(f"CONCLUSION: RL agent maintains edge in {windows_beat}/{len(window_results)} out-of-sample")
            print(f"           windows. Average spread: {avg_spread:+.1f} pp over buy-and-hold.")
        else:
            print(f"CONCLUSION: RL agent only beat buy-and-hold in {windows_beat}/{len(window_results)}")
            print(f"           out-of-sample windows. Signal may be overfit or insufficient.")
            print(f"           Average spread: {avg_spread:+.1f} pp over buy-and-hold.")

    # JSON output
    result = {
        "cycle": "C535",
        "symbol": args.symbol,
        "period": f"{args.start} to {end_date}",
        "trading_days": n_days,
        "cost_model": cost_model,
        "round_trip_bps": round_trip_bps,
        "full_dataset": {
            "rl_with_costs": rl_metrics,
            "buy_and_hold": bh_metrics,
            "ma_crossover": ma_metrics,
            "num_trades": len(rl_trades),
            "total_cost": rl_total_cost,
            "q_table_size": len(agent.q_table),
        },
        "walk_forward": {
            "windows": args.windows,
            "window_results": window_results,
            "combined_metrics": wf_metrics,
            "windows_beating_bh": windows_beat,
        },
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        import os
        os.makedirs("reports", exist_ok=True)
        with open("reports/rl_backtest.jsonl", "a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"\nResults saved to reports/rl_backtest.jsonl")


if __name__ == "__main__":
    main()
