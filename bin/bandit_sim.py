#!/usr/bin/env python3
"""Multi-Armed Bandit Simulator

Benchmarks exploration-exploitation strategies against a configurable bandit
environment. Applies the C527 exploration-exploitation toolkit:
- epsilon-greedy (naive exploration)
- UCB1 (deterministic confidence-bound exploration)
- Thompson Sampling (Bayesian probability matching)

Usage:
    # Default 3-arm bandit, 1000 pulls
    python3 bin/bandit_sim.py

    # Custom arm means (Bernoulli rewards)
    python3 bin/bandit_sim.py --arm-means 0.1 0.3 0.5 0.2

    # Gaussian rewards with known variance
    python3 bin/bandit_sim.py --arm-means 0.2 0.4 0.3 --reward-type gaussian --sigma 0.1

    # Compare strategies over 5000 pulls with 5 arms
    python3 bin/bandit_sim.py --arm-means 0.1 0.2 0.3 0.4 0.5 --pulls 5000

    # JSON output for programmatic use
    python3 bin/bandit_sim.py --arm-means 0.3 0.5 0.4 --json

    # Seed for reproducibility
    python3 bin/bandit_sim.py --arm-means 0.3 0.5 0.4 --seed 42
"""

import argparse
import json
import math
import random
import sys
from collections import defaultdict


def bernoulli_reward(mean, rng):
    """Sample a Bernoulli reward with given mean."""
    return 1.0 if rng.random() < mean else 0.0


def gaussian_reward(mean, sigma, rng):
    """Sample a Gaussian reward with given mean and standard deviation."""
    return rng.gauss(mean, sigma)


class BanditEnvironment:
    """Multi-armed bandit environment with configurable reward distributions."""

    def __init__(self, arm_means, reward_type="bernoulli", sigma=0.1, rng=None):
        """
        Args:
            arm_means: List of true mean rewards for each arm.
            reward_type: "bernoulli" or "gaussian".
            sigma: Standard deviation for Gaussian rewards.
            rng: Random number generator instance.
        """
        self.arm_means = list(arm_means)
        self.reward_type = reward_type
        self.sigma = sigma
        self.rng = rng or random.Random()
        self.num_arms = len(arm_means)
        self.total_pulls = 0
        self.arm_pull_counts = [0] * self.num_arms

    def pull(self, arm_index):
        """Pull an arm and return the reward."""
        if arm_index < 0 or arm_index >= self.num_arms:
            raise ValueError(f"Arm index {arm_index} out of range [0, {self.num_arms - 1}]")

        mean = self.arm_means[arm_index]
        if self.reward_type == "bernoulli":
            reward = bernoulli_reward(mean, self.rng)
        else:
            reward = gaussian_reward(mean, self.sigma, self.rng)

        self.arm_pull_counts[arm_index] += 1
        self.total_pulls += 1
        return reward

    def optimal_mean(self):
        """Return the mean of the best arm."""
        return max(self.arm_means)


class EpsilonGreedy:
    """Epsilon-greedy strategy: explore with probability epsilon, exploit otherwise."""

    def __init__(self, num_arms, epsilon=0.1, rng=None):
        self.num_arms = num_arms
        self.epsilon = epsilon
        self.rng = rng or random.Random()
        self.total_rewards = [0.0] * num_arms
        self.counts = [0] * num_arms

    def select_action(self):
        if self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.num_arms - 1)
        # If no arms tried yet, pick randomly (forced exploration)
        if sum(self.counts) == 0:
            return self.rng.randint(0, self.num_arms - 1)
        averages = [self.total_rewards[i] / max(self.counts[i], 1)
                    for i in range(self.num_arms)]
        best_value = max(averages)
        best_arms = [i for i in range(self.num_arms) if abs(averages[i] - best_value) < 1e-10]
        return self.rng.choice(best_arms)

    def update(self, arm, reward):
        self.total_rewards[arm] += reward
        self.counts[arm] += 1


class UCB1:
    """Upper Confidence Bound strategy: explore uncertain arms proportionally."""

    def __init__(self, num_arms, rng=None):
        self.num_arms = num_arms
        self.rng = rng or random.Random()
        self.total_rewards = [0.0] * num_arms
        self.counts = [0] * num_arms
        self.total_pulls = 0

    def select_action(self):
        # Force exploration of untried arms first (round-robin among untried)
        untried = [i for i in range(self.num_arms) if self.counts[i] == 0]
        if untried:
            return self.rng.choice(untried)

        total = self.total_pulls
        ucb_values = []
        for i in range(self.num_arms):
            avg = self.total_rewards[i] / self.counts[i]
            bonus = math.sqrt(2 * math.log(total) / self.counts[i])
            ucb_values.append(avg + bonus)

        best_value = max(ucb_values)
        best_arms = [i for i in range(self.num_arms) if abs(ucb_values[i] - best_value) < 1e-10]
        return self.rng.choice(best_arms)

    def update(self, arm, reward):
        self.total_rewards[arm] += reward
        self.counts[arm] += 1
        self.total_pulls += 1


class ThompsonSampling:
    """Thompson Sampling: Bayesian probability matching for Bernoulli rewards.

    Maintains a Beta(alpha, beta) posterior for each arm. At each step, samples
    from each posterior and selects the arm with the highest sample. For Gaussian
    rewards, uses a Normal-Gamma conjugate approximation.
    """

    def __init__(self, num_arms, reward_type="bernoulli", rng=None):
        self.num_arms = num_arms
        self.reward_type = reward_type
        self.rng = rng or random.Random()

        if reward_type == "bernoulli":
            # Beta prior: uniform Beta(1, 1)
            self.alpha = [1.0] * num_arms
            self.beta = [1.0] * num_arms
        else:
            # Normal-inverse-gamma conjugate model for Gaussian rewards
            # Prior: mu ~ N(mu_0, sigma^2 / kappa_0), sigma^2 ~ Inv-Gamma(alpha_0, beta_0)
            # Marginal posterior for mu is Student's t — approximated as Normal
            self.mu_0 = 0.0
            self.kappa_0 = 1.0  # prior sample weight
            self.alpha_0 = 2.0  # prior degrees of freedom / 2
            self.beta_0 = 0.5   # prior scale
            # Running stats per arm
            self.sums = [0.0] * num_arms
            self.sum_squares = [0.0] * num_arms
            self.counts = [0] * num_arms

    def select_action(self):
        if self.reward_type == "bernoulli":
            samples = [self.rng.betavariate(self.alpha[i], self.beta[i])
                       for i in range(self.num_arms)]
        else:
            samples = []
            for i in range(self.num_arms):
                n = self.counts[i]
                if n == 0:
                    # Prior sample: wide uncertainty
                    samples.append(self.rng.gauss(self.mu_0, 1.0))
                    continue
                # Posterior parameters (Normal-inverse-gamma update)
                kappa_n = self.kappa_0 + n
                mu_n = (self.kappa_0 * self.mu_0 + n * (self.sums[i] / n)) / kappa_n
                sample_var = (self.sum_squares[i] - n * (self.sums[i] / n) ** 2) / max(n - 1, 1)
                sigma_sq_n = (2 * self.beta_0 + n * sample_var) / (2 * self.alpha_0 + n - 1)
                # Posterior variance of mu: sigma^2 / kappa_n
                posterior_var = sigma_sq_n / kappa_n
                samples.append(self.rng.gauss(mu_n, math.sqrt(posterior_var)))

        best_value = max(samples)
        best_arms = [i for i in range(self.num_arms) if abs(samples[i] - best_value) < 1e-10]
        return self.rng.choice(best_arms)

    def update(self, arm, reward):
        if self.reward_type == "bernoulli":
            if reward > 0:
                self.alpha[arm] += reward
            else:
                self.beta[arm] += 1 - reward
        else:
            self.counts[arm] += 1
            self.sums[arm] += reward
            self.sum_squares[arm] += reward * reward


def run_simulation(env, strategy, num_pulls):
    """Run a bandit simulation and track cumulative regret."""
    optimal = env.optimal_mean()
    cumulative_reward = 0.0
    cumulative_regret = 0.0
    regret_history = []
    arm_selections = defaultdict(int)

    for _ in range(num_pulls):
        arm = strategy.select_action()
        reward = env.pull(arm)
        strategy.update(arm, reward)

        cumulative_reward += reward
        cumulative_regret += (optimal - env.arm_means[arm])
        arm_selections[arm] += 1
        regret_history.append(cumulative_regret)

    return {
        "cumulative_reward": round(cumulative_reward, 4),
        "cumulative_regret": round(cumulative_regret, 4),
        "average_regret": round(cumulative_regret / num_pulls, 6),
        "arm_selections": dict(arm_selections),
        "regret_history": regret_history,
    }


def format_report(results, arm_means, num_pulls):
    """Format simulation results as a human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("MULTI-ARMED BANDIT SIMULATION RESULTS")
    lines.append("=" * 60)
    lines.append(f"Arms: {len(arm_means)} | Pulls: {num_pulls}")
    lines.append(f"True means: {', '.join(f'{m:.3f}' for m in arm_means)}")
    lines.append(f"Optimal arm mean: {max(arm_means):.3f}")
    lines.append("")

    for name, result in results.items():
        lines.append(f"--- {name} ---")
        lines.append(f"  Cumulative reward: {result['cumulative_reward']:.2f}")
        lines.append(f"  Cumulative regret: {result['cumulative_regret']:.2f}")
        lines.append(f"  Average regret/pull: {result['average_regret']:.4f}")
        lines.append(f"  Arm selections:")
        for arm_idx in sorted(result["arm_selections"].keys()):
            count = result["arm_selections"][arm_idx]
            pct = count / num_pulls * 100
            true_mean = arm_means[arm_idx] if arm_idx < len(arm_means) else "?"
            lines.append(f"    Arm {arm_idx} (mean={true_mean}): {count} pulls ({pct:.1f}%)")
        lines.append("")

    # Regret progression at key checkpoints
    lines.append("Regret progression (checkpoints):")
    checkpoints = [0.1, 0.25, 0.5, 0.75, 1.0]
    header = "  Strategy" + "".join(f"  @{int(cp*num_pulls):>8}" for cp in checkpoints)
    lines.append(header)

    for name, result in results.items():
        row = f"  {name}"
        history = result["regret_history"]
        for cp in checkpoints:
            idx = int(cp * num_pulls) - 1
            if idx < 0:
                idx = 0
            idx = min(idx, len(history) - 1)
            row += f"{history[idx]:>8.2f}"
        lines.append(row)

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Armed Bandit Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default simulation
  python3 bin/bandit_sim.py

  # Custom arm means
  python3 bin/bandit_sim.py --arm-means 0.1 0.3 0.5 0.2

  # Gaussian rewards
  python3 bin/bandit_sim.py --arm-means 0.2 0.4 0.3 --reward-type gaussian

  # More pulls, seeded for reproducibility
  python3 bin/bandit_sim.py --arm-means 0.3 0.5 0.4 --pulls 5000 --seed 42

  # JSON output
  python3 bin/bandit_sim.py --arm-means 0.3 0.5 0.4 --json
        """
    )
    parser.add_argument("--arm-means", type=float, nargs="+",
                        default=[0.2, 0.4, 0.6],
                        help="True mean reward for each arm (default: 0.2 0.4 0.6)")
    parser.add_argument("--pulls", type=int, default=1000,
                        help="Number of pulls per strategy (default: 1000)")
    parser.add_argument("--epsilon", type=float, default=0.1,
                        help="Epsilon for epsilon-greedy (default: 0.1)")
    parser.add_argument("--reward-type", choices=["bernoulli", "gaussian"],
                        default="bernoulli",
                        help="Reward distribution type (default: bernoulli)")
    parser.add_argument("--sigma", type=float, default=0.1,
                        help="Standard deviation for Gaussian rewards (default: 0.1)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--strategies", nargs="+",
                        choices=["epsilon-greedy", "ucb1", "thompson"],
                        default=["epsilon-greedy", "ucb1", "thompson"],
                        help="Strategies to benchmark (default: all)")

    args = parser.parse_args()

    if len(args.arm_means) < 2:
        parser.error("At least 2 arms required")

    rng = random.Random(args.seed)

    env = BanditEnvironment(
        arm_means=args.arm_means,
        reward_type=args.reward_type,
        sigma=args.sigma,
        rng=rng,
    )

    results = {}

    if "epsilon-greedy" in args.strategies:
        eg = EpsilonGreedy(len(args.arm_means), epsilon=args.epsilon, rng=random.Random(args.seed))
        results["epsilon-greedy"] = run_simulation(env, eg, args.pulls)

    if "ucb1" in args.strategies:
        ucb = UCB1(len(args.arm_means), rng=random.Random(args.seed))
        results["ucb1"] = run_simulation(env, ucb, args.pulls)

    if "thompson" in args.strategies:
        ts = ThompsonSampling(len(args.arm_means), reward_type=args.reward_type,
                              rng=random.Random(args.seed))
        results["thompson"] = run_simulation(env, ts, args.pulls)

    if args.json:
        output = {
            "config": {
                "arm_means": args.arm_means,
                "pulls": args.pulls,
                "epsilon": args.epsilon,
                "reward_type": args.reward_type,
                "sigma": args.sigma,
                "seed": args.seed,
            },
            "results": {},
        }
        for name, result in results.items():
            # Exclude regret_history from JSON to keep output manageable
            output["results"][name] = {
                k: v for k, v in result.items() if k != "regret_history"
            }
            # Add regret at checkpoints
            history = result["regret_history"]
            checkpoints = {}
            for cp_label, cp in [("10pct", 0.1), ("25pct", 0.25),
                                  ("50pct", 0.5), ("75pct", 0.75), ("100pct", 1.0)]:
                idx = min(int(cp * args.pulls) - 1, len(history) - 1)
                idx = max(idx, 0)
                checkpoints[cp_label] = round(history[idx], 4)
            output["results"][name]["regret_checkpoints"] = checkpoints

        print(json.dumps(output, indent=2))
    else:
        print(format_report(results, args.arm_means, args.pulls))


if __name__ == "__main__":
    main()
