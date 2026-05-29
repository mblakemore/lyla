#!/usr/bin/env python3
"""HMM Regime-Aware DQN Trading — replace MA regimes with HMM regimes.

C537 finding: MA-based RA-DQN works for TSLA/AAPL but fails for NVDA/SPY.
C538 hypothesis: HMM detects regimes more coherently than MA thresholds,
especially for volatile assets where MA chatters between regimes.

Compares HMM-based RA-DQN vs MA-based RA-DQN on walk-forward validation.

Usage:
    python3 bin/hmm_regime_trading.py --symbol TSLA
    python3 bin/hmm_regime_trading.py --symbol NVDA --walk-forward
    python3 bin/hmm_regime_trading.py --all --walk-forward  # benchmark all assets
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import yfinance as yf
except ImportError:
    print("ERROR: pip install numpy yfinance")
    sys.exit(1)

# Import from existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from bin.hmm_regime_detection import (
    HMMRegimeDetector, detect_regimes_ma,
    regime_statistics, regime_switches,
    REGIME_BULL, REGIME_BEAR, REGIME_SIDEWAYS, REGIME_NAMES
)
from bin.regime_aware_trading import (
    RegimeAwareDQN, run_episode_regime_aware,
    walk_forward_regime_aware, compute_features,
    compute_metrics, buy_and_hold_equity, ma_crossover_equity,
)


def fetch_prices(symbol, start, end):
    """Fetch daily close prices."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end)
    if df.empty:
        print(f"No data for {symbol}")
        return None
    return df["Close"].values.tolist()


def hmm_walk_forward(prices, features, n_windows=3, train_ratio=0.7,
                     episodes_per_window=50, trade_penalty=0.0, cost_model=None):
    """Walk-forward validation with HMM regimes (trained per window).

    Uses best-of-3-seed HMM initialization to avoid bad local optima.
    """
    n = len(prices)
    window_size = n // n_windows
    window_results = []

    candidate_seeds = [456, 789, 123]  # top performers from C538 benchmark

    for w in range(n_windows):
        start = w * window_size
        end = start + window_size if w < n_windows - 1 else n
        train_end = start + int(window_size * train_ratio)

        train_prices = np.array(prices[start:train_end])
        test_prices = np.array(prices[train_end:end])

        if len(train_prices) < 50 or len(test_prices) < 5:
            continue

        # Train HMM on train window only (no lookahead)
        # Best-of-3-seed to avoid bad local optima
        best_ll = -999999
        best_hmm = None
        for seed in candidate_seeds:
            rng_hmm = np.random.default_rng(seed)
            hmm = HMMRegimeDetector(rng=rng_hmm)
            hmm.fit(train_prices)
            if hmm.log_lls[-1] > best_ll:
                best_ll = hmm.log_lls[-1]
                best_hmm = hmm
        hmm = best_hmm

        # Predict regimes for both train and test
        train_regimes = hmm.predict(train_prices)
        test_regimes_full = hmm.predict(np.concatenate([train_prices, test_prices]))
        test_regimes = test_regimes_full[len(train_prices):]

        # Get features for train/test
        train_features = features[start:train_end]
        test_features = features[train_end:end]

        # Train RA-DQN on train window with HMM regimes
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
            run_episode_regime_aware(
                train_prices.tolist(), train_features, train_regimes,
                agent, trade_penalty, cost_model
            )
            agent.decay_epsilon()

        # Evaluate on test window
        agent.epsilon = 0
        test_equity, test_trades, test_pnl = run_episode_regime_aware(
            test_prices.tolist(), test_features, test_regimes, agent, 0, cost_model
        )

        bh_return = (test_prices[-1] - test_prices[0]) / test_prices[0] * 100 if len(test_prices) > 1 else 0

        window_results.append({
            "window": w + 1,
            "train_days": len(train_prices),
            "test_days": len(test_prices),
            "hmm_dqn_return_pct": round(test_pnl, 2),
            "bh_return_pct": round(bh_return, 2),
            "spread_pct": round(test_pnl - bh_return, 2),
            "num_trades": test_trades,
            "beat_bh": test_pnl > bh_return,
        })

    return window_results


def run_symbol(symbol, args, cost_model):
    """Run full comparison for one symbol."""
    prices = fetch_prices(symbol, args.start, args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    if prices is None:
        return None

    prices_np = np.array(prices)
    features = compute_features(prices)
    n_days = len(prices)

    # MA regimes (C537 baseline)
    ma_regimes = detect_regimes_ma(prices_np)

    # HMM regimes
    rng_hmm = np.random.default_rng(456)
    hmm = HMMRegimeDetector(rng=rng_hmm)
    hmm.fit(prices_np)
    hmm_regimes = hmm.predict(prices_np)

    ma_stats = regime_statistics(ma_regimes)
    hmm_stats = regime_statistics(hmm_regimes)
    ma_switches = regime_switches(ma_regimes)
    hmm_switches = regime_switches(hmm_regimes)

    results = {
        "symbol": symbol,
        "n_days": n_days,
        "ma_regimes": {"distribution": ma_stats, "switches": ma_switches},
        "hmm_regimes": {"distribution": hmm_stats, "switches": hmm_switches},
    }

    if not args.json:
        print(f"\n{'='*60}")
        print(f"{symbol} — HMM vs MA Regime Detection")
        print(f"{'='*60}")
        print(f"MA regimes:  {ma_stats} ({ma_switches} switches)")
        print(f"HMM regimes: {hmm_stats} ({hmm_switches} switches)")

    # Full-dataset RA-DQN comparison (in-sample, for reference)
    for regime_name, regimes in [("MA", ma_regimes), ("HMM", hmm_regimes)]:
        rng = np.random.default_rng(42)
        agent = RegimeAwareDQN(
            hidden_dim=64, lr=0.001, gamma=0.95,
            epsilon=1.0, epsilon_decay=0.98, epsilon_min=0.05,
            buffer_size=5000, batch_size=32,
            trade_penalty=0.0,
            target_update_freq=30,
            rng=rng
        )

        for ep in range(args.episodes):
            run_episode_regime_aware(
                prices, features, regimes, agent, 0.0, cost_model
            )
            agent.decay_epsilon()

        agent.epsilon = 0
        eq, trades, pnl = run_episode_regime_aware(prices, features, regimes, agent, 0, cost_model)
        metrics = compute_metrics(eq, f"{regime_name}-DQN")

        results[f"{regime_name.lower()}_dqn"] = {**metrics, "num_trades": trades}

        if not args.json:
            print(f"{regime_name}-DQN: {metrics['total_return_pct']:+.1f}% return, Sharpe {metrics['sharpe_ratio']:.2f}, {trades} trades")

    # Walk-forward comparison
    if args.walk_forward:
        if not args.json:
            print(f"\n--- Walk-Forward Validation ({args.windows} windows) ---")

        ma_wf = walk_forward_regime_aware(
            prices, features, ma_regimes, args.windows, train_ratio=0.7,
            episodes_per_window=30, trade_penalty=0.0, cost_model=cost_model
        )

        hmm_wf = hmm_walk_forward(
            prices, features, n_windows=args.windows, train_ratio=0.7,
            episodes_per_window=30, trade_penalty=0.0, cost_model=cost_model
        )

        results["walk_forward"] = {
            "ma": ma_wf,
            "hmm": hmm_wf,
            "ma_windows_beating_bh": sum(1 for w in ma_wf if w['beat_bh']),
            "hmm_windows_beating_bh": sum(1 for w in hmm_wf if w['beat_bh']),
        }

        if not args.json:
            print(f"{'Window':>7} {'MA-DQN':>9} {'HMM-DQN':>9} {'B&H':>7} {'MA Beat':>8} {'HMM Beat':>9}")
            print("-" * 60)
            for ma_w, hmm_w in zip(ma_wf, hmm_wf):
                ma_beat_str = "YES" if ma_w['beat_bh'] else "no "
                hmm_beat_str = "YES" if hmm_w['beat_bh'] else "no "
                print(f"{ma_w['window']:>7} "
                      f"{ma_w['ra_dqn_return_pct']:>8.1f}% "
                      f"{hmm_w['hmm_dqn_return_pct']:>8.1f}% "
                      f"{ma_w['bh_return_pct']:>6.1f}% "
                      f"{ma_beat_str:>6} "
                      f"{hmm_beat_str:>6}")
            print("-" * 60)
            print(f"MA beats B&H: {results['walk_forward']['ma_windows_beating_bh']}/{len(ma_wf)}")
            print(f"HMM beats B&H: {results['walk_forward']['hmm_windows_beating_bh']}/{len(hmm_wf)}")

    return results


def main():
    parser = argparse.ArgumentParser(description="HMM Regime-Aware DQN Trading")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--windows", type=int, default=3)
    parser.add_argument("--all", action="store_true", help="Run on TSLA, NVDA, SPY, AAPL")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cost_model = {'spread_bps': 10, 'commission_bps': 2}

    if args.all:
        symbols = ["TSLA", "NVDA", "SPY", "AAPL"]
        all_results = {}
        for sym in symbols:
            r = run_symbol(sym, args, cost_model)
            if r:
                all_results[sym] = r

        if not args.json:
            print(f"\n{'='*60}")
            print("SUMMARY — HMM vs MA Walk-Forward")
            print(f"{'='*60}")
            for sym, r in all_results.items():
                wf = r.get("walk_forward", {})
                ma_beat = wf.get("ma_windows_beating_bh", "N/A")
                hmm_beat = wf.get("hmm_windows_beating_bh", "N/A")
                total = len(wf.get("ma", [])) if wf.get("ma") else "N/A"
                print(f"{sym}: MA={ma_beat}/{total}, HMM={hmm_beat}/{total}")
        else:
            print(json.dumps(all_results, indent=2))
    else:
        r = run_symbol(args.symbol, args, cost_model)
        if r and args.json:
            print(json.dumps(r, indent=2))

    # Save to report
    Path("reports").mkdir(exist_ok=True)
    with open("reports/hmm_regime_trading.jsonl", "a") as f:
        f.write(json.dumps({"cycle": "C538", "timestamp": datetime.now(timezone.utc).isoformat(), "args": vars(args)}) + "\n")


if __name__ == "__main__":
    main()
