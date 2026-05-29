#!/usr/bin/env python3
"""Hidden Markov Model for Market Regime Detection.

Replaces the MA-based regime detector from C537 (regime_aware_trading.py)
with a probabilistic HMM that models regime transitions explicitly.

C537 finding: regime signal replaces trade penalty, but MA-based detection
fails for NVDA/SPY. HMM should capture regime structure that threshold-based
methods miss — especially short-lived regimes and transition probabilities.

3-state HMM:
  State 0: BULL (positive drift, moderate vol)
  State 1: BEAR (negative drift, high vol)
  State 2: SIDEWAYS (zero drift, low vol)

Observations: [daily_return, volatility] per timestep
Emissions: Gaussian with diagonal covariance
Training: Baum-Welch (EM)
Decoding: Viterbi (most likely state sequence)

Usage:
    python3 bin/hmm_regime_detection.py --symbol TSLA
    python3 bin/hmm_regime_detection.py --symbol TSLA --compare  # vs MA detector
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    from scipy.special import logsumexp
except ImportError:
    print("ERROR: pip install numpy scipy")
    sys.exit(1)

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance")
    sys.exit(1)


# ── Log-Space HMM Primitives ─────────────────────────────────────────────

NEG_INF = -3.0

def log_add(log_a, log_b):
    """log(exp(a) + exp(b)) without overflow."""
    if log_a <= NEG_INF:
        return log_b
    if log_b <= NEG_INF:
        return log_a
    if log_a > log_b:
        return log_a + math.log1p(math.exp(log_b - log_a))
    return log_b + math.log1p(math.exp(log_a - log_b))


def log_add_reduce(log_values):
    """log(sum(exp(values)))."""
    result = NEG_INF
    for v in log_values:
        result = log_add(result, v)
    return result


# ── Gaussian Emission ────────────────────────────────────────────────────

def log_gaussian_pdf(x, mean, var):
    """Log PDF of univariate Gaussian. x, mean, var can be arrays."""
    return -0.5 * np.log(2 * np.pi * var) - 0.5 * ((x - mean) ** 2) / var


def emission_log_prob(obs, means, vars_):
    """Log probability of observation under each state's Gaussian emission.

    Args:
        obs: (T, D) observations
        means: (K, D) state means
        vars_: (K, D) state variances (diagonal covariance)

    Returns:
        (T, K) log emission probabilities
    """
    T, D = obs.shape
    K = means.shape[0]
    log_emission = np.full((T, K), NEG_INF)
    for k in range(K):
        # Sum over dimensions (diagonal covariance = product of univariate Gaussians)
        log_emission[:, k] = np.sum(log_gaussian_pdf(obs, means[k], vars_[k]), axis=1)
    return log_emission


# ── Forward-Backward ─────────────────────────────────────────────────────

def forward(obs_log_prob, log_A, log_pi):
    """Forward algorithm in log space.

    Returns:
        log_alpha: (T, K) log forward probabilities
        log_Z: log likelihood of observation sequence
    """
    T, K = obs_log_prob.shape
    log_alpha = np.full((T, K), NEG_INF)

    # Initialization
    log_alpha[0] = obs_log_prob[0] + log_pi

    # Recursion
    for t in range(1, T):
        for k in range(K):
            # log_alpha[t, k] = log_sum_j (log_alpha[t-1, j] + log_A[j, k]) + log B_k(o_t)
            log_alpha[t, k] = log_add_reduce(log_alpha[t - 1] + log_A[:, k]) + obs_log_prob[t, k]

    log_Z = log_add_reduce(log_alpha[T - 1])
    return log_alpha, log_Z


def backward(obs_log_prob, log_A, log_pi):
    """Backward algorithm in log space.

    Returns:
        log_beta: (T, K) log backward probabilities
    """
    T, K = obs_log_prob.shape
    log_beta = np.full((T, K), NEG_INF)

    # Initialization: log_beta[T-1] = 0 (log(1) = 0)
    log_beta[T - 1] = 0.0

    # Recursion
    for t in range(T - 2, -1, -1):
        for j in range(K):
            # log_beta[t, j] = log_sum_k (log_A[j, k] + log B_k(o_{t+1}) + log_beta[t+1, k])
            terms = log_A[j] + obs_log_prob[t + 1] + log_beta[t + 1]
            log_beta[t, j] = log_add_reduce(terms)

    return log_beta


# ── Baum-Welch (EM) ──────────────────────────────────────────────────────

def baum_welch(obs, n_states, n_iter=100, tol=1e-4, rng=None):
    """Train HMM parameters via Baum-Welch (EM).

    Args:
        obs: (T, D) observations
        n_states: number of hidden states
        n_iter: max EM iterations
        tol: convergence threshold on log-likelihood
        rng: random number generator for initialization

    Returns:
        A: (K, K) transition matrix
        means: (K, D) emission means
        vars_: (K, D) emission variances
        pi: (K,) initial state distribution
        log_likelihoods: list of log-likelihoods per iteration
    """
    rng = rng or np.random.default_rng(42)
    T, D = obs.shape
    K = n_states

    # Initialize parameters
    # Random init for transition matrix (ensure rows sum to 1)
    A = rng.dirichlet(np.ones(K), size=K)
    # Init means from quantiles (see below), variances from overall variance
    vars_ = np.tile(np.var(obs, axis=0), (K, 1))
    # Ensure minimum variance for numerical stability
    vars_ = np.maximum(vars_, 1e-8)
    # Uniform initial state distribution
    pi = np.ones(K) / K

    # Better init: use quantile-based initialization for means
    obs_sorted = np.sort(obs[:, 0])
    third = T // 3
    two_thirds = 2 * T // 3
    init_means = np.zeros((K, D))
    init_means[0, 0] = np.mean(obs_sorted[two_thirds:])  # bull: high returns
    init_means[1, 0] = np.mean(obs_sorted[:third])  # bear: low returns
    init_means[2, 0] = np.mean(obs_sorted[third:two_thirds])  # sideways: mid returns
    for d in range(1, D):
        init_means[:, d] = np.mean(obs[:, d])

    means = init_means

    # Re-init vars based on means
    for k in range(K):
        vars_[k] = np.var(obs - means[k], axis=0) + 1e-6
    vars_ = np.maximum(vars_, 1e-8)

    log_lls = []

    for iteration in range(n_iter):
        log_A = np.log(A + 1e-10)
        log_pi = np.log(pi + 1e-10)

        # E-step
        obs_log_prob = emission_log_prob(obs, means, vars_)
        log_alpha, log_Z = forward(obs_log_prob, log_A, log_pi)
        log_beta = backward(obs_log_prob, log_A, log_pi)

        log_lls.append(float(log_Z))

        if iteration > 0 and abs(log_lls[-1] - log_lls[-2]) < tol:
            break

        # Compute gamma (state occupancy probabilities)
        log_gamma = log_alpha + log_beta - log_Z
        gamma = np.exp(log_gamma)
        gamma = gamma / gamma.sum(axis=1, keepdims=True)  # normalize

        # Compute xi (transition probabilities)
        log_A_new = np.full((K, K), NEG_INF)
        for i in range(K):
            for j in range(K):
                for t in range(T - 1):
                    log_val = log_alpha[t, i] + log_A[i, j] + obs_log_prob[t + 1, j] + log_beta[t + 1, j]
                    log_A_new[i, j] = log_add(log_A_new[i, j], log_val)
                log_A_new[i, j] -= log_Z

        A = np.exp(log_A_new)
        A = A / A.sum(axis=1, keepdims=True)

        # Update means and variances
        for k in range(K):
            weights = gamma[:, k]
            total_weight = weights.sum()
            if total_weight > 1e-10:
                for d in range(D):
                    means[k, d] = np.sum(weights * obs[:, d]) / total_weight
                    vars_[k, d] = np.sum(weights * (obs[:, d] - means[k, d]) ** 2) / total_weight
                    vars_[k, d] = max(vars_[k, d], 1e-8)

        # Update initial state distribution
        pi = gamma[0] / gamma[0].sum()

    # Sort states by mean return (descending): Bull, Bear, Sideways
    # Actually sort as: Bull (high return), Bear (low return), Sideways (mid return)
    sort_order = np.argsort(-means[:, 0])  # descending by mean return
    # Reorder: Bull=0, Bear=2, Sideways=1 → we want Bull, Bear, Sideways
    # After sort: [Bull, Sideways, Bear] by return
    # We want: [Bull, Bear, Sideways]
    # So reorder indices: [0, 2, 1] from sorted
    final_order = [sort_order[0], sort_order[2], sort_order[1]]
    A = A[final_order][:, final_order]
    means = means[final_order]
    vars_ = vars_[final_order]
    pi = pi[final_order]

    return A, means, vars_, pi, log_lls


# ── Viterbi Decoding ─────────────────────────────────────────────────────

def viterbi(obs_log_prob, log_A, log_pi):
    """Viterbi algorithm in log space.

    Returns:
        path: (T,) most likely state sequence
        log_prob: log probability of the path
    """
    T, K = obs_log_prob.shape
    log_delta = np.full((T, K), NEG_INF)
    psi = np.zeros((T, K), dtype=int)

    # Initialization
    log_delta[0] = obs_log_prob[0] + log_pi

    # Recursion
    for t in range(1, T):
        for k in range(K):
            scores = log_delta[t - 1] + log_A[:, k]
            psi[t, k] = np.argmax(scores)
            log_delta[t, k] = scores[psi[t, k]] + obs_log_prob[t, k]

    # Backtrack
    path = np.zeros(T, dtype=int)
    path[T - 1] = np.argmax(log_delta[T - 1])
    log_prob = log_delta[T - 1, path[T - 1]]

    for t in range(T - 2, -1, -1):
        path[t] = psi[t + 1, path[t + 1]]

    return path, log_prob


# ── HMM Regime Detector ──────────────────────────────────────────────────

REGIME_BULL = 0
REGIME_BEAR = 1
REGIME_SIDEWAYS = 2
REGIME_NAMES = {REGIME_BULL: "BULL", REGIME_BEAR: "BEAR", REGIME_SIDEWAYS: "SIDEWAYS"}


def smooth_regime_path(path, min_duration=3):
    """Remove regime segments shorter than min_duration.

    Uses single-pass smoothing: only absorbs into original (pre-smoothing)
    neighbors, preventing cascading collapses where one regime absorbs all others.
    """
    result = path.copy()

    # Find all segment boundaries
    segments = []  # (start, end, regime)
    i = 0
    while i < len(result):
        regime = result[i]
        j = i
        while j < len(result) and result[j] == regime:
            j += 1
        segments.append((i, j, regime))
        i = j

    # Merge short segments into their nearest neighbor (original, not cascaded)
    i = 0
    while i < len(segments):
        start, end, regime = segments[i]
        duration = end - start
        if duration < min_duration:
            # Find best neighbor (original regime, not already merged)
            left_regime = segments[i - 1][2] if i > 0 else regime
            right_regime = segments[i + 1][2] if i < len(segments) - 1 else regime

            # Pick the neighbor with longer duration (more stable)
            left_dur = segments[i - 1][1] - segments[i - 1][0] if i > 0 else 0
            right_dur = segments[i + 1][1] - segments[i + 1][0] if i < len(segments) - 1 else 0

            if left_dur >= right_dur and i > 0:
                result[start:end] = left_regime
            elif i < len(segments) - 1:
                result[start:end] = right_regime
            # else: keep as is (no neighbors or equal)
        i += 1

    return result


class HMMRegimeDetector:
    """3-state HMM for market regime detection."""

    def __init__(self, n_states=3, n_iter=100, tol=1e-4, rng=None):
        self.n_states = n_states
        self.n_iter = n_iter
        self.tol = tol
        self.rng = rng or np.random.default_rng(42)
        self.A = None
        self.means = None
        self.vars_ = None
        self.pi = None
        self.log_lls = None
        self.is_fitted = False

    def _prepare_observations(self, prices):
        """Prepare observation features from price series.

        Uses 3D observations: [daily_return, rolling_volatility, momentum].
        - daily_return: captures immediate direction
        - rolling_volatility (20-day): captures regime uncertainty
        - momentum (10-day return): captures trend persistence

        Returns:
            obs: (T, 3) array of [return, vol, momentum]
        """
        n = len(prices)
        returns = np.zeros(n)
        returns[1:] = np.diff(prices) / prices[:-1]

        # Rolling 20-day volatility
        vol = np.zeros(n)
        vol_window = 20
        for i in range(vol_window, n):
            vol[i] = np.std(returns[i - vol_window:i])

        # 10-day momentum (cumulative return over 10 days)
        momentum = np.zeros(n)
        mom_window = 10
        for i in range(mom_window, n):
            momentum[i] = prices[i] / prices[i - mom_window] - 1.0

        obs = np.column_stack([returns, vol, momentum])
        obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
        return obs

    def fit(self, prices):
        """Train HMM on price data."""
        obs = self._prepare_observations(prices)
        # Remove warmup period where rolling features are zero
        warmup = 20  # vol_window = 20, covers momentum (10) too
        obs = obs[warmup:]

        self.A, self.means, self.vars_, self.pi, self.log_lls = baum_welch(
            obs, self.n_states, self.n_iter, self.tol, self.rng
        )
        self.is_fitted = True
        self._warmup = warmup
        return self

    def predict(self, prices):
        """Predict regime sequence for price data.

        Returns:
            regimes: (T,) array of regime labels
        """
        if not self.is_fitted:
            raise RuntimeError("HMM not fitted. Call fit() first.")

        obs = self._prepare_observations(prices)
        obs = obs[self._warmup:]
        T = len(prices)

        obs_log_prob = emission_log_prob(obs, self.means, self.vars_)
        log_A = np.log(self.A + 1e-10)
        log_pi = np.log(self.pi + 1e-10)

        path, _ = viterbi(obs_log_prob, log_A, log_pi)

        # Smooth: remove regime segments shorter than min_duration
        # This prevents HMM from overfitting to single-day noise
        smoothed = smooth_regime_path(path, min_duration=5)

        # Pad to full length
        regimes = np.full(T, REGIME_SIDEWAYS, dtype=int)
        regimes[:self._warmup] = REGIME_SIDEWAYS
        regimes[self._warmup:] = smoothed

        return regimes

    def summary(self):
        """Print HMM parameter summary."""
        if not self.is_fitted:
            return "HMM not fitted."

        lines = ["HMM Regime Detector Parameters:", "=" * 50]
        for k, name in REGIME_NAMES.items():
            lines.append(f"  {name}:")
            lines.append(f"    Mean return: {self.means[k, 0]:+.4f} ({self.means[k, 0] * 252 * 100:+.1f}% annualized)")
            lines.append(f"    Variance:    {self.vars_[k, 0]:.6f}")

        lines.append(f"  Transition matrix:")
        for i, from_name in REGIME_NAMES.items():
            row = "    ".join(f"{self.A[i, j]:.3f}" for j in range(self.n_states))
            lines.append(f"    {from_name}: {row}")

        lines.append(f"  Initial probs: {'  '.join(f'{p:.3f}' for p in self.pi)}")
        lines.append(f"  Log-likelihood (final): {self.log_lls[-1]:.2f}")
        lines.append(f"  EM iterations: {len(self.log_lls)}")
        return "\n".join(lines)


# ── MA-Based Regime Detector (from C537, for comparison) ─────────────────

def detect_regimes_ma(prices, trend_window=20, vol_window=30, trend_threshold=0.01):
    """MA-based regime detection from C537."""
    n = len(prices)
    regimes = np.full(n, REGIME_SIDEWAYS, dtype=int)

    for i in range(n):
        if i < trend_window:
            continue
        short_ma = np.mean(prices[i - trend_window // 2:i])
        long_ma = np.mean(prices[i - trend_window:i])
        trend = (short_ma - long_ma) / prices[i]
        if trend > trend_threshold:
            regimes[i] = REGIME_BULL
        elif trend < -trend_threshold:
            regimes[i] = REGIME_BEAR

    return regimes


def regime_statistics(regimes):
    """Fraction of time in each regime."""
    total = len(regimes)
    stats = {}
    for label, name in REGIME_NAMES.items():
        count = int(np.sum(regimes == label))
        stats[name] = round(float(count / total * 100), 1)
    return stats


def regime_switches(regimes):
    """Count number of regime transitions."""
    return int(np.sum(regimes[1:] != regimes[:-1]))


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HMM Regime Detection")
    parser.add_argument("--symbol", default="TSLA")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--compare", action="store_true", help="Compare HMM vs MA detector")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticker = yf.Ticker(args.symbol)
    df = ticker.history(start=args.start, end=end_date)

    if df.empty:
        print(f"No data for {args.symbol}")
        sys.exit(1)

    prices = df["Close"].values
    n_days = len(prices)

    # Train and predict with HMM
    hmm = HMMRegimeDetector(rng=np.random.default_rng(42))
    hmm.fit(prices)
    hmm_regimes = hmm.predict(prices)

    if not args.json:
        print(f"HMM Regime Detection — {args.symbol}")
        print(f"Period: {args.start} to {end_date} ({n_days} trading days)")
        print()
        print(hmm.summary())
        print()

        hmm_stats = regime_statistics(hmm_regimes)
        hmm_switches = regime_switches(hmm_regimes)
        print(f"Regime distribution: {hmm_stats}")
        print(f"Regime switches: {hmm_switches}")

        if args.compare:
            # Compare with MA-based detector
            ma_regimes = detect_regimes_ma(prices)
            ma_stats = regime_statistics(ma_regimes)
            ma_switches = regime_switches(ma_regimes)

            print()
            print("=" * 60)
            print("HMM vs MA Regime Detection Comparison")
            print("=" * 60)
            print(f"{'Metric':<25} {'HMM':>12} {'MA':>12}")
            print("-" * 60)
            print(f"{'BULL %':<25} {hmm_stats['BULL']:>10.1f}% {ma_stats['BULL']:>10.1f}%")
            print(f"{'BEAR %':<25} {hmm_stats['BEAR']:>10.1f}% {ma_stats['BEAR']:>10.1f}%")
            print(f"{'SIDEWAYS %':<25} {hmm_stats['SIDEWAYS']:>10.1f}% {ma_stats['SIDEWAYS']:>10.1f}%")
            print(f"{'Switches':<25} {hmm_switches:>12} {ma_switches:>12}")
            print("=" * 60)

            # Agreement analysis
            agreement = np.sum(hmm_regimes == ma_regimes) / len(hmm_regimes) * 100
            print(f"Agreement: {agreement:.1f}%")

            # Per-regime return analysis
            returns = np.diff(prices) / prices[:-1]
            print()
            print("--- Per-Regime Return Analysis (HMM) ---")
            for label, name in REGIME_NAMES.items():
                mask = hmm_regimes[1:] == label
                days = int(np.sum(mask))
                if days > 0:
                    regime_returns = returns[mask]
                    avg_ret = float(np.mean(regime_returns) * 100)
                    std_ret = float(np.std(regime_returns) * 100)
                    print(f"  {name}: {days} days, avg daily: {avg_ret:+.3f}%, std: {std_ret:.3f}%")

            print()
            print("--- Per-Regime Return Analysis (MA) ---")
            for label, name in REGIME_NAMES.items():
                mask = ma_regimes[1:] == label
                days = int(np.sum(mask))
                if days > 0:
                    regime_returns = returns[mask]
                    avg_ret = float(np.mean(regime_returns) * 100)
                    std_ret = float(np.std(regime_returns) * 100)
                    print(f"  {name}: {days} days, avg daily: {avg_ret:+.3f}%, std: {std_ret:.3f}%")

    # JSON output
    results = {
        "cycle": "C538",
        "symbol": args.symbol,
        "period": f"{args.start} to {end_date}",
        "hmm": {
            "regime_distribution": regime_statistics(hmm_regimes),
            "regime_switches": regime_switches(hmm_regimes),
            "log_likelihood": round(hmm.log_lls[-1], 2),
            "em_iterations": len(hmm.log_lls),
            "means": {REGIME_NAMES[k]: {"return": round(float(hmm.means[k, 0]), 6)}
                      for k in range(hmm.n_states)},
            "transitions": {REGIME_NAMES[i]: {REGIME_NAMES[j]: round(float(hmm.A[i, j]), 4)
                                               for j in range(hmm.n_states)}
                             for i in range(hmm.n_states)},
        }
    }

    if args.compare:
        ma_regimes = detect_regimes_ma(prices)
        results["ma"] = {
            "regime_distribution": regime_statistics(ma_regimes),
            "regime_switches": regime_switches(ma_regimes),
        }
        results["agreement_pct"] = round(float(np.sum(hmm_regimes == ma_regimes) / len(hmm_regimes) * 100), 1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        Path("reports").mkdir(exist_ok=True)
        with open("reports/hmm_regime_detection.jsonl", "a") as f:
            f.write(json.dumps(results) + "\n")
        print(f"\nResults saved to reports/hmm_regime_detection.jsonl")


if __name__ == "__main__":
    main()
