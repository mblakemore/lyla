#!/usr/bin/env python3
"""HMM State Identifiability Audit — are the detected regimes meaningful?

C538/C539 findings: HMM beats MA in walk-forward but neither consistently beats B&H.
Creator's note: HMM states may not be identifiable — transition matrix oscillates
between junk states, smoothing hides the noise, and "BEAR" mean return is +0.0002.

Audits each asset's HMM for:
  1. Transition matrix diagonal dominance (sticky states = real regimes)
  2. Emission-mean separation in σ (can we tell states apart?)
  3. Label validity (does "BULL" actually have positive returns?)
  4. Oscillator detection (A→B→A patterns that look like switches but aren't regimes)
  5. Smoothed vs raw switch count (how much did min_duration=5 hide?)

Usage:
    python3 bin/hmm_state_identifiability.py --symbol TSLA
    python3 bin/hmm_state_identifiability.py --all
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

sys.path.insert(0, str(Path(__file__).parent.parent))
from bin.hmm_regime_detection import (
    HMMRegimeDetector,
    REGIME_NAMES,
    smooth_regime_path,
    emission_log_prob,
)


def transition_diagonal(A):
    """Fraction of time spent in self-transitions vs switching."""
    return np.diag(A).copy()


def oscillator_score(A):
    """Detect 2-state oscillators: A→B→A cycles dominate.

    Returns max oscillation probability for each state pair.
    An oscillator between states i,j means: A[i,j] * A[j,i] is high.
    """
    K = A.shape[0]
    scores = np.zeros((K, K))
    for i in range(K):
        for j in range(K):
            if i != j:
                scores[i, j] = A[i, j] * A[j, i] + A[j, i] * A[i, j]
    return scores


def emission_separation(means, vars_):
    """Compute pairwise mean separation in units of pooled σ per dimension.

    Returns (K, K) matrix where [i,j] = mean separation in σ between states i and j.
    Uses the pooled std: sqrt((var_i + var_j) / 2)
    """
    K = means.shape[0]
    D = means.shape[1]
    sep = np.zeros((K, K, D))  # [i, j, dim]
    for i in range(K):
        for j in range(K):
            pooled_std = np.sqrt((vars_[i] + vars_[j]) / 2)
            pooled_std = np.maximum(pooled_std, 1e-10)
            sep[i, j] = np.abs(means[i] - means[j]) / pooled_std
    return sep


def label_validity(means, prices, regimes):
    """Check if regime labels match actual behavior.

    For each state, compute the actual mean return of days assigned to that state.
    Returns dict: {state_name: {"mean_return": ..., "expected_sign": ..., "valid": bool}}
    """
    returns = np.diff(prices) / prices[:-1]
    # Align: regimes[1:] matches returns
    aligned_regimes = regimes[1:]

    validity = {}
    expected = {0: "positive", 1: "negative", 2: "near_zero"}
    for k, name in REGIME_NAMES.items():
        mask = aligned_regimes == k
        if np.sum(mask) > 0:
            actual_mean = float(np.mean(returns[mask]))
        else:
            actual_mean = 0.0
        valid = True
        if k == 0 and actual_mean <= 0:  # BULL should be positive
            valid = False
        elif k == 1 and actual_mean >= 0:  # BEAR should be negative
            valid = False
        elif k == 2 and abs(actual_mean) > 0.002:  # SIDEWAYS should be near zero
            valid = False
        validity[name] = {
            "mean_return": round(actual_mean * 100, 4),
            "expected": expected[k],
            "valid": valid,
        }
    return validity


def raw_vs_smoothed_switches(prices, hmm):
    """Compare switch count before and after smoothing (min_duration=5)."""
    obs = hmm._prepare_observations(prices)
    obs = obs[hmm._warmup:]
    obs_log_prob = emission_log_prob(obs, hmm.means, hmm.vars_)
    log_A = np.log(hmm.A + 1e-10)
    log_pi = np.log(hmm.pi + 1e-10)

    from bin.hmm_regime_detection import viterbi
    raw_path, _ = viterbi(obs_log_prob, log_A, log_pi)

    # Pad to full length
    full_raw = np.full(len(prices), 2, dtype=int)  # 2 = SIDEWAYS
    full_raw[:hmm._warmup] = 2
    full_raw[hmm._warmup:] = raw_path

    raw_switches = int(np.sum(full_raw[1:] != full_raw[:-1]))

    # Smoothed
    smoothed = smooth_regime_path(raw_path.copy(), min_duration=5)
    full_smoothed = np.full(len(prices), 2, dtype=int)
    full_smoothed[:hmm._warmup] = 2
    full_smoothed[hmm._warmup:] = smoothed
    smooth_switches = int(np.sum(full_smoothed[1:] != full_smoothed[:-1]))

    return raw_switches, smooth_switches


def identifiability_report(symbol, prices):
    """Compute full identifiability report for one asset."""
    hmm = HMMRegimeDetector(rng=np.random.default_rng(42))
    hmm.fit(prices)
    regimes = hmm.predict(prices)

    A = hmm.A
    means = hmm.means
    vars_ = hmm.vars_
    K = A.shape[0]

    # 1. Diagonal dominance
    diagonal = transition_diagonal(A)

    # 2. Oscillator detection
    osc = oscillator_score(A)
    max_osc = np.max(osc)
    # Find which pair oscillates most
    osc_pair = np.unravel_index(np.argmax(osc), osc.shape)

    # 3. Emission separation
    sep = emission_separation(means, vars_)
    # Average separation across dimensions, across all pairs
    avg_sep = np.mean([sep[i, j] for i in range(K) for j in range(K) if i < j])

    # 4. Label validity
    validity = label_validity(means, prices, regimes)

    # 5. Raw vs smoothed switches
    raw_sw, smooth_sw = raw_vs_smoothed_switches(prices, hmm)

    # 6. State occupancy
    occupancy = {REGIME_NAMES[k]: round(float(np.sum(regimes == k) / len(regimes) * 100), 1)
                 for k in range(K)}

    # 7. Identifiability score (0-100, higher = better)
    # Components: diagonal dominance, mean separation, label validity, no oscillators
    diag_score = float(np.mean(diagonal)) * 100  # sticky states
    sep_score = min(avg_sep / 2.0, 1.0) * 100  # 2σ separation = 100
    valid_score = sum(1 for v in validity.values() if v["valid"]) / len(validity) * 100
    osc_penalty = max_osc * 100 if osc_pair[0] != osc_pair[1] else 0  # penalize oscillators
    smooth_ratio = smooth_sw / max(raw_sw, 1)  # how much smoothing reduced switches

    score = round((diag_score * 0.3 + sep_score * 0.3 + valid_score * 0.2 + (100 - osc_penalty) * 0.2), 1)

    report = {
        "symbol": symbol,
        "n_days": len(prices),
        "identifiability_score": score,
        "transition_diagonal": {REGIME_NAMES[i]: round(float(diagonal[i]), 3) for i in range(K)},
        "max_oscillation": {
            "pair": f"{REGIME_NAMES[osc_pair[0]]}-{REGIME_NAMES[osc_pair[1]]}",
            "score": round(float(max_osc), 4),
        },
        "emission_separation_sigma": round(float(avg_sep), 3),
        "label_validity": validity,
        "raw_switches": raw_sw,
        "smoothed_switches": smooth_sw,
        "smooth_ratio": round(smooth_ratio, 2),
        "state_occupancy": occupancy,
        "transition_matrix": {REGIME_NAMES[i]: {REGIME_NAMES[j]: round(float(A[i, j]), 3)
                                                  for j in range(K)}
                               for i in range(K)},
        "emission_means": {REGIME_NAMES[k]: {"return": round(float(means[k, 0]), 6),
                                              "vol": round(float(means[k, 1]), 6),
                                              "momentum": round(float(means[k, 2]), 6)}
                           for k in range(K)},
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="HMM State Identifiability Audit")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.all:
        symbols = ["TSLA", "NVDA", "SPY", "AAPL"]
    else:
        symbols = [args.symbol]

    all_reports = {}

    if not args.json:
        print("=" * 80)
        print("HMM State Identifiability Audit")
        print("=" * 80)

    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=args.start, end=end_date)
        if df.empty:
            print(f"No data for {symbol}")
            continue

        prices = df["Close"].values
        report = identifiability_report(symbol, prices)
        all_reports[symbol] = report

        if not args.json:
            print(f"\n{'─' * 60}")
            print(f"{symbol} — Identifiability Score: {report['identifiability_score']}/100")
            print(f"{'─' * 60}")

            # Transition matrix
            print(f"Transition matrix:")
            for from_name, row in report["transition_matrix"].items():
                row_str = " ".join(f"{row[to_name]:.3f}" for to_name in REGIME_NAMES.values())
                print(f"  {from_name}: {row_str}")

            print(f"\nDiagonal dominance (self-transition):")
            for name, val in report["transition_diagonal"].items():
                indicator = " OK" if val > 0.7 else " WEAK" if val > 0.4 else " POOR"
                print(f"  {name}: {val:.3f}{indicator}")

            print(f"\nOscillator risk: {report['max_oscillation']['pair']} = {report['max_oscillation']['score']:.4f}")

            print(f"\nEmission mean separation: {report['emission_separation_sigma']:.3f}σ")

            print(f"\nLabel validity:")
            for name, v in report["label_validity"].items():
                status = "VALID" if v["valid"] else "INVALID"
                print(f"  {name}: mean return {v['mean_return']:+.3f}% (expected {v['expected']}) — {status}")

            print(f"\nSwitches: raw={report['raw_switches']}, smoothed={report['smoothed_switches']} "
                  f"(smoothing hid {1 - report['smooth_ratio']:.0%} of switches)")

            print(f"\nState occupancy: {report['state_occupancy']}")

    # Save
    Path("reports").mkdir(exist_ok=True)
    with open("reports/hmm_identifiability.jsonl", "a") as f:
        f.write(json.dumps({
            "cycle": "C540",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "args": vars(args),
            "reports": all_reports,
        }) + "\n")

    if args.json:
        print(json.dumps(all_reports, indent=2))
    else:
        print(f"\nResults saved to reports/hmm_identifiability.jsonl")


if __name__ == "__main__":
    main()
