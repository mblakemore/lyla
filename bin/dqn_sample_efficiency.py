#!/usr/bin/env python3
"""DQN Sample Efficiency Study — episodes-per-window convergence sweep.

C538 finding: "DQN sample efficiency is the bottleneck, not regime quality."
Walk-forward uses 30 episodes/window — is that enough?

Runs walk-forward at multiple episode counts to measure convergence:
  30, 50, 100, 200, 500 episodes per window

Compares HMM-DQN vs MA-DQN across all assets.
Answers: does more training help beat B&H? Where does it plateau?

Usage:
    python3 bin/dqn_sample_efficiency.py --symbol TSLA
    python3 bin/dqn_sample_efficiency.py --all
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    import yfinance as yf
except ImportError:
    print("ERROR: pip install numpy yfinance")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from bin.hmm_regime_detection import HMMRegimeDetector
from bin.regime_aware_trading import (
    RegimeAwareDQN, run_episode_regime_aware,
    compute_features, buy_and_hold_equity,
    REGIME_BULL, REGIME_BEAR, REGIME_SIDEWAYS,
)
from bin.hmm_regime_trading import hmm_walk_forward, fetch_prices


def ma_walk_forward(prices, features, n_windows, episodes_per_window, cost_model):
    """Walk-forward with MA regimes."""
    from bin.hmm_regime_detection import detect_regimes_ma
    from bin.regime_aware_trading import walk_forward_regime_aware
    regimes = detect_regimes_ma(np.array(prices))
    return walk_forward_regime_aware(
        prices, features, regimes, n_windows, train_ratio=0.7,
        episodes_per_window=episodes_per_window, trade_penalty=0.0, cost_model=cost_model
    )


def sample_efficiency_sweep(symbol, episode_counts, n_windows=3, cost_model=None):
    """Run walk-forward at multiple episode counts for both MA and HMM regimes.

    Returns a dict with convergence data for each episode count.
    """
    if cost_model is None:
        cost_model = {'spread_bps': 10, 'commission_bps': 2}

    prices = np.array(fetch_prices(symbol, "2024-01-01",
                       datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    features = compute_features(prices.tolist())

    results = {
        "symbol": symbol,
        "n_days": len(prices),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "episode_counts": episode_counts,
    }

    for ep_count in episode_counts:
        t0 = time.time()

        # MA regimes
        ma_wf = ma_walk_forward(
            prices.tolist(), features, n_windows, ep_count, cost_model
        )
        ma_beat = sum(1 for w in ma_wf if w.get('beat_bh', False))
        ma_avg_return = np.mean([w['ra_dqn_return_pct'] for w in ma_wf]) if ma_wf else 0
        ma_avg_spread = np.mean([w['spread_pct'] for w in ma_wf]) if ma_wf else 0

        # HMM regimes
        hmm_wf = hmm_walk_forward(
            prices.tolist(), features, n_windows, train_ratio=0.7,
            episodes_per_window=ep_count, trade_penalty=0.0, cost_model=cost_model
        )
        hmm_beat = sum(1 for w in hmm_wf if w.get('beat_bh', False))
        hmm_avg_return = np.mean([w['hmm_dqn_return_pct'] for w in hmm_wf]) if hmm_wf else 0
        hmm_avg_spread = np.mean([w['spread_pct'] for w in hmm_wf]) if hmm_wf else 0

        elapsed = round(time.time() - t0, 1)

        results[f"ep{ep_count}"] = {
            "ma": {
                "windows_beating_bh": ma_beat,
                "total_windows": len(ma_wf),
                "avg_return_pct": round(ma_avg_return, 2),
                "avg_spread_pct": round(ma_avg_spread, 2),
            },
            "hmm": {
                "windows_beating_bh": hmm_beat,
                "total_windows": len(hmm_wf),
                "avg_return_pct": round(hmm_avg_return, 2),
                "avg_spread_pct": round(hmm_avg_spread, 2),
            },
            "elapsed_seconds": elapsed,
        }

    return results


def main():
    parser = argparse.ArgumentParser(description="DQN Sample Efficiency Study")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--all", action="store_true", help="Run on TSLA, NVDA, SPY, AAPL")
    parser.add_argument("--windows", type=int, default=3)
    parser.add_argument("--episodes", type=str, default="30,50,100,200,500",
                        help="Comma-separated episode counts to test")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    episode_counts = [int(e) for e in args.episodes.split(",")]

    if args.all:
        symbols = ["TSLA", "NVDA", "SPY", "AAPL"]
    else:
        symbols = [args.symbol]

    all_results = {}

    if not args.json:
        print("=" * 80)
        print("DQN Sample Efficiency Study — Episodes-per-Window Convergence")
        print(f"Episode counts: {episode_counts}")
        print("=" * 80)

    for symbol in symbols:
        if not args.json:
            print(f"\n{'─' * 60}")
            print(f"Processing {symbol}...")

        r = sample_efficiency_sweep(symbol, episode_counts, args.windows)
        all_results[symbol] = r

        if not args.json:
            print(f"\n{'Episodes':>10} {'MA Beat B&H':>12} {'MA Spread':>10} "
                  f"{'HMM Beat B&H':>13} {'HMM Spread':>11} {'Time':>6}")
            print("-" * 65)
            for ep in episode_counts:
                key = f"ep{ep}"
                if key in r:
                    ma = r[key]["ma"]
                    hmm = r[key]["hmm"]
                    ma_str = f"{ma['windows_beating_bh']}/{ma['total_windows']}"
                    hmm_str = f"{hmm['windows_beating_bh']}/{hmm['total_windows']}"
                    print(f"{ep:>10} {ma_str:>12} {ma['avg_spread_pct']:>+9.1f}pp "
                          f"{hmm_str:>13} {hmm['avg_spread_pct']:>+10.1f}pp "
                          f"{r[key]['elapsed_seconds']:>5.0f}s")

    # Save results
    Path("reports").mkdir(exist_ok=True)
    with open("reports/dqn_sample_efficiency.jsonl", "a") as f:
        f.write(json.dumps({
            "cycle": "C539",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args": vars(args),
            "results": all_results,
        }) + "\n")

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        print(f"\nResults saved to reports/dqn_sample_efficiency.jsonl")


if __name__ == "__main__":
    main()
