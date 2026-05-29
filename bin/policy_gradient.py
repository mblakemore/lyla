#!/usr/bin/env python3
"""Policy Gradient Methods — REINFORCE, REINFORCE+Baseline, Actor-Critic

Demonstrates policy gradient methods on a MountainCar-like environment.
Applies the C527 RL toolkit: policy gradient theorem, advantage functions,
and actor-critic architecture.

Compares three variants:
  1. REINFORCE — Monte Carlo policy gradient (high variance)
  2. REINFORCE+Baseline — subtracts state value to reduce variance
  3. Actor-Critic — TD error as advantage estimate (lowest variance)

Usage:
    python3 bin/policy_gradient.py
    python3 bin/policy_gradient.py --episodes 1000
    python3 bin/policy_gradient.py --json
"""

import argparse
import json
import math
import random
import sys
from collections import defaultdict


class MountainCar:
    """MountainCar environment — learn to escape a valley.

    The car must build momentum by oscillating back and forth to reach
    the goal at the right hill. State: (position, velocity). Actions:
    reverse (0), wait (1), forward (2).
    """

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.position = 0.0
        self.velocity = 0.0
        self.goal = 0.9
        self.min_pos = -1.2
        self.max_pos = 1.1
        self.action_names = {0: "reverse", 1: "wait", 2: "forward"}
        self.steps = 0

    def reset(self):
        self.position = self.rng.uniform(-0.6, -0.4)
        self.velocity = 0.0
        self.steps = 0
        return self._state()

    def _state(self):
        return (self.position, self.velocity)

    def step(self, action):
        force = {0: -0.02, 1: 0.0, 2: 0.02}[action]
        gravity = -0.0025 * math.cos(3 * self.position)
        self.velocity += force + gravity - 0.05 * self.velocity
        self.velocity = max(-0.2, min(0.2, self.velocity))
        self.position += self.velocity
        self.position = max(self.min_pos, min(self.max_pos, self.position))
        self.steps += 1

        reward = -1.0
        done = False
        if self.position >= self.goal:
            reward = 0.0
            done = True
        elif self.position <= self.min_pos and self.velocity < 0:
            self.velocity = 0.0

        return self._state(), reward, done, self.steps


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    else:
        ex = math.exp(x)
        return ex / (1.0 + ex)


class LinearPolicy:
    """Softmax policy: pi(a|s) = exp(w_a . s) / sum_b exp(w_b . s).

    Uses linear features: [1, position, velocity] for each action.
    """

    def __init__(self, num_actions, rng=None):
        self.num_actions = num_actions
        self.rng = rng or random.Random()
        self.num_features = 3
        self.weights = [
            [self.rng.gauss(0, 0.1) for _ in range(self.num_features)]
            for _ in range(num_actions)
        ]

    def _features(self, state):
        pos, vel = state
        return [1.0, pos, vel]

    def action_probs(self, state):
        features = self._features(state)
        logits = []
        for a in range(self.num_actions):
            logit = sum(self.weights[a][f] * features[f]
                        for f in range(self.num_features))
            logits.append(logit)

        max_logit = max(logits)
        exps = [math.exp(l - max_logit) for l in logits]
        total = sum(exps)
        return [e / total for e in exps]

    def select_action(self, state):
        probs = self.action_probs(state)
        r = self.rng.random()
        cumulative = 0.0
        for a, p in enumerate(probs):
            cumulative += p
            if r < cumulative:
                return a
        return self.num_actions - 1

    def log_prob_gradient(self, state, action):
        """Gradient of log pi(a|s) w.r.t. weights[action].

        d/dw_a [log pi(a|s)] = features * (1 - pi(a|s))
        """
        probs = self.action_probs(state)
        features = self._features(state)
        grad = [0.0] * self.num_features
        for f in range(self.num_features):
            grad[f] = features[f] * (1.0 - probs[action])
        return grad

    def copy(self):
        new = LinearPolicy(self.num_actions, self.rng)
        new.weights = [w[:] for w in self.weights]
        return new


class LinearValue:
    """Linear value function: V(s) = w . features(s)."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.num_features = 3
        self.weights = [self.rng.gauss(0, 0.1) for _ in range(self.num_features)]

    def _features(self, state):
        pos, vel = state
        return [1.0, pos, vel]

    def predict(self, state):
        features = self._features(state)
        return sum(self.weights[f] * features[f] for f in range(self.num_features))

    def update(self, state, target, lr=0.01):
        features = self._features(state)
        error = target - self.predict(state)
        for f in range(self.num_features):
            self.weights[f] += lr * error * features[f]
        return error


def rollout(env, agent, max_steps=200):
    """Run one episode, return list of (state, action, reward)."""
    state = env.reset()
    trajectory = []
    total_reward = 0.0
    done = False

    while not done:
        action = agent.select_action(state)
        next_state, reward, done, steps = env.step(action)
        trajectory.append((state, action, reward))
        total_reward += reward
        state = next_state
        if steps >= max_steps:
            break

    return trajectory, total_reward


def reinforce(env, agent, num_episodes, lr=0.1, gamma=0.99, seed=None):
    """REINFORCE: Monte Carlo policy gradient.

    theta <- theta + lr * sum_t G_t * grad_log_pi(a_t|s_t)

    Uses normalized returns (subtract mean, divide by std) to improve
    stability — this is the standard REINFORCE implementation. The
    variance reduction here comes from return normalization, not from
    a learned baseline.
    """
    episode_rewards = []
    avg_rewards = []
    window = 20

    for episode in range(num_episodes):
        trajectory, total_reward = rollout(env, agent, max_steps=200)
        episode_rewards.append(total_reward)

        if len(episode_rewards) % window == 0:
            avg_rewards.append(sum(episode_rewards[-window:]) / window)

        # Compute discounted returns
        returns = []
        G = 0.0
        for t in reversed(range(len(trajectory))):
            _, _, reward = trajectory[t]
            G = reward + gamma * G
            returns.insert(0, G)

        # Normalize returns within this episode for stability
        if len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns) + 1e-8)
            normalized = [(r - mean_r) / std_r for r in returns]
        else:
            normalized = returns

        for t in range(len(trajectory)):
            state, action, _ = trajectory[t]
            grad = agent.log_prob_gradient(state, action)
            for f in range(agent.num_features):
                agent.weights[action][f] += lr * normalized[t] * grad[f]

    return {
        "episode_rewards": episode_rewards,
        "avg_rewards": avg_rewards,
        "final_avg": sum(episode_rewards[-window:]) / min(window, len(episode_rewards)),
    }


def reinforce_baseline(env, agent, num_episodes, lr=0.05, v_lr=0.01,
                        gamma=0.99, seed=None):
    """REINFORCE with learned baseline.

    theta <- theta + lr * sum_t (G_t - V(s_t)) * grad_log_pi(a_t|s_t)
    V(s) <- V(s) + v_lr * (G_t - V(s_t))

    The baseline V(s) reduces variance without introducing bias.
    """
    value = LinearValue(random.Random(seed))
    episode_rewards = []
    avg_rewards = []
    window = 20

    for episode in range(num_episodes):
        trajectory, total_reward = rollout(env, agent, max_steps=200)
        episode_rewards.append(total_reward)

        if len(episode_rewards) % window == 0:
            avg_rewards.append(sum(episode_rewards[-window:]) / window)

        # Compute discounted returns
        returns = []
        G = 0.0
        for t in reversed(range(len(trajectory))):
            _, _, reward = trajectory[t]
            G = reward + gamma * G
            returns.insert(0, G)

        for t in range(len(trajectory)):
            state, action, _ = trajectory[t]
            G_t = returns[t]
            v_s = value.predict(state)
            advantage = G_t - v_s

            grad = agent.log_prob_gradient(state, action)
            for f in range(agent.num_features):
                agent.weights[action][f] += lr * advantage * grad[f]

            value.update(state, G_t, v_lr)

    return {
        "episode_rewards": episode_rewards,
        "avg_rewards": avg_rewards,
        "final_avg": sum(episode_rewards[-window:]) / min(window, len(episode_rewards)),
    }


def actor_critic(env, agent, num_episodes, lr=0.01, v_lr=0.01,
                  gamma=0.99, seed=None):
    """Actor-Critic: TD error as advantage estimate.

    delta_t = R_t + gamma * V(s') - V(s)
    theta <- theta + lr * delta_t * grad_log_pi(a_t|s_t)
    phi <- phi + v_lr * delta_t * features(s)

    Updates online — no need to wait for episode end.
    """
    value = LinearValue(random.Random(seed))
    episode_rewards = []
    avg_rewards = []
    window = 20

    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < 200:
            action = agent.select_action(state)
            next_state, reward, done, steps = env.step(action)
            total_reward += reward

            v_s = value.predict(state)
            v_next = value.predict(next_state)
            td_error = reward + gamma * v_next - v_s

            grad = agent.log_prob_gradient(state, action)
            for f in range(agent.num_features):
                agent.weights[action][f] += lr * td_error * grad[f]

            # Update critic: V(s) <- V(s) + v_lr * td_error * features(s)
            features = [1.0, state[0], state[1]]
            for f in range(value.num_features):
                value.weights[f] += v_lr * td_error * features[f]

            state = next_state

        episode_rewards.append(total_reward)

        if len(episode_rewards) % window == 0:
            avg_rewards.append(sum(episode_rewards[-window:]) / window)

    return {
        "episode_rewards": episode_rewards,
        "avg_rewards": avg_rewards,
        "final_avg": sum(episode_rewards[-window:]) / min(window, len(episode_rewards)),
    }


def compute_stats(rewards, window=20):
    """Compute learning curve checkpoints and variance stats."""
    n = len(rewards)
    checkpoints = {}
    for cp in [0.1, 0.3, 0.5, 0.7, 1.0]:
        idx = int(cp * n)
        slice_ = rewards[max(0, idx - window + 1):idx + 1]
        checkpoints[f"{int(cp*100)}pct"] = round(sum(slice_) / len(slice_), 2)

    # Variance of rewards at different checkpoints (shows variance reduction)
    variance_checkpoints = {}
    for cp in [0.5, 1.0]:
        idx = int(cp * n)
        slice_ = rewards[max(0, idx - window * 5 + 1):idx + 1]
        mean_ = sum(slice_) / len(slice_)
        var_ = sum((r - mean_) ** 2 for r in slice_) / len(slice_)
        variance_checkpoints[f"{int(cp*100)}pct_var"] = round(var_, 1)

    return checkpoints, variance_checkpoints


def format_report(results):
    """Format comparison report."""
    lines = []
    lines.append("=" * 60)
    lines.append("POLICY GRADIENT COMPARISON — MountainCar")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Methods compared:")
    lines.append("  1. REINFORCE        — Monte Carlo policy gradient")
    lines.append("  2. REINFORCE+Base   — REINFORCE with learned value baseline")
    lines.append("  3. Actor-Critic     — TD error as advantage (online update)")
    lines.append("")

    for name, stats in results.items():
        rewards = stats["episode_rewards"]
        final_avg = stats["final_avg"]
        best = max(rewards)
        worst = min(rewards)
        checkpoints, var_checkpoints = compute_stats(rewards)

        lines.append(f"--- {name} ---")
        lines.append(f"  Final avg reward (last 20): {final_avg:.1f}")
        lines.append(f"  Best episode: {best:.1f}")
        lines.append(f"  Worst episode: {worst:.1f}")
        lines.append(f"  Learning curve (avg reward):")
        for cp, val in checkpoints.items():
            lines.append(f"    {cp:>12s}: {val:>7.1f}")
        lines.append(f"  Reward variance:")
        for cp, val in var_checkpoints.items():
            lines.append(f"    {cp:>12s}: {val:>7.1f}")
        lines.append("")

    lines.append("--- Key Insight ---")
    lines.append("  Actor-Critic converges fastest (TD updates every step).")
    lines.append("  REINFORCE+Baseline reduces variance vs pure REINFORCE.")
    lines.append("  Pure REINFORCE has highest variance — needs normalization.")
    lines.append("")
    lines.append("  The advantage function A(s,a) = Q(s,a) - V(s) is the")
    lines.append("  unifying concept: REINFORCE uses G-V (MC advantage),")
    lines.append("  Actor-Critic uses delta (TD advantage). Both estimate")
    lines.append("  how much better action a is compared to average in state s.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Policy Gradient Methods — REINFORCE, Baseline, Actor-Critic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--episodes", type=int, default=500,
                        help="Training episodes per method (default: 500)")
    parser.add_argument("--gamma", type=float, default=0.99,
                        help="Discount factor (default: 0.99)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    results = {}

    # 1. REINFORCE (normalized returns, higher lr for stability)
    env1 = MountainCar(rng=random.Random(args.seed))
    agent1 = LinearPolicy(3, rng=random.Random(args.seed))
    results["REINFORCE"] = reinforce(
        env1, agent1, args.episodes, lr=0.05, gamma=args.gamma, seed=args.seed
    )

    # 2. REINFORCE + Baseline
    env2 = MountainCar(rng=random.Random(args.seed))
    agent2 = LinearPolicy(3, rng=random.Random(args.seed))
    results["REINFORCE+Baseline"] = reinforce_baseline(
        env2, agent2, args.episodes, lr=0.05, v_lr=0.01,
        gamma=args.gamma, seed=args.seed
    )

    # 3. Actor-Critic
    env3 = MountainCar(rng=random.Random(args.seed))
    agent3 = LinearPolicy(3, rng=random.Random(args.seed))
    results["Actor-Critic"] = actor_critic(
        env3, agent3, args.episodes, lr=0.01, v_lr=0.01,
        gamma=args.gamma, seed=args.seed
    )

    if args.json:
        output = {
            "config": vars(args),
            "results": {},
        }
        for name, stats in results.items():
            output["results"][name] = {
                "final_avg": round(stats["final_avg"], 2),
            }
            rewards = stats["episode_rewards"]
            checkpoints, var_checkpoints = compute_stats(rewards)
            output["results"][name]["learning_curve"] = checkpoints
            output["results"][name]["variance"] = var_checkpoints
        print(json.dumps(output, indent=2))
    else:
        print(format_report(results))


if __name__ == "__main__":
    main()
