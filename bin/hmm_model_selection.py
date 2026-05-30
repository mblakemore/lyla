#!/usr/bin/env python3
"""HMM Model Selection — BIC/AIC for Optimal Number of States.

C540 found that 3-state HMM learns alternation patterns, not market regimes
for volatile assets. The question: how many states should the HMM actually have?

Sweeps K=2..6 states per asset, computes BIC and AIC, and identifies the
model order that best balances fit and complexity.

Usage:
    python3 bin/hmm_model_selection.py --symbol TSLA
    python3 bin/hmm_model_selection.py --all  # TSLA, NVDA, SPY, AAPL
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import yfinance as yf
except ImportError:
    print("ERROR: pip install yfinance")
    sys.exit(1)

# ── Import HMM primitives from hmm_regime_detection ────────────────────────
# We reuse the same forward/backward/Baum-Welch machinery but generalize
# initialization for arbitrary K (the existing code hardcodes K=3 quantiles).

NEG_INF = -3.0


def log_add(log_a, log_b):
    if log_a <= NEG_INF: return log_b
    if log_b <= NEG_INF: return log_a
    if log_a > log_b:
        return log_a + np.log1p(np.exp(log_b - log_a))
    return log_b + np.log1p(np.exp(log_a - log_b))


def log_add_reduce(log_values):
    result = NEG_INF
    for v in log_values:
        result = log_add(result, v)
    return result


def log_gaussian_pdf(x, mean, var):
    return -0.5 * np.log(2 * np.pi * var) - 0.5 * ((x - mean) ** 2) / var


def emission_log_prob(obs, means, vars_):
    T, D = obs.shape
    K = means.shape[0]
    log_emission = np.full((T, K), NEG_INF)
    for k in range(K):
        log_emission[:, k] = np.sum(log_gaussian_pdf(obs, means[k], vars_[k]), axis=1)
    return log_emission


def forward_alg(obs_log_prob, log_A, log_pi):
    T, K = obs_log_prob.shape
    log_alpha = np.full((T, K), NEG_INF)
    log_alpha[0] = obs_log_prob[0] + log_pi
    for t in range(1, T):
        for k in range(K):
            log_alpha[t, k] = log_add_reduce(log_alpha[t - 1] + log_A[:, k]) + obs_log_prob[t, k]
    log_Z = log_add_reduce(log_alpha[T - 1])
    return log_alpha, log_Z


def backward_alg(obs_log_prob, log_A, log_pi):
    T, K = obs_log_prob.shape
    log_beta = np.full((T, K), NEG_INF)
    log_beta[T - 1] = 0.0
    for t in range(T - 2, -1, -1):
        for j in range(K):
            terms = log_A[j] + obs_log_prob[t + 1] + log_beta[t + 1]
            log_beta[t, j] = log_add_reduce(terms)
    return log_beta


def count_params(K, D):
    """Count free parameters in a K-state, D-dim HMM.

    Transition: K*(K-1) (rows sum to 1, each row has D-1 free params)
    Means: K*D
    Variances: K*D (diagonal covariance)
    Initial: K-1
    """
    return K * (K - 1) + K * D + K * D + (K - 1)


def baum_welch(obs, K, n_iter=100, tol=1e-4, rng=None):
    """Train HMM with arbitrary K states.

    Uses k-means-style initialization: cluster observations by return,
    then use cluster centroids as initial means. This is more robust
    than quantile init when K > 3.
    """
    rng = rng or np.random.default_rng(42)
    T, D = obs.shape

    # Quantile-based init for means (simpler, more robust than k-means++)
    # Sort observations by return and assign buckets
    sorted_idx = np.argsort(return_col := obs[:, 0].copy())
    bucket_size = T // K
    means = np.zeros((K, D))
    for k in range(K):
        start = k * bucket_size
        end = (k + 1) * bucket_size if k < K - 1 else T
        means[k] = obs[sorted_idx[start:end]].mean(axis=0)

    # Sort by descending return so S0 = highest return state
    sort_idx = np.argsort(-means[:, 0])
    means = means[sort_idx]

    # Init variances
    vars_ = np.tile(np.var(obs, axis=0), (K, 1))
    for k in range(K):
        vars_[k] = np.var(obs - means[k], axis=0) + 1e-6
    vars_ = np.maximum(vars_, 1e-8)

    # Init transition: sticky (diagonal-heavy)
    A = np.full((K, K), 0.5 / K)
    np.fill_diagonal(A, 0.5 + 0.5 / K)
    A = A / A.sum(axis=1, keepdims=True)

    pi = np.ones(K) / K

    log_lls = []
    for iteration in range(n_iter):
        log_A = np.log(A + 1e-10)
        log_pi = np.log(pi + 1e-10)

        obs_log_prob = emission_log_prob(obs, means, vars_)
        log_alpha, log_Z = forward_alg(obs_log_prob, log_A, log_pi)
        log_beta = backward_alg(obs_log_prob, log_A, log_pi)

        log_lls.append(float(log_Z))
        if iteration > 0 and abs(log_lls[-1] - log_lls[-2]) < tol:
            break

        # gamma
        log_gamma = log_alpha + log_beta - log_Z
        gamma = np.exp(log_gamma)
        gamma = gamma / gamma.sum(axis=1, keepdims=True)

        # xi
        log_A_new = np.full((K, K), NEG_INF)
        for i in range(K):
            for j in range(K):
                for t in range(T - 1):
                    log_val = log_alpha[t, i] + log_A[i, j] + obs_log_prob[t + 1, j] + log_beta[t + 1, j]
                    log_A_new[i, j] = log_add(log_A_new[i, j], log_val)
                log_A_new[i, j] -= log_Z
        A = np.exp(log_A_new)
        A = A / A.sum(axis=1, keepdims=True)

        # Update means and vars
        for k in range(K):
            w = gamma[:, k]
            w_sum = w.sum()
            if w_sum > 1e-10:
                for d in range(D):
                    means[k, d] = np.sum(w * obs[:, d]) / w_sum
                    vars_[k, d] = np.sum(w * (obs[:, d] - means[k, d]) ** 2) / w_sum
                    vars_[k, d] = max(vars_[k, d], 1e-8)

        pi = gamma[0] / gamma[0].sum()

    return A, means, vars_, pi, log_lls


def prepare_observations(prices):
    """Same feature engineering as hmm_regime_detection.py."""
    n = len(prices)
    returns = np.zeros(n)
    returns[1:] = np.diff(prices) / prices[:-1]

    vol = np.zeros(n)
    for i in range(20, n):
        vol[i] = np.std(returns[i - 20:i])

    momentum = np.zeros(n)
    for i in range(10, n):
        momentum[i] = prices[i] / prices[i - 10] - 1.0

    obs = np.column_stack([returns, vol, momentum])
    obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
    return obs[20:]  # remove warmup


def model_selection(symbol, start="2024-01-01", end=None, n_seeds=3):
    """Run HMM model selection for a single asset.

    Runs each K with multiple random seeds and keeps the best (highest LogLL).
    Reports stability: std of LogLL across seeds indicates local optima risk.

    Returns dict with BIC/AIC per K, optimal K, and diagnostics.
    """
    end = end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end)
    if df.empty:
        print(f"No data for {symbol}")
        return None

    prices = df["Close"].values
    obs = prepare_observations(prices)
    T, D = obs.shape

    results = {
        "symbol": symbol,
        "n_observations": T,
        "n_features": D,
        "n_seeds": n_seeds,
        "models": {}
    }

    for K in range(2, 7):
        best_log_ll = -np.inf
        best_state = None
        log_lls_across_seeds = []

        for seed in range(n_seeds):
            rng = np.random.default_rng(seed)
            try:
                A, means, vars_, pi, log_lls = baum_welch(obs, K, rng=rng)
                ll = log_lls[-1]
                log_lls_across_seeds.append(ll)
                if ll > best_log_ll:
                    best_log_ll = ll
                    best_state = (A, means, vars_, pi, log_lls)
            except Exception:
                continue

        if best_state is None:
            continue

        A, means, vars_, pi, log_lls = best_state
        log_ll = best_log_ll
        n_params = count_params(K, D)

        aic = 2 * n_params - 2 * log_ll
        bic = n_params * np.log(T) - 2 * log_ll

        # Diagonal-ness of transition matrix (stickiness)
        stickiness = np.mean(np.diag(A))

        # Emission separation: min |mean_i - mean_j| / std for all pairs
        overall_std = np.std(obs[:, 0])
        separations = []
        for i in range(K):
            for j in range(i + 1, K):
                sep = abs(means[i, 0] - means[j, 0]) / overall_std
                separations.append(sep)
        min_separation = min(separations) if separations else 0

        stability = float(np.std(log_lls_across_seeds)) if len(log_lls_across_seeds) > 1 else 0.0

        results["models"][K] = {
            "log_likelihood": round(log_ll, 2),
            "n_params": n_params,
            "aic": round(aic, 2),
            "bic": round(bic, 2),
            "em_iterations": len(log_lls),
            "stickiness": round(stickiness, 4),
            "min_emission_separation_sigma": round(min_separation, 4),
            "stability_std": round(stability, 2),
            "means": {f"S{k}": round(float(means[k, 0]), 6) for k in range(K)},
            "diagonal": {f"S{k}": round(float(A[k, k]), 4) for k in range(K)}
        }

    # Find optimal K by BIC (lower is better)
    best_k_bic = min(results["models"], key=lambda k: results["models"][k]["bic"])
    best_k_aic = min(results["models"], key=lambda k: results["models"][k]["aic"])

    # BIC deltas: marginal improvement per added state
    sorted_Ks = sorted(results["models"])
    bic_deltas = {}
    for i in range(1, len(sorted_Ks)):
        K_prev, K_curr = sorted_Ks[i - 1], sorted_Ks[i]
        delta = results["models"][K_prev]["bic"] - results["models"][K_curr]["bic"]
        bic_deltas[K_curr] = round(delta, 2)
    results["bic_deltas"] = bic_deltas

    # Elbow: where delta per param starts diminishing
    # Simple heuristic: first K where delta/added_params < mean(delta/added_params)
    param_deltas = {}
    for K in bic_deltas:
        K_prev = K - 1
        added_params = results["models"][K]["n_params"] - results["models"][K_prev]["n_params"]
        param_deltas[K] = bic_deltas[K] / added_params if added_params > 0 else 0
    if param_deltas:
        avg_delta_per_param = np.mean(list(param_deltas.values()))
        elbow_k = None
        for K in sorted(param_deltas):
            if param_deltas[K] < avg_delta_per_param:
                elbow_k = K
                break
        results["elbow_k"] = elbow_k
        results["avg_delta_per_param"] = round(avg_delta_per_param, 2)

    results["optimal_k_bic"] = best_k_bic
    results["optimal_k_aic"] = best_k_aic

    return results


def main():
    parser = argparse.ArgumentParser(description="HMM Model Selection via BIC/AIC")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--all", action="store_true", dest="all_symbols")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    symbols = ["TSLA", "NVDA", "SPY", "AAPL"] if args.all_symbols else [args.symbol]
    if not args.symbol and not args.all_symbols:
        parser.error("Either --symbol or --all is required")

    all_results = {}
    for sym in symbols:
        print(f"=== {sym} ===")
        result = model_selection(sym, args.start, args.end)
        if result is None:
            continue

        all_results[sym] = result

        print(f"Observations: {result['n_observations']}, Features: {result['n_features']}, Seeds: {result.get('n_seeds', 1)}")
        print(f"{'K':>3} {'LogLL':>10} {'Params':>7} {'BIC':>12} {'ΔBIC':>8} {'Sticky':>7} {'Sep':>6} {'Stable':>7}")
        print("-" * 70)
        for K in sorted(result["models"]):
            m = result["models"][K]
            delta = result.get("bic_deltas", {}).get(K, "--")
            delta_str = f"{delta:>8.2f}" if isinstance(delta, float) else f"{'--':>8}"
            print(f"{K:>3} {m['log_likelihood']:>10.2f} {m['n_params']:>7} "
                  f"{m['bic']:>12.2f} {delta_str} {m['stickiness']:>7.4f} {m['min_emission_separation_sigma']:>6.4f} "
                  f"{m.get('stability_std', 'N/A'):>7.2f}")
        print("-" * 70)
        print(f"BIC optimal K: {result['optimal_k_bic']}")
        print(f"AIC optimal K: {result['optimal_k_aic']}")
        if "elbow_k" in result:
            print(f"BIC elbow K:   {result['elbow_k']} (avg ΔBIC/param: {result['avg_delta_per_param']})")
        print()

        # Means per state for optimal model
        opt = result["models"][result["optimal_k_bic"]]
        print(f"Optimal model (K={result['optimal_k_bic']}) state means:")
        for label, mean_ret in opt["means"].items():
            print(f"  {label}: {mean_ret:+.6f} ({mean_ret * 252 * 100:+.2f}% annualized)")
        print()

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        Path("reports").mkdir(exist_ok=True)
        with open("reports/hmm_model_selection.jsonl", "a") as f:
            for sym, result in all_results.items():
                f.write(json.dumps(result) + "\n")
        print(f"Results saved to reports/hmm_model_selection.jsonl")


if __name__ == "__main__":
    main()
