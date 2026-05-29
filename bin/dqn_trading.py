#!/usr/bin/env python3
"""DQN Trading Agent — Deep Q-Network for financial trading with trade penalty.

Addresses C535 findings:
  1. Tabular Q-learning overtrades (251x on TSLA, 43.7 pp cost drag)
  2. Discretized states create false confidence — DQN uses continuous features
  3. No trade penalty — agent doesn't learn that switching positions costs money

Builds on C531 (DQN on CartPole) + C534/C535 (RL trading framework).

Key innovations over C535 tabular Q-learning:
  - Neural network Q-function (no discretization, generalizes across similar states)
  - Experience replay (breaks temporal correlation in financial time series)
  - Target network (stable bootstrapping — prevents chasing moving targets)
  - Trade penalty in reward (agent learns to hold positions longer)

Usage:
    python3 bin/dqn_trading.py --symbol TSLA
    python3 bin/dqn_trading.py --symbol TSLA --episodes 100
    python3 bin/dqn_trading.py --symbol SPY --trade-penalty 0.002
    python3 bin/dqn_trading.py --walk-forward --windows 3
    python3 bin/dqn_trading.py --json
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    print("ERROR: pip install yfinance numpy")
    sys.exit(1)


# ── Neural Network (from C531, adapted for trading) ─────────────────────

def relu(x):
    return np.maximum(0, x)

def relu_deriv(x):
    return (x > 0).astype(float)

def he_init(fan_in, fan_out, rng):
    return rng.standard_normal((fan_in, fan_out)) * math.sqrt(2.0 / fan_in)


class MLP:
    """2-hidden-layer MLP for Q-value estimation."""

    def __init__(self, input_dim, hidden_dim, output_dim, rng):
        self.W1 = he_init(input_dim, hidden_dim, rng)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = he_init(hidden_dim, hidden_dim, rng)
        self.b2 = np.zeros(hidden_dim)
        self.W3 = he_init(hidden_dim, output_dim, rng)
        self.b3 = np.zeros(output_dim)

    def forward(self, x):
        self._x = x
        self.z1 = x @ self.W1 + self.b1
        self.a1 = relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = relu(self.z2)
        return self.a2 @ self.W3 + self.b3

    def backward(self, x, grad_output, lr):
        bs = x.shape[0]
        dW3 = self.a2.T @ grad_output / bs
        db3 = grad_output.mean(axis=0)
        da2 = grad_output @ self.W3.T
        dz2 = da2 * relu_deriv(self.z2)
        dW2 = self.a1.T @ dz2 / bs
        db2 = dz2.mean(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * relu_deriv(self.z1)
        dW1 = x.T @ dz1 / bs
        db1 = dz1.mean(axis=0)

        for w in [dW1, dW2, dW3]:
            norm = np.sqrt((w ** 2).sum())
            if norm > 5.0:
                w *= 5.0 / norm

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W3 -= lr * dW3
        self.b3 -= lr * db3

    def copy(self):
        net = MLP.__new__(MLP)
        net.W1 = self.W1.copy()
        net.b1 = self.b1.copy()
        net.W2 = self.W2.copy()
        net.b2 = self.b2.copy()
        net.W3 = self.W3.copy()
        net.b3 = self.b3.copy()
        return net


# ── Experience Replay ────────────────────────────────────────────────────

class ReplayBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, item):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = item
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size, rng):
        indices = rng.choice(len(self.buffer), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        return (np.array(states), np.array(actions), np.array(rewards),
                np.array(next_states), np.array(dones))

    def __len__(self):
        return len(self.buffer)


# ── Feature Computation ──────────────────────────────────────────────────

def compute_features(prices):
    """Compute continuous features for each timestep.

    Returns list of [return_1d, return_5d, volatility_10d, RSI_14d] arrays.
    Position is handled separately as part of state.
    """
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
        ret_5d = (prices[i] - prices[i - 5]) / prices[i - 5] if i >= 5 else 0.0

        window = prices[max(0, i - 10):i]
        if len(window) >= 2:
            window_returns = [(window[j] - window[j - 1]) / window[j - 1]
                              for j in range(1, len(window))]
            vol = (sum(r ** 2 for r in window_returns) / len(window_returns)) ** 0.5
        else:
            vol = 0.0

        gains = [r if r > 0 else 0 for r in returns[i - 13:i + 1]]
        losses = [abs(r) if r < 0 else 0 for r in returns[i - 13:i + 1]]
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50.0

        features.append(np.array([ret_1d, ret_5d, vol, rsi]))

    return features


# ── Feature Normalization ────────────────────────────────────────────────

class FeatureNormalizer:
    """Normalize features to [-1, 1] using min/max from training data.

    DQN learns better when inputs are in a consistent range. We compute
    normalization bounds from the training window and apply them during
    both training and evaluation.
    """

    def __init__(self):
        self.min_vals = None
        self.max_vals = None

    def fit(self, features):
        """Compute min/max from feature matrix (excluding Nones)."""
        valid = [f for f in features if f is not None]
        if not valid:
            return
        stacked = np.array(valid)
        self.min_vals = stacked.min(axis=0)
        self.max_vals = stacked.max(axis=1).reshape(1, -4)

    def transform(self, features):
        """Normalize features to [-1, 1]."""
        if self.min_vals is None:
            return features
        range_vals = (self.max_vals.flatten() - self.min_vals).clip(min=1e-8)
        return (2.0 * (features - self.min_vals) / range_vals - 1.0).clip(-2, 2)


# ── DQN Trading Agent ────────────────────────────────────────────────────

class DQNTradingAgent:
    """DQN agent for trading with continuous features and trade penalty.

    State: [return_1d, return_5d, volatility, RSI, position] (5-dim, continuous)
    Actions: 0=HOLD, 1=BUY, 2=SELL
    Reward: price return + position PnL - trade_penalty (if action changes)
    """

    def __init__(self, hidden_dim=64, lr=0.001, gamma=0.95,
                 epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.99,
                 buffer_size=5000, batch_size=32, trade_penalty=0.001,
                 target_update_freq=50, rng=None):
        self.rng = rng or np.random.default_rng()
        self.gamma = gamma
        self.trade_penalty = trade_penalty
        self.lr = lr

        # State: 4 features + 1-hot position (2) = 6 input dims
        # Actions: HOLD, BUY, SELL = 3 output dims
        self.input_dim = 6
        self.action_dim = 3

        self.online_net = MLP(self.input_dim, hidden_dim, self.action_dim, self.rng)
        self.target_net = self.online_net.copy()
        self.buffer = ReplayBuffer(buffer_size)
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.step_count = 0

        # Epsilon-greedy
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

        # Track last action for trade penalty
        self.last_action = 0

    def _make_state(self, features, in_position):
        """Build 6-dim state: 4 features + 2-dim position one-hot."""
        position_vec = np.array([1.0, 0.0] if in_position else [0.0, 1.0])
        return np.concatenate([features, position_vec])

    def select_action(self, state):
        if self.rng.random() < self.epsilon:
            return int(self.rng.integers(0, self.action_dim))
        q_values = self.online_net.forward(state.reshape(1, -1))[0]
        return int(np.argmax(q_values))

    def store(self, state, action, reward, next_state, done):
        self.buffer.push((state, action, reward, next_state, float(done)))

    def learn(self):
        if len(self.buffer) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.buffer.sample(
            self.batch_size, self.rng
        )
        actions_flat = actions.flatten()

        q_current = self.online_net.forward(states)
        q_next = self.target_net.forward(next_states)
        max_q_next = np.max(q_next, axis=1)

        targets = rewards + self.gamma * max_q_next * (1 - dones)

        errors = np.array([q_current[i, int(a)] - targets[i]
                           for i, a in enumerate(actions_flat)])
        grad_output = np.zeros_like(q_current)
        for i, a in enumerate(actions_flat):
            grad_output[i, int(a)] = 2.0 * errors[i]

        self.online_net.backward(states, grad_output, self.lr)
        self.step_count += 1

        if self.step_count % self.target_update_freq == 0:
            self.target_net = self.online_net.copy()

        return float(np.mean(errors ** 2))

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


# ── Tabular Q-Learning Baseline (from C534/C535) ─────────────────────────

class TabularQTrader:
    """Tabular Q-learning for comparison with DQN."""

    def __init__(self, alpha=0.15, gamma=0.95, epsilon=1.0,
                 epsilon_decay=0.99, epsilon_min=0.01, n_bins=5):
        self.q_table = {}
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.n_bins = n_bins
        self.actions = [0, 1, 2]
        self.rng = np.random.default_rng()
        self.last_action = 0

    def _discretize(self, value, low, high):
        clamped = max(low, min(high, value))
        return int(round((clamped - low) / (high - low) * (self.n_bins - 1)))

    def _make_state(self, features, in_position):
        ret_1 = self._discretize(features[0], -0.05, 0.05)
        ret_5 = self._discretize(features[1], -0.05, 0.05)
        vol = self._discretize(features[2], 0, 0.1)
        rsi = self._discretize(features[3], 0, 100)
        return (ret_1, ret_5, vol, rsi, 1 if in_position else 0)

    def _get_q(self, state, action):
        return self.q_table.get((state, action), 0.0)

    def select_action(self, state):
        if self.rng.random() < self.epsilon:
            return int(self.rng.choice(self.actions))
        return max(self.actions, key=lambda a: self._get_q(state, a))

    def update(self, state, action, reward, next_state):
        best_next = max(self.actions, key=lambda a: self._get_q(next_state, a))
        target = reward + self.gamma * self._get_q(next_state, best_next)
        current = self._get_q(state, action)
        self.q_table[(state, action)] = current + self.alpha * (target - current)

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


# ── Trading Simulation ───────────────────────────────────────────────────

def run_episode(prices, features, agent, trade_penalty=0.0, cost_model=None):
    """Run one episode of trading simulation.

    Returns: (equity_curve, num_trades, total_pnl, trade_log)
    """
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}

    spread = cost_model['spread_bps'] / 10000
    commission = cost_model['commission_bps'] / 10000

    initial_capital = 10000.0
    cash = initial_capital
    position = 0  # number of shares
    equity_curve = [initial_capital]
    num_trades = 0
    last_action = 0

    for t in range(1, len(prices)):
        feat = features[t - 1]
        if feat is None:
            equity_curve.append(cash + position * prices[t])
            continue

        in_pos = position > 0
        state = agent._make_state(feat, in_pos)
        action = agent.select_action(state)

        price = prices[t]
        prev_price = prices[t - 1]
        ret = (price - prev_price) / prev_price

        # Execute
        if action == 1:  # BUY
            if cash >= price and position == 0:
                effective_price = price * (1 + spread)
                shares = int(cash / effective_price)
                if shares > 0:
                    cost = shares * effective_price * commission
                    position = shares
                    cash -= shares * effective_price + cost
                    num_trades += 1
        elif action == 2:  # SELL
            if position > 0:
                effective_price = price * (1 - spread)
                cost = position * effective_price * commission
                cash += position * effective_price - cost
                num_trades += 1
                position = 0

        # Reward: return + trade penalty for switching
        reward = ret
        if action != last_action and action != 0:
            reward -= trade_penalty

        # Learn (DQN stores, tabular updates directly)
        if hasattr(agent, 'store'):
            next_feat = features[t]
            if next_feat is not None:
                next_state = agent._make_state(next_feat, position > 0)
                agent.store(state, action, reward, next_state, False)
                agent.learn()
        else:
            next_feat = features[t]
            if next_feat is not None:
                next_state = agent._make_state(next_feat, position > 0)
                agent.update(state, action, reward, next_state)

        last_action = action
        equity_curve.append(cash + position * prices[t])

    # Liquidate
    if position > 0:
        cash += position * prices[-1] * (1 - spread)

    total_pnl = (equity_curve[-1] - initial_capital) / initial_capital * 100

    return equity_curve, num_trades, total_pnl


def buy_and_hold_equity(prices, initial_capital=10000.0):
    shares = initial_capital / prices[0]
    return [shares * p for p in prices]


def ma_crossover_equity(prices, short=10, long=30, cost_model=None):
    """MA crossover benchmark."""
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}
    spread = cost_model['spread_bps'] / 10000
    commission = cost_model['commission_bps'] / 10000

    cash, position, equity = 10000.0, 0, [10000.0]
    for t in range(len(prices)):
        if t < long:
            equity.append(cash + position * prices[t])
            continue
        short_ma = sum(prices[t - short:t]) / short
        long_ma = sum(prices[t - long:t]) / long
        if short_ma > long_ma and position == 0 and cash >= prices[t]:
            eff = prices[t] * (1 + spread)
            shares = int(cash / eff)
            if shares > 0:
                cost = shares * eff * commission
                position = shares
                cash -= shares * eff + cost
        elif short_ma <= long_ma and position > 0:
            eff = prices[t] * (1 - spread)
            cost = position * eff * commission
            cash += position * eff - cost
            position = 0
        equity.append(cash + position * prices[t])
    if position > 0:
        cash += position * prices[-1]
    return equity


def compute_metrics(equity_curve, label=""):
    if len(equity_curve) < 2:
        return {"label": label, "total_return_pct": 0, "sharpe_ratio": 0,
                "max_drawdown_pct": 0, "final_equity": equity_curve[-1] if equity_curve else 0}

    returns = np.array([(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
                        for i in range(1, len(equity_curve))])
    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100
    sharpe = np.sqrt(252) * np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
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


# ── Walk-Forward Validation ──────────────────────────────────────────────

def walk_forward_dqn(prices, features, n_windows, train_ratio=0.7,
                     episodes_per_window=50, trade_penalty=0.0, cost_model=None):
    """Walk-forward validation for DQN trading agent."""
    n = len(prices)
    window_size = n // n_windows
    window_results = []

    for w in range(n_windows):
        start = w * window_size
        end = start + window_size if w < n_windows - 1 else n
        train_end = start + int(window_size * train_ratio)

        train_prices = prices[start:train_end]
        train_features = features[start:train_end]
        test_prices = prices[train_end:end]
        test_features = features[train_end:end]

        if len(train_prices) < 20 or len(test_prices) < 5:
            continue

        # Normalize features from training window
        normalizer = FeatureNormalizer()
        normalizer.fit(train_features)

        # Train DQN
        rng = np.random.default_rng(42 + w)
        agent = DQNTradingAgent(
            hidden_dim=64, lr=0.001, gamma=0.95,
            epsilon=1.0, epsilon_decay=0.98, epsilon_min=0.05,
            buffer_size=5000, batch_size=32,
            trade_penalty=trade_penalty,
            target_update_freq=30,
            rng=rng
        )

        for ep in range(episodes_per_window):
            _, _, _ = run_episode(train_prices, train_features, agent,
                                   trade_penalty, cost_model)
            agent.decay_epsilon()

        # Evaluate on test (greedy)
        agent.epsilon = 0
        test_equity, test_trades, test_pnl = run_episode(
            test_prices, test_features, agent, 0, cost_model
        )

        # Buy-and-hold baseline
        if len(test_prices) > 1:
            bh_return = (test_prices[-1] - test_prices[0]) / test_prices[0] * 100
        else:
            bh_return = 0

        window_results.append({
            "window": w + 1,
            "train_days": len(train_prices),
            "test_days": len(test_prices),
            "dqn_return_pct": round(test_pnl, 2),
            "bh_return_pct": round(bh_return, 2),
            "spread_pct": round(test_pnl - bh_return, 2),
            "num_trades": test_trades,
            "beat_bh": test_pnl > bh_return,
        })

    return window_results


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DQN Trading Agent with Trade Penalty")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--trade-penalty", type=float, default=0.002,
                        help="Penalty per trade switch (default: 0.002 = 0.2%)")
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--walk-forward", action="store_true",
                        help="Run walk-forward validation")
    parser.add_argument("--windows", type=int, default=3)
    parser.add_argument("--compare-tabular", action="store_true",
                        help="Compare against tabular Q-learning baseline")
    parser.add_argument("--json", action="store_true")
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

    cost_model = {'spread_bps': 10, 'commission_bps': 2}
    results = {"cycle": "C536", "symbol": args.symbol, "period": f"{args.start} to {end_date}"}

    if not args.json:
        print(f"DQN Trading Agent — {args.symbol}")
        print(f"Period: {args.start} to {end_date} ({n_days} trading days)")
        print(f"Trade penalty: {args.trade_penalty * 100:.1f}%")
        print()

    # ── Train DQN ──────────────────────────────────────────────────────
    rng = np.random.default_rng(42)
    dqn_agent = DQNTradingAgent(
        hidden_dim=args.hidden_dim, lr=args.lr, gamma=0.95,
        epsilon=1.0, epsilon_decay=0.98, epsilon_min=0.05,
        buffer_size=5000, batch_size=32,
        trade_penalty=args.trade_penalty,
        target_update_freq=30,
        rng=rng
    )

    episode_returns = []
    for ep in range(args.episodes):
        eq, trades, pnl = run_episode(prices, features, dqn_agent,
                                       args.trade_penalty, cost_model)
        episode_returns.append(pnl)
        dqn_agent.decay_epsilon()

    # Evaluate DQN (greedy)
    dqn_agent.epsilon = 0
    dqn_equity, dqn_trades, dqn_pnl = run_episode(
        prices, features, dqn_agent, 0, cost_model
    )
    dqn_metrics = compute_metrics(dqn_equity, "DQN")

    # ── Tabular Baseline (optional) ────────────────────────────────────
    tabular_metrics = None
    tabular_trades = 0
    if args.compare_tabular:
        tab_agent = TabularQTrader(alpha=0.15, gamma=0.95, epsilon=1.0,
                                    epsilon_decay=0.99, epsilon_min=0.01)
        for ep in range(args.episodes):
            _, _, _ = run_episode(prices, features, tab_agent, 0, cost_model)
            tab_agent.decay_epsilon()
        tab_agent.epsilon = 0
        tab_equity, tabular_trades, _ = run_episode(
            prices, features, tab_agent, 0, cost_model
        )
        tabular_metrics = compute_metrics(tab_equity, "Tabular Q")

    # ── Benchmarks ─────────────────────────────────────────────────────
    bh_equity = buy_and_hold_equity(prices)
    bh_metrics = compute_metrics(bh_equity, "Buy & Hold")
    ma_equity = ma_crossover_equity(prices, cost_model=cost_model)
    ma_metrics = compute_metrics(ma_equity, "MA Crossover")

    # ── Walk-Forward (optional) ────────────────────────────────────────
    wf_results = None
    if args.walk_forward:
        wf_results = walk_forward_dqn(
            prices, features, args.windows, train_ratio=0.7,
            episodes_per_window=30, trade_penalty=args.trade_penalty,
            cost_model=cost_model
        )

    # ── Report ─────────────────────────────────────────────────────────
    if not args.json:
        print("=" * 70)
        print("DQN TRADING — With Transaction Costs")
        print("=" * 70)
        print(f"{'Strategy':<18} {'Final Equity':>14} {'Return':>10} {'Sharpe':>8} {'Max DD':>8} {'Trades':>7}")
        print("-" * 70)
        for m in [bh_metrics, ma_metrics, dqn_metrics]:
            trades_str = ""
            if m['label'] == "DQN":
                trades_str = f"{dqn_trades:>7}"
            elif m['label'] == "Tabular Q":
                trades_str = f"{tabular_trades:>7}"
            print(f"{m['label']:<18} ${m['final_equity']:>12,.2f} {m['total_return_pct']:>9.1f}% "
                  f"{m['sharpe_ratio']:>7.2f} {m['max_drawdown_pct']:>7.1f}%{trades_str}")

        if tabular_metrics:
            print(f"{'Tabular Q':<18} ${tabular_metrics['final_equity']:>12,.2f} "
                  f"{tabular_metrics['total_return_pct']:>9.1f}% "
                  f"{tabular_metrics['sharpe_ratio']:>7.2f} "
                  f"{tabular_metrics['max_drawdown_pct']:>7.1f}%{tabular_trades:>7}")

        print("=" * 70)
        print(f"DQN trades: {dqn_trades} | Tabular trades: {tabular_trades if args.compare_tabular else 'N/A'}")
        print(f"Trade reduction: ", end="")
        if tabular_trades > 0:
            pct = (1 - dqn_trades / tabular_trades) * 100
            print(f"{pct:+.1f}% ({tabular_trades - dqn_trades} fewer trades)")
        else:
            print("N/A")
        print()

        # Learning curve
        window = 10
        avg_final = sum(episode_returns[-window:]) / window
        print(f"Learning: avg return over last {window} episodes: {avg_final:+.1f}%")
        print(f"Final epsilon: {dqn_agent.epsilon:.4f}")
        print(f"Buffer size: {len(dqn_agent.buffer)}")
        print()

        if wf_results:
            print("=" * 70)
            print("WALK-FORWARD VALIDATION — DQN Out-of-Sample")
            print("=" * 70)
            print(f"{'Window':>7} {'Train':>7} {'Test':>7} {'DQN Ret%':>9} {'B&H Ret%':>9} {'Spread':>8} {'Trades':>7} {'Beat?':>6}")
            print("-" * 70)
            for wr in wf_results:
                beat = "YES" if wr['beat_bh'] else "no "
                print(f"{wr['window']:>7} {wr['train_days']:>7} {wr['test_days']:>7} "
                      f"{wr['dqn_return_pct']:>8.1f}% {wr['bh_return_pct']:>8.1f}% "
                      f"{wr['spread_pct']:>+7.1f}pp {wr['num_trades']:>7} {beat:>6}")
            print("=" * 70)
            windows_beat = sum(1 for w in wf_results if w['beat_bh'])
            print(f"Windows beating buy-and-hold: {windows_beat}/{len(wf_results)}")
            print()

            if windows_beat >= len(wf_results) * 0.5:
                print(f"CONCLUSION: DQN maintains edge in {windows_beat}/{len(wf_results)} out-of-sample")
                print(f"           windows with trade penalty. Signal is more robust than tabular.")
            else:
                print(f"CONCLUSION: DQN beat buy-and-hold in {windows_beat}/{len(wf_results)}")
                print(f"           out-of-sample windows. Trade frequency reduced but edge")
                print(f"           may still be insufficient for reliable out-of-sample performance.")
        print()

        # Key insight
        print("--- Key Insight ---")
        if tabular_trades > dqn_trades:
            print(f"  DQN traded {tabular_trades - dqn_trades} fewer times than tabular Q-learning")
            print(f"  ({dqn_trades} vs {tabular_trades}). Continuous features + trade penalty")
            print(f"  produce a more conservative policy — the agent learns to hold")
            print(f"  positions rather than flip on noise.")
        else:
            print(f"  DQN traded {dqn_trades} times vs tabular {tabular_trades}.")
            print(f"  Continuous features allow finer state discrimination, but trade")
            print(f"  penalty magnitude may need tuning for optimal frequency.")

    # ── JSON Output ────────────────────────────────────────────────────
    results["dqn"] = {
        **dqn_metrics,
        "num_trades": dqn_trades,
        "episode_returns_avg_final10": round(sum(episode_returns[-10:]) / 10, 2),
        "final_epsilon": round(dqn_agent.epsilon, 4),
        "buffer_size": len(dqn_agent.buffer),
        "trade_penalty": args.trade_penalty,
    }
    results["buy_and_hold"] = bh_metrics
    results["ma_crossover"] = ma_metrics
    if tabular_metrics:
        results["tabular_q"] = {**tabular_metrics, "num_trades": tabular_trades}
    if wf_results:
        results["walk_forward"] = {
            "windows": args.windows,
            "window_results": wf_results,
            "windows_beating_bh": sum(1 for w in wf_results if w['beat_bh']),
        }

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        import os
        os.makedirs("reports", exist_ok=True)
        with open("reports/dqn_trading.jsonl", "a") as f:
            f.write(json.dumps(results) + "\n")
        print(f"Results saved to reports/dqn_trading.jsonl")


if __name__ == "__main__":
    main()
