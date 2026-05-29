#!/usr/bin/env python3
"""Bayesian A/B Testing Tool

Applies the computational reasoning toolkit (C520-C525):
- Beta-Binomial conjugate model (C521: conjugate priors)
- Posterior predictive distributions (C521: Bayesian inference)
- KL divergence for effect size (C520: KL divergence)
- Model comparison via Bayes factors (C521: model comparison)
- MCMC fallback via Metropolis-Hastings (C525: HMC/NUTS simplified)

Usage:
    python3 bin/ab_test.py --successes-a 80 --trials-a 200 --successes-b 100 --trials-b 250
    python3 bin/ab_test.py --data experiments.csv  # columns: group,successes,trials
"""

import argparse
import json
import math
import random
import sys
from pathlib import Path


def beta_pdf(alpha, beta, x):
    """Beta PDF at x with parameters alpha, beta."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return math.exp(gamma_log_pdf(alpha, beta, x))


def gamma_log_pdf(alpha, beta, x):
    """Log of Beta PDF at x."""
    return (
        (alpha - 1) * math.log(x)
        + (beta - 1) * math.log(1 - x)
        - math.lgamma(alpha)
        - math.lgamma(beta)
        + math.lgamma(alpha + beta)
    )


def beta_mean(alpha, beta):
    return alpha / (alpha + beta)


def beta_variance(alpha, beta):
    return (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))


def beta_std(alpha, beta):
    return math.sqrt(beta_variance(alpha, beta))


def beta_cdf_approx(alpha, beta, x, samples=10000):
    """Approximate Beta CDF via Monte Carlo integration."""
    rng = random.Random(42)
    count = 0
    for _ in range(samples):
        sample = rng.betavariate(alpha, beta)
        if sample <= x:
            count += 1
    return count / samples


def credible_interval(alpha, beta, cred_level=0.95):
    """Compute credible interval via Monte Carlo sampling from posterior."""
    rng = random.Random(42)
    samples = [rng.betavariate(alpha, beta) for _ in range(50000)]
    samples.sort()
    lower_idx = int((1 - cred_level) / 2 * len(samples))
    upper_idx = int((1 + cred_level) / 2 * len(samples))
    return samples[lower_idx], samples[upper_idx]


def kl_divergence_beta(alpha_a, beta_a, alpha_b, beta_b, num_points=1000):
    """Approximate KL divergence between two Beta distributions via numerical integration.

    D_KL(p || q) = integral p(x) * log(p(x)/q(x)) dx
    where p = Beta(alpha_a, beta_a), q = Beta(alpha_b, beta_b)
    """
    total = 0.0
    for i in range(1, num_points):
        x = i / num_points
        log_p = gamma_log_pdf(alpha_a, beta_a, x)
        log_q = gamma_log_pdf(alpha_b, beta_b, x)
        p = math.exp(log_p)
        total += p * (log_p - log_q)
    return total / (num_points - 1)


def probability_a_greater_b(alpha_a, beta_a, alpha_b, beta_b, num_samples=50000):
    """P(A > B) via Monte Carlo sampling from both posteriors."""
    rng = random.Random(42)
    count = 0
    for _ in range(num_samples):
        a = rng.betavariate(alpha_a, beta_a)
        b = rng.betavariate(alpha_b, beta_b)
        if a > b:
            count += 1
    return count / num_samples


def expected_difference(alpha_a, beta_a, alpha_b, beta_b, num_samples=50000):
    """E[A - B] via Monte Carlo sampling."""
    rng = random.Random(42)
    total_diff = 0.0
    for _ in range(num_samples):
        a = rng.betavariate(alpha_a, beta_a)
        b = rng.betavariate(alpha_b, beta_b)
        total_diff += (a - b)
    return total_diff / num_samples


def mcmc_metropolis_hastings(successes, trials, alpha_prior=1, beta_prior=1,
                              num_samples=10000, burn_in=1000, step_size=0.01):
    """MCMC sampling via Metropolis-Hastings for the Beta-Binomial model.

    This is the simplified 1D version of what HMC/NUTS does in Stan/PyMC (C525).
    In 1D, MH is adequate. In higher dimensions, HMC uses gradient information
    to propose moves — MH uses blind random walks.

    Target: p(theta | data) proportional to theta^successes * (1-theta)^(trials-successes) * Beta(theta; alpha, beta)
    """
    # Log posterior (unnormalized)
    failures = trials - successes

    def log_posterior(theta):
        if theta <= 0 or theta >= 1:
            return -math.inf
        return (
            (successes + alpha_prior - 1) * math.log(theta)
            + (failures + beta_prior - 1) * math.log(1 - theta)
        )

    # Initialize
    theta = beta_mean(alpha_prior + successes, beta_prior + failures)
    samples = []
    accepted = 0

    for i in range(burn_in + num_samples):
        # Proposal: random walk with normal step
        theta_prop = theta + random.gauss(0, step_size)
        if 0 < theta_prop < 1:
            log_alpha = log_posterior(theta_prop) - log_posterior(theta)
            if math.log(random.random()) < log_alpha:
                theta = theta_prop
                if i >= burn_in:
                    accepted += 1

        if i >= burn_in:
            samples.append(theta)

    acceptance_rate = accepted / num_samples
    return samples, acceptance_rate


def bayes_factor_1sided(successes_a, trials_a, successes_b, trials_b):
    """Approximate Bayes factor for H1: A > B vs H0: A = B.

    Uses the ratio of marginal likelihoods under the Beta-Binomial model.
    BF > 1 favors H1 (A > B), BF < 1 favors H0 (no difference).

    Approximation: compare posterior odds to prior odds.
    """
    # Prior: uniform Beta(1,1) for both — prior odds = 0.5 (symmetric)
    # Posterior: Beta(successes+1, failures+1)
    alpha_a, beta_a = successes_a + 1, trials_a - successes_a + 1
    alpha_b, beta_b = successes_b + 1, trials_b - successes_b + 1

    # Probability A > B under posterior
    p_a_gt_b = probability_a_greater_b(alpha_a, beta_a, alpha_b, beta_b)

    # Bayes factor = posterior odds / prior odds
    # Prior odds = 0.5 (symmetric prior)
    posterior_odds = p_a_gt_b / (1 - p_a_gt_b) if p_a_gt_b < 1 else float('inf')
    bf = posterior_odds / 1.0  # prior odds = 1 for symmetric

    return bf


def interpret_bayes_factor(bf):
    """Interpret Bayes factor strength (Kass & Raftery 1995)."""
    if bf < 1:
        for threshold, label in [(0.1, "Very strong evidence for H0 (no difference)"),
                                  (0.25, "Strong evidence for H0"),
                                  (0.5, "Positive evidence for H0")]:
            if bf <= threshold:
                return label
        return "Anecdotal evidence for H0"
    else:
        for threshold, label in [(100, "Decisive evidence for H1 (A > B)"),
                                  (10, "Very strong evidence for H1"),
                                  (6, "Strong evidence for H1"),
                                  (2, "Positive evidence for H1")]:
            if bf >= threshold:
                return label
        return "Anecdotal evidence for H1"


def run_bayesian_ab_test(successes_a, trials_a, successes_b, trials_b,
                          alpha_prior=1, beta_prior=1, use_mcmc=False):
    """Run a complete Bayesian A/B test analysis.

    Args:
        successes_a, trials_a: Group A conversion data
        successes_b, trials_b: Group B conversion data
        alpha_prior, beta_prior: Beta prior parameters (default: uniform prior)
        use_mcmc: If True, use MCMC sampling; otherwise use conjugate analytic solution

    Returns:
        dict with posterior parameters, probabilities, and effect sizes
    """
    alpha_a = alpha_prior + successes_a
    beta_a = beta_prior + (trials_a - successes_a)
    alpha_b = alpha_prior + successes_b
    beta_b = beta_prior + (trials_b - successes_b)

    rate_a = successes_a / trials_a if trials_a > 0 else 0
    rate_b = successes_b / trials_b if trials_b > 0 else 0

    # Posterior summaries
    posterior = {
        "group_a": {
            "alpha": alpha_a,
            "beta": beta_a,
            "mean": beta_mean(alpha_a, beta_a),
            "std": beta_std(alpha_a, beta_a),
            "observed_rate": rate_a,
            "ci_95": list(credible_interval(alpha_a, beta_a, 0.95)),
        },
        "group_b": {
            "alpha": alpha_b,
            "beta": beta_b,
            "mean": beta_mean(alpha_b, beta_b),
            "std": beta_std(alpha_b, beta_b),
            "observed_rate": rate_b,
            "ci_95": list(credible_interval(alpha_b, beta_b, 0.95)),
        },
    }

    # Decision metrics
    p_a_gt_b = probability_a_greater_b(alpha_a, beta_a, alpha_b, beta_b)
    expected_diff = expected_difference(alpha_a, beta_a, alpha_b, beta_b)

    # KL divergence: how different are the posteriors?
    kl_a_b = kl_divergence_beta(alpha_a, beta_a, alpha_b, beta_b)
    kl_b_a = kl_divergence_beta(alpha_b, beta_b, alpha_a, beta_a)
    jensen_shannon = math.sqrt((kl_a_b + kl_b_a) / 2)  # Symmetrized, sqrt for metric

    # Bayes factor
    bf = bayes_factor_1sided(successes_a, trials_a, successes_b, trials_b)

    # MCMC diagnostics (if requested)
    mcmc_diagnostics = None
    if use_mcmc:
        mcmc_a, accept_a = mcmc_metropolis_hastings(successes_a, trials_a, alpha_prior, beta_prior)
        mcmc_b, accept_b = mcmc_metropolis_hastings(successes_b, trials_b, alpha_prior, beta_prior)
        mcmc_mean_a = sum(mcmc_a) / len(mcmc_a)
        mcmc_mean_b = sum(mcmc_b) / len(mcmc_b)
        mcmc_diagnostics = {
            "acceptance_rate_a": round(accept_a, 3),
            "acceptance_rate_b": round(accept_b, 3),
            "mcmc_mean_a": round(mcmc_mean_a, 6),
            "mcmc_mean_b": round(mcmc_mean_b, 6),
            "analytic_mean_a": round(beta_mean(alpha_a, beta_a), 6),
            "analytic_mean_b": round(beta_mean(alpha_b, beta_b), 6),
            "mcmc_matches_analytic": abs(mcmc_mean_a - beta_mean(alpha_a, beta_a)) < 0.001
                                     and abs(mcmc_mean_b - beta_mean(alpha_b, beta_b)) < 0.001,
        }

    result = {
        "posterior": posterior,
        "decision": {
            "p_a_greater_b": round(p_a_gt_b, 4),
            "p_b_greater_a": round(1 - p_a_gt_b, 4),
            "expected_difference": round(expected_diff, 4),
            "winner": "A" if p_a_gt_b > 0.5 else "B",
            "confidence": max(p_a_gt_b, 1 - p_a_gt_b),
        },
        "effect_size": {
            "kl_divergence_a_to_b": round(kl_a_b, 6),
            "kl_divergence_b_to_a": round(kl_b_a, 6),
            "jensen_shannon_distance": round(jensen_shannon, 6),
        },
        "bayes_factor": round(bf, 2),
        "bayes_factor_interpretation": interpret_bayes_factor(bf),
    }

    if mcmc_diagnostics:
        result["mcmc_diagnostics"] = mcmc_diagnostics

    return result


def format_report(result):
    """Format analysis result as a human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("BAYESIAN A/B TEST RESULTS")
    lines.append("=" * 60)

    for group in ["group_a", "group_b"]:
        label = group.replace("_", " ").upper()
        p = result["posterior"][group]
        lines.append(f"\n{label}:")
        lines.append(f"  Observed rate: {p['observed_rate']:.4f} ({p['alpha']}/{p['alpha']+p['beta']-2})")
        lines.append(f"  Posterior mean: {p['mean']:.4f} +/- {p['std']:.4f}")
        lines.append(f"  95% CI: [{p['ci_95'][0]:.4f}, {p['ci_95'][1]:.4f}]")

    d = result["decision"]
    lines.append(f"\nDECISION:")
    lines.append(f"  P(A > B): {d['p_a_greater_b']:.2%}")
    lines.append(f"  P(B > A): {d['p_b_greater_a']:.2%}")
    lines.append(f"  Expected difference: {d['expected_difference']:+.4f}")
    lines.append(f"  Winner: {d['winner']} (confidence: {d['confidence']:.2%})")

    es = result["effect_size"]
    lines.append(f"\nEFFECT SIZE:")
    lines.append(f"  KL(A||B): {es['kl_divergence_a_to_b']:.6f}")
    lines.append(f"  KL(B||A): {es['kl_divergence_b_to_a']:.6f}")
    lines.append(f"  Jensen-Shannon distance: {es['jensen_shannon_distance']:.6f}")

    lines.append(f"\nMODEL COMPARISON:")
    lines.append(f"  Bayes factor: {result['bayes_factor']:.2f}")
    lines.append(f"  {result['bayes_factor_interpretation']}")

    if result.get("mcmc_diagnostics"):
        m = result["mcmc_diagnostics"]
        lines.append(f"\nMCMC DIAGNOSTICS:")
        lines.append(f"  Acceptance rate A: {m['acceptance_rate_a']:.1%}")
        lines.append(f"  Acceptance rate B: {m['acceptance_rate_b']:.1%}")
        lines.append(f"  MCMC matches analytic: {m['mcmc_matches_analytic']}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Bayesian A/B Testing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple A/B test
  python3 bin/ab_test.py --successes-a 80 --trials-a 200 --successes-b 100 --trials-b 250

  # With MCMC diagnostics
  python3 bin/ab_test.py --successes-a 80 --trials-a 200 --successes-b 100 --trials-b 250 --mcmc

  # Custom prior (informative: expect ~10% conversion)
  python3 bin/ab_test.py --successes-a 8 --trials-a 100 --successes-b 12 --trials-b 100 --alpha 2 --beta 18

  # JSON output for programmatic use
  python3 bin/ab_test.py --successes-a 80 --trials-a 200 --successes-b 100 --trials-b 250 --json
        """
    )
    parser.add_argument("--successes-a", type=int, help="Number of successes in group A")
    parser.add_argument("--trials-a", type=int, help="Total trials in group A")
    parser.add_argument("--successes-b", type=int, help="Number of successes in group B")
    parser.add_argument("--trials-b", type=int, help="Total trials in group B")
    parser.add_argument("--alpha", type=float, default=1, help="Beta prior alpha (default: 1, uniform)")
    parser.add_argument("--beta", type=float, default=1, help="Beta prior beta (default: 1, uniform)")
    parser.add_argument("--mcmc", action="store_true", help="Include MCMC diagnostics")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if None in [args.successes_a, args.trials_a, args.successes_b, args.trials_b]:
        parser.error("All four arguments required: --successes-a, --trials-a, --successes-b, --trials-b")

    if args.successes_a > args.trials_a or args.successes_b > args.trials_b:
        parser.error("Successes cannot exceed trials")

    result = run_bayesian_ab_test(
        args.successes_a, args.trials_a,
        args.successes_b, args.trials_b,
        args.alpha, args.beta,
        args.mcmc
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))


if __name__ == "__main__":
    main()
