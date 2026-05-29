#!/usr/bin/env python3
"""Proximal Policy Optimization (PPO) — Clipped Objective Policy Gradient

Demonstrates PPO on CartPole, the algorithm that made policy gradients
practical for real-world problems. Combines value and policy approaches:
  1. Clipped surrogate objective — prevents large policy updates
  2. GAE advantage estimation — balances TD bias and MC variance
  3. Mini-batch SGD — multiple epochs per collected trajectory batch

Compares PPO to REINFORCE and Actor-Critic (from C530) on the same environment.

Usage:
    python3 bin/ppo.py
    python3 bin/ppo.py --episodes 300
    python3 bin/ppo.py --json
"""

import argparse
import json
import math
import random
import sys

import numpy as np


# ---------------------------------------------------------------------------
# CartPole Environment (same as C531 DQN)
# ---------------------------------------------------------------------------

class CartPole:
    """CartPole environment — balance a pole on a cart.

    State: [cart_pos, pole_angle, cart_vel, pole_ang_vel] (continuous, 4-dim)
    Actions: 0=push left, 1=push right
    Reward: +1 per step
    Done: pole angle > 12 degrees or cart position > 4
    Max steps: 500
    """

    def __init__(self, rng=None):
        self.rng = rng or np.random.default_rng()
        self.gravity = 9.8
        self.mass_cart = 1.0
        self.mass_pole = 0.1
        self.total_mass = self.mass_cart + self.mass_pole
        self.length = 0.5
        self.mass_pole_length = self.mass_pole * self.length
        self.force_mag = 10.0
        self.tau = 0.02
        self.theta_threshold = 12 * (2 * math.pi / 360)
        self.x_threshold = 4.0
        self.max_steps = 500
        self.steps = 0

    def reset(self):
        self.state = self.rng.uniform(-0.05, 0.05, size=4)
        self.steps = 0
        return self.state.copy()

    def step(self, action):
        x, theta, x_dot, theta_dot = self.state
        force = self.force_mag if action == 1 else -self.force_mag

        delta_theta = (
            (self.gravity * math.cos(theta) - force * math.cos(theta))
            / self.total_mass
        )
        delta_x = (force + self.mass_pole_length * delta_theta * math.cos(theta)) / self.total_mass
        balance = (1 + 3 * self.mass_pole / (4 * self.total_mass)) * delta_theta

        x_dot += delta_x * self.tau
        theta_dot += balance * self.tau
        x += x_dot * self.tau
        theta += theta_dot * self.tau
        self.steps += 1

        done = (abs(x) > self.x_threshold or abs(theta) > self.theta_threshold
                or self.steps >= self.max_steps)
        reward = 1.0
        self.state = np.array([x, theta, x_dot, theta_dot])
        return self.state, reward, done, {}


# ---------------------------------------------------------------------------
# Neural Network (same MLP as C531, reused for actor and critic)
# ---------------------------------------------------------------------------

def relu(x):
    return np.maximum(0, x)

def relu_deriv(x):
    return (x > 0).astype(float)

def he_init(fan_in, fan_out, rng):
    return rng.standard_normal((fan_in, fan_out)) * math.sqrt(2.0 / fan_in)


class MLP:
    """Multi-layer perceptron — 2 hidden layers with ReLU."""

    def __init__(self, input_dim, hidden_dim, output_dim, rng=None):
        self.rng = rng or np.random.default_rng()
        self.W1 = he_init(input_dim, hidden_dim, self.rng)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = he_init(hidden_dim, hidden_dim, self.rng)
        self.b2 = np.zeros(hidden_dim)
        self.W3 = he_init(hidden_dim, output_dim, self.rng)
        self.b3 = np.zeros(output_dim)

    def forward(self, x):
        self.x = x
        self.z1 = x @ self.W1 + self.b1
        self.a1 = relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = relu(self.z2)
        self.output = self.a2 @ self.W3 + self.b3
        return self.output

    def backward(self, x, grad_output, lr=0.001):
        batch_size = x.shape[0]

        dW3 = self.a2.T @ grad_output / batch_size
        db3 = grad_output.mean(axis=0)

        da2 = grad_output @ self.W3.T
        dz2 = da2 * relu_deriv(self.z2)
        dW2 = self.a1.T @ dz2 / batch_size
        db2 = dz2.mean(axis=0)

        da1 = dz2 @ self.W2.T
        dz1 = da1 * relu_deriv(self.z1)
        dW1 = x.T @ dz1 / batch_size
        db1 = dz1.mean(axis=0)

        # Gradient clipping
        max_norm = 5.0
        for w in [dW1, dW2, dW3]:
            norm = np.sqrt((w ** 2).sum())
            if norm > max_norm:
                w *= max_norm / norm

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W3 -= lr * dW3
        self.b3 -= lr * db3

    def copy(self):
        net = MLP.__new__(MLP)
        net.rng = self.rng
        net.W1 = self.W1.copy()
        net.b1 = self.b1.copy()
        net.W2 = self.W2.copy()
        net.b2 = self.b2.copy()
        net.W3 = self.W3.copy()
        net.b3 = self.b3.copy()
        return net


# ---------------------------------------------------------------------------
# Softmax Policy Network (Actor)
# ---------------------------------------------------------------------------

class PolicyNetwork:
    """Softmax policy: pi(a|s) = softmax(MLP(s)).

    Uses MLP for feature extraction, then softmax over action logits.
    Returns action probabilities and log-probability of selected action.
    """

    def __init__(self, input_dim, hidden_dim, output_dim, rng=None):
        self.rng = rng or np.random.default_rng()
        self.output_dim = output_dim
        # MLP: input -> hidden -> hidden -> logits (output_dim)
        self.W1 = he_init(input_dim, hidden_dim, self.rng)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = he_init(hidden_dim, hidden_dim, self.rng)
        self.b2 = np.zeros(hidden_dim)
        self.W3 = he_init(hidden_dim, output_dim, self.rng)
        self.b3 = np.zeros(output_dim)

    def forward(self, x):
        """Forward pass. Returns action probabilities."""
        self.x = x
        self.z1 = x @ self.W1 + self.b1
        self.a1 = relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = relu(self.z2)
        self.logits = self.a2 @ self.W3 + self.b3

        # Softmax
        logits_max = self.logits.max(axis=1, keepdims=True)
        exps = np.exp(self.logits - logits_max)
        self.probs = exps / exps.sum(axis=1, keepdims=True)
        return self.probs

    def select_action(self, probs):
        """Sample action from probability distribution."""
        return self.rng.choice(self.output_dim, p=probs[0])

    def log_prob(self, probs, actions):
        """Log probability of actions under current policy.

        Args:
            probs: Action probabilities (batch_size, num_actions)
            actions: Selected actions (batch_size,)
        Returns:
            log_probs: (batch_size,)
        """
        batch_size = probs.shape[0]
        log_probs = np.zeros(batch_size)
        for i in range(batch_size):
            log_probs[i] = math.log(probs[i, actions[i]] + 1e-8)
        return log_probs

    def backward(self, advantages, log_probs_old, lr=0.001):
        """Backward pass for policy gradient.

        Gradient of clipped PPO objective:
          L = mean( A * log(pi_new) / log(pi_old) ), clipped to [1-eps, 1+eps]

        Args:
            advantages: GAE advantages (batch_size,)
            log_probs_old: Old log probabilities (batch_size,)
            lr: Learning rate
        """
        batch_size = advantages.shape[0]

        # d/dlogit [log pi(a)] = one_hot(a) - probs
        # Chain rule: dL/dlogit = A * d(log pi)/dlogit
        dlogits = np.zeros((batch_size, self.output_dim))
        for i in range(batch_size):
            # We need to know which action was taken — reconstruct from log_probs_old
            # Since we stored log_probs, we know the action was the one with that log_prob
            # Simpler: pass action indices
            pass

        # Forward to get probs
        probs = self.probs

        # Gradient: d(log pi(a|s))/dW = (one_hot(a) - pi) / ...
        # For policy gradient: grad = (A * (one_hot(a) - pi))
        # Simplified: grad_log_probs for each action
        dlogits = (np.log(probs + 1e-8) - log_probs_old[:, np.newaxis]) * advantages[:, np.newaxis]

        # Backprop through softmax + MLP
        da2 = dlogits @ self.W3.T
        dz2 = da2 * relu_deriv(self.z2)
        dW3 = self.a2.T @ dlogits / batch_size
        db3 = dlogits.mean(axis=0)
        dW2 = self.a1.T @ dz2 / batch_size
        db2 = dz2.mean(axis=0)
        da1 = dz2 @ self.W2.T
        dz1 = da1 * relu_deriv(self.z1)
        dW1 = self.x.T @ dz1 / batch_size
        db1 = dz1.mean(axis=0)

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W3 -= lr * dW3
        self.b3 -= lr * db3

    def get_params(self):
        return [self.W1, self.b1, self.W2, self.b2, self.W3, self.b3]

    def set_params(self, params):
        self.W1, self.b1, self.W2, self.b2, self.W3, self.b3 = params


# ---------------------------------------------------------------------------
# Value Network (Critic)
# ---------------------------------------------------------------------------

class ValueNetwork:
    """Value function: V(s) = MLP(s) -> scalar."""

    def __init__(self, input_dim, hidden_dim, rng=None):
        self.rng = rng or np.random.default_rng()
        self.mlp = MLP(input_dim, hidden_dim, 1, self.rng)

    def predict(self, x):
        return self.mlp.forward(x).flatten()

    def update(self, targets, lr=0.001):
        """Update value network to match targets (MSE loss)."""
        values = self.mlp.output.flatten()
        errors = values - targets
        grad_output = 2.0 * errors.reshape(-1, 1)
        self.mlp.backward(self.mlp.x, grad_output, lr)
        return float(np.mean(errors ** 2))


# ---------------------------------------------------------------------------
# PPO Agent
# ---------------------------------------------------------------------------

class PPOAgent:
    """PPO agent with clipped objective and GAE advantage estimation.

    The clipped objective prevents policy updates from being too large:
      L_PPO = mean( A_t / r_t * log(pi_theta(s_t, a_t)) )
    where r_t = pi_new / pi_old is clipped to [1-eps, 1+eps].

    GAE (Generalized Advantage Estimation) combines TD and MC advantages:
      A_t = (1+g) * [delta_t + (gamma*g)*delta_{t+1} + ...]
    where g (lambda) controls the bias-variance tradeoff.
    """

    def __init__(self, state_dim, action_dim, hidden_dim=64,
                 lr=0.01, v_lr=0.005, gamma=0.99, gae_lambda=0.95,
                 clip_epsilon=0.2, epochs=4, batch_size=32, rng=None):
        self.rng = rng or np.random.default_rng()
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.v_lr = v_lr

        # Actor and Critic
        self.actor = PolicyNetwork(state_dim, hidden_dim, action_dim, self.rng)
        self.critic = ValueNetwork(state_dim, hidden_dim, self.rng)

        # State normalization
        self.norm_bounds = [4.0, 12 * math.pi / 180, 10.0, 20.0]

    def _normalize(self, state):
        return np.array([
            np.clip(state[i], -b, b) / b
            for i, b in enumerate(self.norm_bounds)
        ])

    def select_action(self, state):
        normed = self._normalize(state).reshape(1, -1)
        probs = self.actor.forward(normed)
        return self.actor.select_action(probs)

    def collect_trajectory(self, env, max_steps=500):
        """Collect one episode of experience.

        Returns list of (state, action, reward, log_prob, value, done).
        """
        trajectory = []
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            normed = self._normalize(state).reshape(1, -1)
            probs = self.actor.forward(normed)
            action = self.actor.select_action(probs)
            log_p = math.log(probs[0, action] + 1e-8)

            value = self.critic.predict(normed)[0]

            next_state, reward, done, _ = env.step(action)
            total_reward += reward
            trajectory.append((state, action, reward, log_p, value, done))
            state = next_state
            steps += 1

        return trajectory, total_reward

    def compute_gae(self, trajectory, bootstrap_value=0.0):
        """Compute Generalized Advantage Estimation.

        A_t = delta_t + (gamma*lambda)*delta_{t+1} + (gamma*lambda)^2 * delta_{t+2} + ...
        where delta_t = r_t + gamma * V(s_{t+1}) - V(s_t)

        Returns advantages and returns (advantages + values).
        """
        advantages = []
        gae = 0.0

        for t in reversed(range(len(trajectory))):
            state, action, reward, log_p, value, done = trajectory[t]

            if t < len(trajectory) - 1:
                _, _, _, _, _, next_done = trajectory[t + 1]
                next_state = trajectory[t + 1][0]
                next_normed = self._normalize(next_state).reshape(1, -1)
                next_value = self.critic.predict(next_normed)[0]
            else:
                next_value = bootstrap_value

            delta = reward + self.gamma * next_value * (1 - int(done)) - value
            gae = delta + self.gamma * self.gae_lambda * (1 - int(done)) * gae
            advantages.insert(0, gae)

        # Returns = advantages + values
        returns = []
        for t in range(len(trajectory)):
            _, _, _, _, value, _ = trajectory[t]
            returns.append(advantages[t] + value)

        return np.array(advantages), np.array(returns)

    def update(self, trajectories):
        """Update policy and value using collected trajectories.

        Multiple epochs of mini-batch gradient descent with clipped objective.
        """
        # Flatten trajectories
        all_states = []
        all_actions = []
        all_advantages = []
        all_returns = []
        all_log_probs = []

        for trajectory, _ in trajectories:
            advantages, returns = self.compute_gae(trajectory)

            # Normalize advantages (improves stability)
            if len(advantages) > 1:
                adv_mean = advantages.mean()
                adv_std = advantages.std() + 1e-8
                advantages = (advantages - adv_mean) / adv_std

            for t in range(len(trajectory)):
                state, action, reward, log_p, value, done = trajectory[t]
                normed = self._normalize(state).reshape(1, -1)
                all_states.append(normed)
                all_actions.append(action)
                all_advantages.append(advantages[t])
                all_returns.append(returns[t])
                all_log_probs.append(log_p)

        states = np.vstack(all_states)
        actions = np.array(all_actions)
        advantages = np.array(all_advantages)
        returns = np.array(all_returns)
        log_probs_old = np.array(all_log_probs)

        n_samples = len(states)
        total_loss = 0.0

        for epoch in range(self.epochs):
            # Shuffle
            indices = self.rng.permutation(n_samples)

            for start in range(0, n_samples, self.batch_size):
                end = min(start + self.batch_size, n_samples)
                batch_idx = indices[start:end]

                batch_states = states[batch_idx]
                batch_advantages = advantages[batch_idx]
                batch_returns = returns[batch_idx]
                batch_log_probs = log_probs_old[batch_idx]
                batch_actions = actions[batch_idx]

                # Forward pass — get new probs and values
                new_probs = self.actor.forward(batch_states)
                new_values = self.critic.predict(batch_states)

                # Compute log probs of taken actions
                new_log_probs = np.array([
                    math.log(new_probs[i, batch_actions[i]] + 1e-8)
                    for i in range(len(batch_idx))
                ])

                # Importance ratio
                ratios = np.exp(new_log_probs - batch_log_probs)

                # Clipped surrogate objective
                clipped_ratios = np.clip(ratios, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                surr1 = ratios * batch_advantages
                surr2 = clipped_ratios * batch_advantages
                policy_losses = -np.minimum(surr1, surr2)

                # Value loss (MSE)
                value_errors = new_values - batch_returns

                # Combined gradient
                batch_size = len(batch_idx)

                # Policy gradient
                dlogits = np.zeros((batch_size, self.action_dim))
                for i in range(batch_size):
                    dlogits[i] = np.zeros(self.action_dim)
                    dlogits[i, batch_actions[i]] = 1.0
                dlogits -= new_probs

                # Weight by advantages
                dlogits *= policy_losses[:, np.newaxis]

                # Backprop policy
                da2 = dlogits @ self.actor.W3.T
                dz2 = da2 * relu_deriv(self.actor.z2)
                dW3 = self.actor.a2.T @ dlogits / batch_size
                db3 = dlogits.mean(axis=0)
                dW2 = self.actor.a1.T @ dz2 / batch_size
                db2 = dz2.mean(axis=0)
                da1 = dz2 @ self.actor.W2.T
                dz1 = da1 * relu_deriv(self.actor.z1)
                dW1 = batch_states.T @ dz1 / batch_size
                db1 = dz1.mean(axis=0)

                self.actor.W1 -= self.lr * dW1
                self.actor.b1 -= self.lr * db1
                self.actor.W2 -= self.lr * dW2
                self.actor.b2 -= self.lr * db2
                self.actor.W3 -= self.lr * dW3
                self.actor.b3 -= self.lr * db3

                # Backprop value
                dvalues = 2.0 * value_errors.reshape(-1, 1)
                self.critic.mlp.backward(batch_states, dvalues, self.v_lr)

                total_loss += float(np.mean(policy_losses))

        return total_loss / (self.epochs * max(1, n_samples // self.batch_size))


# ---------------------------------------------------------------------------
# Baseline: REINFORCE (simplified, from C530 pattern)
# ---------------------------------------------------------------------------

class REINFORCEAgent:
    """Simple REINFORCE agent for comparison."""

    def __init__(self, state_dim, action_dim, hidden_dim=64,
                 lr=0.01, gamma=0.99, rng=None):
        self.rng = rng or np.random.default_rng()
        self.action_dim = action_dim
        self.gamma = gamma
        self.lr = lr
        self.norm_bounds = [4.0, 12 * math.pi / 180, 10.0, 20.0]
        self.actor = PolicyNetwork(state_dim, hidden_dim, action_dim, self.rng)

    def _normalize(self, state):
        return np.array([
            np.clip(state[i], -b, b) / b
            for i, b in enumerate(self.norm_bounds)
        ])

    def select_action(self, state):
        normed = self._normalize(state).reshape(1, -1)
        probs = self.actor.forward(normed)
        return self.actor.select_action(probs)

    def train_episode(self, env, max_steps=500):
        """Run one episode and update with REINFORCE."""
        trajectory = []
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            normed = self._normalize(state).reshape(1, -1)
            probs = self.actor.forward(normed)
            action = self.actor.select_action(probs)
            log_p = math.log(probs[0, action] + 1e-8)

            next_state, reward, done, _ = env.step(action)
            total_reward += reward
            trajectory.append((normed, action, reward, log_p, probs.copy()))
            state = next_state
            steps += 1

        # Compute discounted returns
        returns = []
        G = 0.0
        for t in reversed(range(len(trajectory))):
            _, _, reward, _, _ = trajectory[t]
            G = reward + self.gamma * G
            returns.insert(0, G)

        # Normalize returns
        if len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / len(returns) + 1e-8)
            returns = [(r - mean_r) / std_r for r in returns]

        # Update policy
        for t in range(len(trajectory)):
            normed, action, _, _, probs = trajectory[t]
            batch_size = 1
            dlogits = np.zeros((1, self.action_dim))
            dlogits[0, action] = 1.0 - probs[0, action]
            dlogits *= returns[t]

            da2 = dlogits @ self.actor.W3.T
            dz2 = da2 * relu_deriv(self.actor.z2)
            dW3 = self.actor.a2.T @ dlogits
            db3 = dlogits
            dW2 = self.actor.a1.T @ dz2
            db2 = dz2
            da1 = dz2 @ self.actor.W2.T
            dz1 = da1 * relu_deriv(self.actor.z1)
            dW1 = normed.T @ dz1
            db1 = dz1

            self.actor.W1 -= self.lr * dW1.squeeze()
            self.actor.b1 -= self.lr * db1.squeeze()
            self.actor.W2 -= self.lr * dW2.squeeze()
            self.actor.b2 -= self.lr * db2.squeeze()
            self.actor.W3 -= self.lr * dW3.squeeze()
            self.actor.b3 -= self.lr * db3.squeeze()

        return total_reward


# ---------------------------------------------------------------------------
# Training Loop
# ---------------------------------------------------------------------------

def train_ppo(env, agent, num_episodes, rollout_steps=8, max_steps=500):
    """Train PPO agent.

    Collects rollout_steps episodes per update, then performs multiple
    epochs of mini-batch gradient descent.
    """
    episode_rewards = []
    episode_lengths = []
    update_count = 0
    batch = []

    for episode in range(num_episodes):
        trajectory, total_reward = agent.collect_trajectory(env, max_steps)
        episode_rewards.append(total_reward)
        episode_lengths.append(len(trajectory))
        batch.append((trajectory, total_reward))

        # Update after collecting rollout_steps trajectories
        if len(batch) >= rollout_steps:
            agent.update(batch)
            batch = []
            update_count += 1

    # Final update with remaining trajectories
    if batch:
        agent.update(batch)
        update_count += 1

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "num_updates": update_count,
    }


def train_reinforce(env, agent, num_episodes, max_steps=500):
    """Train REINFORCE agent."""
    episode_rewards = []
    episode_lengths = []

    for _ in range(num_episodes):
        total_reward = agent.train_episode(env, max_steps)
        episode_rewards.append(total_reward)
        episode_lengths.append(int(total_reward))  # reward = steps in CartPole

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def compute_learning_curve(rewards, window=20):
    """Compute moving average at checkpoints."""
    n = len(rewards)
    checkpoints = {}
    for cp in [0.1, 0.25, 0.5, 0.75, 1.0]:
        idx = int(cp * n)
        if idx == 0:
            idx = 1
        slice_ = rewards[max(0, idx - window + 1):idx + 1]
        checkpoints[f"{int(cp * 100)}pct"] = round(sum(slice_) / len(slice_), 1)
    return checkpoints


def compute_success_rate(lengths, threshold=200, window=50):
    """Compute fraction of episodes reaching threshold steps."""
    n = len(lengths)
    checkpoints = {}
    for cp in [0.1, 0.25, 0.5, 0.75, 1.0]:
        idx = int(cp * n)
        if idx == 0:
            idx = 1
        slice_ = lengths[max(0, idx - window + 1):idx + 1]
        success = sum(1 for l in slice_ if l >= threshold)
        checkpoints[f"{int(cp * 100)}pct"] = round(success / len(slice_) * 100, 1)
    return checkpoints


def format_report(ppo_stats, reinforce_stats):
    """Format comparison report."""
    lines = []
    lines.append("=" * 60)
    lines.append("PROXIMAL POLICY OPTIMIZATION — CartPole")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Methods compared:")
    lines.append("  1. PPO — Clipped objective + GAE advantage + mini-batch SGD")
    lines.append("  2. REINFORCE — Monte Carlo policy gradient (baseline)")
    lines.append("")

    for name, stats in [("PPO", ppo_stats), ("REINFORCE", reinforce_stats)]:
        rewards = stats["episode_rewards"]
        lengths = stats["episode_lengths"]
        final_avg = sum(rewards[-50:]) / min(50, len(rewards))
        best = max(rewards)

        lines.append(f"--- {name} ---")
        lines.append(f"  Final avg reward (last 50): {final_avg:.1f}")
        lines.append(f"  Best episode: {best:.0f}")
        if "num_updates" in stats:
            lines.append(f"  Policy updates: {stats['num_updates']}")
        lines.append("")

        lines.append("  Learning Curve (avg reward, window=20):")
        for cp, val in compute_learning_curve(rewards).items():
            lines.append(f"    {cp:>12s}: {val:>7.1f}")

        lines.append("  Success Rate (>=200 steps, window=50):")
        for cp, val in compute_success_rate(lengths).items():
            lines.append(f"    {cp:>12s}: {val:>6.1f}%")
        lines.append("")

    lines.append("--- Key Insight ---")
    lines.append("  PPO clips the importance ratio to [1-eps, 1+eps], preventing")
    lines.append("  large policy updates that destroy learned behavior. This is")
    lines.append("  simpler than TRPO (no conjugate gradient) but achieves similar")
    lines.append("  sample efficiency — the algorithm that made RL practical.")
    lines.append("")
    lines.append("  GAE (lambda=0.95) balances TD bias (lambda=0) and MC variance")
    lines.append("  (lambda=1). The sweet spot: low enough variance for stable")
    lines.append("  gradients, low enough bias for accurate advantage estimates.")
    lines.append("")
    lines.append("  PPO unifies the RL toolkit: value functions from DQN (C531),")
    lines.append("  policy gradients from REINFORCE (C530), and the clipped")
    lines.append("  objective that makes both work together reliably.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Proximal Policy Optimization (PPO) — Clipped Objective on CartPole",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--episodes", type=int, default=1000,
                        help="Training episodes (default: 1000)")
    parser.add_argument("--hidden-dim", type=int, default=64,
                        help="Hidden layer dimension (default: 64)")
    parser.add_argument("--lr", type=float, default=0.01,
                        help="Policy learning rate (default: 0.01)")
    parser.add_argument("--v-lr", type=float, default=0.005,
                        help="Value learning rate (default: 0.005)")
    parser.add_argument("--gamma", type=float, default=0.99,
                        help="Discount factor (default: 0.99)")
    parser.add_argument("--gae-lambda", type=float, default=0.95,
                        help="GAE lambda (default: 0.95)")
    parser.add_argument("--clip-epsilon", type=float, default=0.2,
                        help="PPO clip epsilon (default: 0.2)")
    parser.add_argument("--epochs", type=int, default=10,
                        help="PPO optimization epochs (default: 10)")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Mini-batch size (default: 32)")
    parser.add_argument("--rollout-steps", type=int, default=16,
                        help="Trajectories per update (default: 16)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    # Train PPO
    print("Training PPO...")
    env_ppo = CartPole(rng=rng)
    ppo_agent = PPOAgent(
        state_dim=4, action_dim=2,
        hidden_dim=args.hidden_dim,
        lr=args.lr, v_lr=args.v_lr,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_epsilon=args.clip_epsilon,
        epochs=args.epochs,
        batch_size=args.batch_size,
        rng=rng,
    )
    ppo_stats = train_ppo(env_ppo, ppo_agent, args.episodes,
                          rollout_steps=args.rollout_steps)

    # Train REINFORCE baseline
    print("Training REINFORCE baseline...")
    rng_re = np.random.default_rng(args.seed)
    env_re = CartPole(rng=rng_re)
    re_agent = REINFORCEAgent(
        state_dim=4, action_dim=2,
        hidden_dim=args.hidden_dim,
        lr=args.lr, gamma=args.gamma,
        rng=rng_re,
    )
    reinforce_stats = train_reinforce(env_re, re_agent, args.episodes)

    if args.json:
        output = {
            "config": vars(args),
            "ppo": {
                "final_avg_reward": round(
                    sum(ppo_stats["episode_rewards"][-50:]) / min(50, len(ppo_stats["episode_rewards"])), 2
                ),
                "best_reward": max(ppo_stats["episode_rewards"]),
                "num_updates": ppo_stats["num_updates"],
                "learning_curve": compute_learning_curve(ppo_stats["episode_rewards"]),
                "success_rate": compute_success_rate(ppo_stats["episode_lengths"]),
            },
            "reinforce": {
                "final_avg_reward": round(
                    sum(reinforce_stats["episode_rewards"][-50:]) / min(50, len(reinforce_stats["episode_rewards"])), 2
                ),
                "best_reward": max(reinforce_stats["episode_rewards"]),
                "learning_curve": compute_learning_curve(reinforce_stats["episode_rewards"]),
                "success_rate": compute_success_rate(reinforce_stats["episode_lengths"]),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_report(ppo_stats, reinforce_stats))


if __name__ == "__main__":
    main()
