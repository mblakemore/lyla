#!/usr/bin/env python3
"""Regime-Aware Trading Agent — detect market regime, adapt strategy.

Addresses C535 insight: "the agent needs regime awareness to match simple technical strategies."
MA crossover (10/30) returned 174.3% — the strongest signal — because it implicitly detects
trend vs sideways. This agent makes that explicit.

Builds on C536 (DQN trading) + C535 (walk-forward, MA crossover baseline).

Key idea: Markets exhibit distinct regimes with different optimal strategies:
  - BULL (upward trend): Trend-follow — stay invested, ride momentum
  - BEAR (downward trend): Mean-revert — fade oversold bounces
  - SIDEWAYS (range-bound): Mean-revert — buy low, sell high of range

Regime detection uses two signals:
  1. Trend strength: (MA10 - MA30) / price — positive = bull, negative = bear
  2. Volatility regime: rolling 20d return std / annualized — high vs low

The agent compares 4 approaches:
  (a) Buy-and-hold
  (b) MA crossover (10/30) — the C535 baseline
  (c) DQN (from C536) — single policy, no regime awareness
  (d) Regime-aware — switches strategy based on detected regime

Usage:
    python3 bin/regime_aware_trading.py --symbol TSLA
    python3 bin/regime_aware_trading.py --symbol TSLA --walk-forward
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


# ── Regime Detection ─────────────────────────────────────────────────────

REGIME_BULL = 0
REGIME_BEAR = 1
REGIME_SIDEWAYS = 2

REGIME_NAMES = {REGIME_BULL: "BULL", REGIME_BEAR: "BEAR", REGIME_SIDEWAYS: "SIDEWAYS"}


def detect_regimes(prices, trend_window=20, vol_window=30, trend_threshold=0.01):
    """Detect market regimes using trend strength and volatility.

    Returns array of regime labels for each day.

    Regime logic:
      - Compute MA(trend_window) and MA(trend_window//2)
      - Trend = (short_MA - long_MA) / price
      - Vol = rolling std of daily returns over vol_window
      - BULL: trend > +threshold
      - BEAR: trend < -threshold
      - SIDEWAYS: |trend| <= threshold
    """
    n = len(prices)
    regimes = np.full(n, REGIME_SIDEWAYS, dtype=int)
    returns = np.diff(prices) / prices[:-1]

    for i in range(n):
        if i < trend_window:
            continue

        short_ma = np.mean(prices[i - trend_window // 2 : i])
        long_ma = np.mean(prices[i - trend_window : i])
        trend = (short_ma - long_ma) / prices[i]

        if trend > trend_threshold:
            regimes[i] = REGIME_BULL
        elif trend < -trend_threshold:
            regimes[i] = REGIME_BEAR

    return regimes


def regime_statistics(regimes):
    """Compute what fraction of time was spent in each regime."""
    total = len(regimes)
    stats = {}
    for label, name in REGIME_NAMES.items():
        count = int(np.sum(regimes == label))
        stats[name] = round(float(count / total * 100), 1)
    return stats


# ── Regime-Aware Strategy ────────────────────────────────────────────────

def regime_aware_equity(prices, regimes, cost_model=None,
                        trend_window=20, vol_window=30):
    """Regime-aware trading strategy.

    Strategy per regime:
      - BULL: Trend-follow. Stay invested when in bull regime.
             Use MA(5)/MA(10) crossover for entry timing within bull.
      - BEAR: Mean-revert. Buy when price drops below MA(20), sell at MA(15).
      - SIDEWAYS: Mean-revert. Buy at lower band, sell at upper band of recent range.

    Returns equity curve.
    """
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}

    spread = cost_model['spread_bps'] / 10000
    commission = cost_model['commission_bps'] / 10000

    n = len(prices)
    cash = 10000.0
    position = 0  # shares held
    equity = [10000.0]

    for i in range(1, n):
        regime = regimes[i]
        price = prices[i]

        if regime == REGIME_BULL:
            # Trend-follow in bull: stay invested, use short MA for pullback entries
            if i >= trend_window and position == 0:
                short_ma = np.mean(prices[max(0, i - 5):i])
                long_ma = np.mean(prices[max(0, i - trend_window // 2):i])
                if short_ma > long_ma and cash >= price:
                    eff = price * (1 + spread)
                    shares = int(cash / eff)
                    if shares > 0:
                        cost = shares * eff * commission
                        position = shares
                        cash -= shares * eff + cost
            # Hold through bull — no selling unless MA cross down
            elif position > 0 and i >= 10:
                short_ma = np.mean(prices[max(0, i - 3):i])
                long_ma = np.mean(prices[max(0, i - 10):i])
                if short_ma < long_ma:
                    eff = price * (1 - spread)
                    cost = position * eff * commission
                    cash += position * eff - cost
                    position = 0

        elif regime == REGIME_BEAR:
            # Mean-revert in bear: buy dips, sell quick bounces
            if i >= trend_window and position == 0:
                ma20 = np.mean(prices[i - trend_window:i])
                if price < ma20 * 0.995 and cash >= price:  # oversold threshold
                    eff = price * (1 + spread)
                    shares = int(cash / eff)
                    if shares > 0:
                        cost = shares * eff * commission
                        position = shares
                        cash -= shares * eff + cost
            # Sell on small bounce in bear
            elif position > 0 and i >= 5:
                ma_fast = np.mean(prices[i - 5:i])
                if price > ma_fast * 1.005:  # 0.5% bounce
                    eff = price * (1 - spread)
                    cost = position * eff * commission
                    cash += position * eff - cost
                    position = 0

        else:
            # SIDEWAYS: range mean-reversion
            if i >= vol_window:
                recent = prices[i - vol_window:i]
                band_low = np.min(recent)
                band_high = np.max(recent)
                mid = (band_low + band_high) / 2

                if position == 0 and price <= band_low * 1.01 and cash >= price:
                    eff = price * (1 + spread)
                    shares = int(cash / eff)
                    if shares > 0:
                        cost = shares * eff * commission
                        position = shares
                        cash -= shares * eff + cost
                elif position > 0 and price >= band_high * 0.99:
                    eff = price * (1 - spread)
                    cost = position * eff * commission
                    cash += position * eff - cost
                    position = 0
            elif i < vol_window:
                # Not enough data for range, stay flat
                pass

        equity.append(cash + position * price)

    # Liquidate
    if position > 0:
        cash += position * prices[-1] * (1 - spread)

    return equity


# ── Buy-and-Hold & MA Crossover (from C536) ──────────────────────────────

def buy_and_hold_equity(prices):
    shares = 10000.0 / prices[0]
    return [shares * p for p in prices]


def ma_crossover_equity(prices, short=10, long=30, cost_model=None):
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


# ── Metrics ──────────────────────────────────────────────────────────────

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


# ── Regime-Aware DQN (from C536, adapted) ────────────────────────────────

def relu(x):
    return np.maximum(0, x)

def relu_deriv(x):
    return (x > 0).astype(float)


class MLP:
    """2-hidden-layer MLP for Q-value estimation."""
    def __init__(self, input_dim, hidden_dim, output_dim, rng):
        scale1 = math.sqrt(2.0 / input_dim)
        self.W1 = rng.standard_normal((input_dim, hidden_dim)) * scale1
        self.b1 = np.zeros(hidden_dim)
        scale2 = math.sqrt(2.0 / hidden_dim)
        self.W2 = rng.standard_normal((hidden_dim, hidden_dim)) * scale2
        self.b2 = np.zeros(hidden_dim)
        scale3 = math.sqrt(2.0 / hidden_dim)
        self.W3 = rng.standard_normal((hidden_dim, output_dim)) * scale3
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
        dW1 = self._x.T @ dz1 / bs
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
        net.W1, net.b1 = self.W1.copy(), self.b1.copy()
        net.W2, net.b2 = self.W2.copy(), self.b2.copy()
        net.W3, net.b3 = self.W3.copy(), self.b3.copy()
        return net


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


def compute_features(prices):
    """Compute continuous features: return_1d, return_5d, volatility_10d, RSI_14d."""
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


class RegimeAwareDQN:
    """DQN that conditions on market regime.

    State: [return_1d, return_5d, volatility, RSI, regime_one_hot(3), position_one_hot(2)]
           = 4 + 3 + 2 = 9 dimensions

    By including regime in the state, the network learns different Q-values
    for the same price features in different regimes.
    """

    def __init__(self, hidden_dim=64, lr=0.001, gamma=0.95,
                 epsilon=1.0, epsilon_min=0.05, epsilon_decay=0.99,
                 buffer_size=5000, batch_size=32, trade_penalty=0.005,
                 target_update_freq=50, rng=None):
        self.rng = rng or np.random.default_rng()
        self.gamma = gamma
        self.trade_penalty = trade_penalty
        self.lr = lr

        # 4 features + 3 regime one-hot + 2 position one-hot = 9
        self.input_dim = 9
        self.action_dim = 3  # HOLD, BUY, SELL

        self.online_net = MLP(self.input_dim, hidden_dim, self.action_dim, self.rng)
        self.target_net = self.online_net.copy()
        self.buffer = ReplayBuffer(buffer_size)
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.step_count = 0

        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay

    def _make_state(self, features, regime, in_position):
        regime_one_hot = np.zeros(3)
        regime_one_hot[regime] = 1.0
        position_vec = np.array([1.0, 0.0] if in_position else [0.0, 1.0])
        return np.concatenate([features, regime_one_hot, position_vec])

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


def run_episode_regime_aware(prices, features, regimes, agent, trade_penalty=0.0, cost_model=None):
    """Run one episode of regime-aware DQN trading simulation."""
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}

    spread = cost_model['spread_bps'] / 10000
    commission = cost_model['commission_bps'] / 10000

    initial_capital = 10000.0
    cash = initial_capital
    position = 0
    equity_curve = [initial_capital]
    num_trades = 0
    last_action = 0

    for t in range(1, len(prices)):
        feat = features[t - 1]
        if feat is None:
            equity_curve.append(cash + position * prices[t])
            continue

        regime = regimes[t - 1] if t - 1 < len(regimes) else REGIME_SIDEWAYS
        in_pos = position > 0
        state = agent._make_state(feat, regime, in_pos)
        action = agent.select_action(state)

        price = prices[t]
        prev_price = prices[t - 1]
        ret = (price - prev_price) / prev_price

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

        reward = ret
        if action != last_action and action != 0:
            reward -= trade_penalty

        next_feat = features[t]
        if next_feat is not None:
            next_regime = regimes[t] if t < len(regimes) else REGIME_SIDEWAYS
            next_state = agent._make_state(next_feat, next_regime, position > 0)
            agent.store(state, action, reward, next_state, False)
            agent.learn()

        last_action = action
        equity_curve.append(cash + position * prices[t])

    if position > 0:
        cash += position * prices[-1] * (1 - spread)

    total_pnl = (equity_curve[-1] - initial_capital) / initial_capital * 100
    return equity_curve, num_trades, total_pnl


# ── Walk-Forward Validation ──────────────────────────────────────────────

def walk_forward_regime_aware(prices, features, regimes, n_windows, train_ratio=0.7,
                               episodes_per_window=50, trade_penalty=0.005, cost_model=None):
    """Walk-forward validation for regime-aware DQN."""
    n = len(prices)
    window_size = n // n_windows
    window_results = []

    for w in range(n_windows):
        start = w * window_size
        end = start + window_size if w < n_windows - 1 else n
        train_end = start + int(window_size * train_ratio)

        train_prices = prices[start:train_end]
        train_features = features[start:train_end]
        train_regimes = regimes[start:train_end]
        test_prices = prices[train_end:end]
        test_features = features[train_end:end]
        test_regimes = regimes[train_end:end]

        if len(train_prices) < 20 or len(test_prices) < 5:
            continue

        rng = np.random.default_rng(42 + w)
        agent = RegimeAwareDQN(
            hidden_dim=64, lr=0.001, gamma=0.95,
            epsilon=1.0, epsilon_decay=0.98, epsilon_min=0.05,
            buffer_size=5000, batch_size=32,
            trade_penalty=trade_penalty,
            target_update_freq=30,
            rng=rng
        )

        for ep in range(episodes_per_window):
            _, _, _ = run_episode_regime_aware(
                train_prices, train_features, train_regimes,
                agent, trade_penalty, cost_model
            )
            agent.decay_epsilon()

        agent.epsilon = 0
        test_equity, test_trades, test_pnl = run_episode_regime_aware(
            test_prices, test_features, test_regimes, agent, 0, cost_model
        )

        if len(test_prices) > 1:
            bh_return = (test_prices[-1] - test_prices[0]) / test_prices[0] * 100
        else:
            bh_return = 0

        window_results.append({
            "window": w + 1,
            "train_days": len(train_prices),
            "test_days": len(test_prices),
            "ra_dqn_return_pct": round(test_pnl, 2),
            "bh_return_pct": round(bh_return, 2),
            "spread_pct": round(test_pnl - bh_return, 2),
            "num_trades": test_trades,
            "beat_bh": test_pnl > bh_return,
        })

    return window_results


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Regime-Aware Trading Agent")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--trade-penalty", type=float, default=0.005)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--windows", type=int, default=3)
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
    regimes = detect_regimes(prices)
    n_days = len(prices)

    cost_model = {'spread_bps': 10, 'commission_bps': 2}
    results = {"cycle": "C537", "symbol": args.symbol,
               "period": f"{args.start} to {end_date}"}

    regime_stats = regime_statistics(regimes)

    if not args.json:
        print(f"Regime-Aware Trading Agent — {args.symbol}")
        print(f"Period: {args.start} to {end_date} ({n_days} trading days)")
        print(f"Regime distribution: {regime_stats}")
        print()

    # ── Rule-based regime-aware strategy ───────────────────────────────
    ra_rule_equity = regime_aware_equity(prices, regimes, cost_model)
    ra_rule_metrics = compute_metrics(ra_rule_equity, "Regime-Aware Rule")

    # ── Regime-aware DQN ──────────────────────────────────────────────
    rng = np.random.default_rng(42)
    ra_dqn = RegimeAwareDQN(
        hidden_dim=64, lr=0.001, gamma=0.95,
        epsilon=1.0, epsilon_decay=0.98, epsilon_min=0.05,
        buffer_size=5000, batch_size=32,
        trade_penalty=args.trade_penalty,
        target_update_freq=30,
        rng=rng
    )

    episode_returns = []
    for ep in range(args.episodes):
        eq, trades, pnl = run_episode_regime_aware(
            prices, features, regimes, ra_dqn, args.trade_penalty, cost_model
        )
        episode_returns.append(pnl)
        ra_dqn.decay_epsilon()

    ra_dqn.epsilon = 0
    ra_dqn_equity, ra_dqn_trades, ra_dqn_pnl = run_episode_regime_aware(
        prices, features, regimes, ra_dqn, 0, cost_model
    )
    ra_dqn_metrics = compute_metrics(ra_dqn_equity, "Regime-Aware DQN")

    # ── Benchmarks ─────────────────────────────────────────────────────
    bh_equity = buy_and_hold_equity(prices)
    bh_metrics = compute_metrics(bh_equity, "Buy & Hold")
    ma_equity = ma_crossover_equity(prices, cost_model=cost_model)
    ma_metrics = compute_metrics(ma_equity, "MA Crossover")

    # ── Walk-Forward ──────────────────────────────────────────────────
    wf_results = None
    if args.walk_forward:
        wf_results = walk_forward_regime_aware(
            prices, features, regimes, args.windows, train_ratio=0.7,
            episodes_per_window=30, trade_penalty=args.trade_penalty,
            cost_model=cost_model
        )

    # ── Report ─────────────────────────────────────────────────────────
    if not args.json:
        print("=" * 75)
        print("REGIME-AWARE TRADING — With Transaction Costs")
        print("=" * 75)
        print(f"{'Strategy':<20} {'Final Equity':>14} {'Return':>10} {'Sharpe':>8} {'Max DD':>8}")
        print("-" * 75)
        for m in [bh_metrics, ma_metrics, ra_rule_metrics, ra_dqn_metrics]:
            print(f"{m['label']:<20} ${m['final_equity']:>12,.2f} {m['total_return_pct']:>9.1f}% "
                  f"{m['sharpe_ratio']:>7.2f} {m['max_drawdown_pct']:>7.1f}%")
        print("=" * 75)
        print(f"Regime-Aware DQN trades: {ra_dqn_trades}")
        print()

        # Per-regime analysis
        print("--- Regime Analysis ---")
        for label, name in REGIME_NAMES.items():
            regime_mask = regimes[1:] == label  # skip first, aligns with returns
            regime_days = int(np.sum(regime_mask))
            if regime_days > 0:
                daily_returns = np.diff(prices) / prices[:-1]
                regime_ret = daily_returns[regime_mask]
                avg_ret = float(np.mean(regime_ret) * 100) if len(regime_ret) > 0 else 0
                print(f"  {name}: {regime_days} days ({regime_stats[name]}%), "
                      f"avg daily return: {avg_ret:+.2f}%")
        print()

        # Learning curve
        window = 10
        avg_final = sum(episode_returns[-window:]) / window
        print(f"Learning: avg return over last {window} episodes: {avg_final:+.1f}%")
        print(f"Final epsilon: {ra_dqn.epsilon:.4f}")
        print(f"Buffer size: {len(ra_dqn.buffer)}")
        print()

        if wf_results:
            print("=" * 75)
            print("WALK-FORWARD VALIDATION — Regime-Aware DQN Out-of-Sample")
            print("=" * 75)
            print(f"{'Window':>7} {'Train':>7} {'Test':>7} {'RA-DQN Ret%':>11} {'B&H Ret%':>9} {'Spread':>8} {'Trades':>7} {'Beat?':>6}")
            print("-" * 75)
            for wr in wf_results:
                beat = "YES" if wr['beat_bh'] else "no "
                print(f"{wr['window']:>7} {wr['train_days']:>7} {wr['test_days']:>7} "
                      f"{wr['ra_dqn_return_pct']:>10.1f}% {wr['bh_return_pct']:>8.1f}% "
                      f"{wr['spread_pct']:>+7.1f}pp {wr['num_trades']:>7} {beat:>6}")
            print("=" * 75)
            windows_beat = sum(1 for w in wf_results if w['beat_bh'])
            print(f"Windows beating buy-and-hold: {windows_beat}/{len(wf_results)}")
            print()

    # ── JSON Output ────────────────────────────────────────────────────
    results["regime_distribution"] = regime_stats
    results["regime_aware_rule"] = ra_rule_metrics
    results["regime_aware_dqn"] = {
        **ra_dqn_metrics,
        "num_trades": ra_dqn_trades,
        "episode_returns_avg_final10": round(sum(episode_returns[-10:]) / 10, 2),
        "final_epsilon": round(ra_dqn.epsilon, 4),
        "buffer_size": len(ra_dqn.buffer),
        "trade_penalty": args.trade_penalty,
    }
    results["buy_and_hold"] = bh_metrics
    results["ma_crossover"] = ma_metrics
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
        with open("reports/regime_aware_trading.jsonl", "a") as f:
            f.write(json.dumps(results) + "\n")
        print(f"Results saved to reports/regime_aware_trading.jsonl")


if __name__ == "__main__":
    main()
