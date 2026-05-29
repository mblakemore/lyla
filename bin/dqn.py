#!/usr/bin/env python3
"""Deep Q-Network (DQN) — Neural Network Function Approximation for Q-Learning

Demonstrates how neural networks replace Q-tables, enabling RL in
high-dimensional continuous state spaces. Applies the C529 Q-learning
framework with two key innovations:
  1. Function approximation — neural network estimates Q(s,a) instead of table lookup
  2. Experience replay — breaks correlation between consecutive samples for stability

Compares DQN to tabular Q-learning baseline on CartPole.

Usage:
    python3 bin/dqn.py
    python3 bin/dqn.py --episodes 500
    python3 bin/dqn.py --json
"""

import argparse
import json
import math
import random
import sys

import numpy as np


# ---------------------------------------------------------------------------
# CartPole Environment (self-contained, no gym dependency)
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
        self.length = 0.5  # half pole length
        self.mass_pole_length = self.mass_pole * self.length
        self.force_mag = 10.0
        self.tau = 0.02  # seconds between steps
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
# Simple Neural Network (NumPy, no framework dependency)
# ---------------------------------------------------------------------------

def relu(x):
    return np.maximum(0, x)

def relu_deriv(x):
    return (x > 0).astype(float)

def he_init(fan_in, fan_out, rng):
    return rng.standard_normal((fan_in, fan_out)) * math.sqrt(2.0 / fan_in)


class MLP:
    """Multi-layer perceptron for Q-value estimation.

    Architecture: input -> hidden (ReLU) -> hidden (ReLU) -> output (linear)
    Forward pass returns Q-values for each action.
    """

    def __init__(self, input_dim, hidden_dim, output_dim, rng=None):
        self.rng = rng or np.random.default_rng()
        self.W1 = he_init(input_dim, hidden_dim, self.rng)
        self.b1 = np.zeros(hidden_dim)
        self.W2 = he_init(hidden_dim, hidden_dim, self.rng)
        self.b2 = np.zeros(hidden_dim)
        self.W3 = he_init(hidden_dim, output_dim, self.rng)
        self.b3 = np.zeros(output_dim)

    def forward(self, x):
        """Forward pass. Returns (Q-values, cache for backprop)."""
        self.z1 = x @ self.W1 + self.b1
        self.a1 = relu(self.z1)
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = relu(self.z2)
        self.output = self.a2 @ self.W3 + self.b3
        return self.output

    def backward(self, x, grad_output, lr=0.001):
        """Backward pass with SGD update.

        Args:
            x: Input batch (n, input_dim)
            grad_output: Gradient of loss w.r.t. output (n, output_dim)
            lr: Learning rate
        """
        batch_size = x.shape[0]

        # Output layer
        dW3 = self.a2.T @ grad_output / batch_size
        db3 = grad_output.mean(axis=0)

        # Hidden layer 2
        da2 = grad_output @ self.W3.T
        dz2 = da2 * relu_deriv(self.z2)
        dW2 = self.a1.T @ dz2 / batch_size
        db2 = dz2.mean(axis=0)

        # Hidden layer 1
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

        # Update
        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W3 -= lr * dW3
        self.b3 -= lr * db3

    def copy(self):
        """Create a copy of the network (for target network)."""
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
# Experience Replay Buffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    """Fixed-size experience replay buffer.

    Stores (state, action, reward, next_state, done) tuples and samples
    random batches to break temporal correlation.
    """

    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size, rng):
        indices = rng.choice(min(len(self.buffer), self.capacity), batch_size, replace=False)
        batch = [self.buffer[i] for i in indices]
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones),
        )

    def __len__(self):
        return len(self.buffer)


# ---------------------------------------------------------------------------
# DQN Agent
# ---------------------------------------------------------------------------

class DQNAgent:
    """Deep Q-Network agent with experience replay and target network.

    Uses a neural network to approximate Q(s, a) and a target network
    for stable bootstrapping. The target network is periodically updated
    from the online network to reduce correlation between target and prediction.
    """

    def __init__(self, state_dim, action_dim, hidden_dim=64,
                 lr=0.01, gamma=0.99, epsilon=1.0, epsilon_min=0.01,
                 epsilon_decay=0.995, target_update_freq=100,
                 buffer_size=10000, batch_size=64, rng=None):
        self.rng = rng or np.random.default_rng()
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.target_update_freq = target_update_freq
        self.batch_size = batch_size
        self.lr = lr
        self.step_count = 0

        # Online and target networks
        self.online_net = MLP(state_dim, hidden_dim, action_dim, self.rng)
        self.target_net = self.online_net.copy()

        # Replay buffer
        self.buffer = ReplayBuffer(buffer_size)

        # Normalization bounds (CartPole defaults)
        self.norm_bounds = [4.0, 12 * math.pi / 180, 10.0, 20.0]

    def _normalize(self, state):
        """Clip and normalize state to [-1, 1] for stable learning."""
        return np.array([
            np.clip(state[i], -b, b) / b
            for i, b in enumerate(self.norm_bounds)
        ])

    def select_action(self, state):
        """Epsilon-greedy action selection."""
        if self.rng.random() < self.epsilon:
            return self.rng.integers(0, self.action_dim)
        normed = self._normalize(state).reshape(1, -1)
        q_values = self.online_net.forward(normed)[0]
        return int(np.argmax(q_values))

    def store(self, state, action, reward, next_state, done):
        self.buffer.push(state, action, reward, next_state, done)

    def learn(self):
        """Sample from replay buffer and perform one gradient update."""
        if len(self.buffer) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.buffer.sample(
            self.batch_size, self.rng
        )

        # Normalize states
        states_n = np.array([self._normalize(s) for s in states])
        next_states_n = np.array([self._normalize(s) for s in next_states])

        # Current Q-values
        q_current = self.online_net.forward(states_n)

        # Target Q-values from target network
        q_next = self.target_net.forward(next_states_n)
        max_q_next = np.max(q_next, axis=1)

        # DQN target: r + gamma * max_a' Q_target(s', a') * (1 - done)
        targets = rewards + self.gamma * max_q_next * (1 - dones.astype(float))

        # Compute MSE loss gradient for selected actions only
        errors = np.array([q_current[i, action] - targets[i] for i, action in enumerate(actions)])
        grad_output = np.zeros_like(q_current)
        for i, action in enumerate(actions):
            grad_output[i, action] = 2.0 * errors[i]

        self.online_net.backward(states_n, grad_output, self.lr)
        self.step_count += 1

        # Update target network periodically
        if self.step_count % self.target_update_freq == 0:
            self.target_net = self.online_net.copy()

        return float(np.mean(errors ** 2))

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


# ---------------------------------------------------------------------------
# Tabular Baseline (for comparison)
# ---------------------------------------------------------------------------

class TabularQAgent:
    """Simplified tabular Q-learning on binned CartPole state.

    Discretizes continuous state into bins to enable table lookup.
    Used as a baseline to show what DQN gains from function approximation.
    """

    def __init__(self, num_actions, num_bins=10, alpha=0.1, gamma=0.99,
                 epsilon=1.0, epsilon_min=0.01, epsilon_decay=0.995, rng=None):
        self.rng = rng or np.random.default_rng()
        self.num_actions = num_actions
        self.num_bins = num_bins
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table = {}

    def _bin_state(self, state):
        """Discretize continuous state into bins."""
        # Cart pos: [-4, 4], Angle: [-12, 12] deg, Vel: [-inf, inf], AngVel: [-inf, inf]
        x, theta, x_dot, theta_dot = state
        bins = []
        for val, lo, hi in [(x, -4, 4), (theta, -12 * math.pi / 180, 12 * math.pi / 180)]:
            b = int((val - lo) / (hi - lo) * (self.num_bins - 1))
            bins.append(max(0, min(self.num_bins - 1, b)))
        for val in [x_dot, theta_dot]:
            b = int(np.clip(val, -5, 5) / 10 * (self.num_bins - 1))
            bins.append(max(0, min(self.num_bins - 1, b)))
        return tuple(bins)

    def select_action(self, state):
        if self.rng.random() < self.epsilon:
            return self.rng.integers(0, self.num_actions)
        key = self._bin_state(state)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * self.num_actions
        return int(np.argmax(self.q_table[key]))

    def update(self, state, action, reward, next_state, done):
        key = self._bin_state(state)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * self.num_actions

        if done:
            target = reward
        else:
            next_key = self._bin_state(next_state)
            if next_key not in self.q_table:
                self.q_table[next_key] = [0.0] * self.num_actions
            target = reward + self.gamma * max(self.q_table[next_key])

        self.q_table[key][action] += self.alpha * (target - self.q_table[key][action])

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_dqn(env, agent, num_episodes, max_steps=500):
    """Train DQN agent on CartPole."""
    episode_rewards = []
    episode_lengths = []

    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            agent.store(state, action, reward, next_state, done)
            agent.learn()

            total_reward += reward
            state = next_state
            steps += 1

        agent.decay_epsilon()
        episode_rewards.append(total_reward)
        episode_lengths.append(steps)

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "final_epsilon": round(agent.epsilon, 6),
        "buffer_size": len(agent.buffer),
    }


def train_tabular(env, agent, num_episodes, max_steps=500):
    """Train tabular Q-learning agent on CartPole."""
    episode_rewards = []
    episode_lengths = []

    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            action = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            agent.update(state, action, reward, next_state, done)

            total_reward += reward
            state = next_state
            steps += 1

        agent.decay_epsilon()
        episode_rewards.append(total_reward)
        episode_lengths.append(steps)

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "final_epsilon": round(agent.epsilon, 6),
        "table_size": len(agent.q_table),
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
        slice_ = rewards[max(0, idx - window + 1):idx + 1]
        checkpoints[f"{int(cp * 100)}pct"] = round(sum(slice_) / len(slice_), 1)
    return checkpoints


def compute_success_rate(lengths, max_len=200, window=20):
    """Compute fraction of episodes reaching max_len at checkpoints."""
    n = len(lengths)
    checkpoints = {}
    for cp in [0.1, 0.25, 0.5, 0.75, 1.0]:
        idx = int(cp * n)
        slice_ = lengths[max(0, idx - window * 5 + 1):idx + 1]
        success = sum(1 for l in slice_ if l >= max_len)
        checkpoints[f"{int(cp * 100)}pct"] = round(success / len(slice_) * 100, 1)
    return checkpoints


def format_report(dqn_stats, tabular_stats):
    """Format comparison report."""
    lines = []
    lines.append("=" * 60)
    lines.append("DEEP Q-NETWORK — CartPole")
    lines.append("=" * 60)
    lines.append("")
    lines.append("DQN: Neural network Q-function + experience replay + target network")
    lines.append("Tabular: Discretized state + Q-table baseline")
    lines.append("")

    for name, stats in [("DQN", dqn_stats), ("Tabular Baseline", tabular_stats)]:
        rewards = stats["episode_rewards"]
        lengths = stats["episode_lengths"]
        final_avg = sum(rewards[-100:]) / min(100, len(rewards))
        best = max(rewards)

        lines.append(f"--- {name} ---")
        lines.append(f"  Final avg reward (last 100): {final_avg:.1f}")
        lines.append(f"  Best episode: {best:.0f}")
        lines.append(f"  Final epsilon: {stats['final_epsilon']}")
        if "buffer_size" in stats:
            lines.append(f"  Replay buffer size: {stats['buffer_size']}")
        if "table_size" in stats:
            lines.append(f"  Q-table entries: {stats['table_size']}")
        lines.append("")

        lines.append("  Learning Curve (avg reward, window=20):")
        for cp, val in compute_learning_curve(rewards).items():
            lines.append(f"    {cp:>12s}: {val:>7.1f}")

        lines.append("  Success Rate (>=200 steps, window=100):")
        for cp, val in compute_success_rate(lengths).items():
            lines.append(f"    {cp:>12s}: {val:>6.1f}%")
        lines.append("")

    lines.append("--- Key Insight ---")
    lines.append("  DQN replaces the Q-table with a neural network, enabling")
    lines.append("  RL in continuous state spaces without discretization.")
    lines.append("  Experience replay breaks temporal correlation — samples are")
    lines.append("  i.i.d., satisfying the independence assumption of SGD.")
    lines.append("  The target network stabilizes bootstrapping: Q-target and")
    lines.append("  Q-prediction use different parameters, preventing chasing")
    lines.append("  a moving target. Without it, DQN diverges.")
    lines.append("")
    lines.append("  This is the bridge from C529 (tabular Q-learning) to")
    lines.append("  deep RL. The same Q-learning update, but with a neural")
    lines.append("  network as the function approximator, scales from")
    lines.append("  gridworlds to Atari, Go, and robotics.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Deep Q-Network (DQN) — Neural Q-function for CartPole",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--episodes", type=int, default=500,
                        help="Training episodes (default: 500)")
    parser.add_argument("--hidden-dim", type=int, default=64,
                        help="Hidden layer dimension (default: 64)")
    parser.add_argument("--lr", type=float, default=0.01,
                        help="Learning rate (default: 0.01)")
    parser.add_argument("--gamma", type=float, default=0.99,
                        help="Discount factor (default: 0.99)")
    parser.add_argument("--epsilon-decay", type=float, default=0.995,
                        help="Epsilon decay per episode (default: 0.995)")
    parser.add_argument("--buffer-size", type=int, default=50000,
                        help="Replay buffer capacity (default: 50000)")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Mini-batch size (default: 64)")
    parser.add_argument("--target-update-freq", type=int, default=100,
                        help="Target network sync frequency (default: 100)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    # Train DQN
    env_dqn = CartPole(rng=rng)
    dqn_agent = DQNAgent(
        state_dim=4, action_dim=2,
        hidden_dim=args.hidden_dim,
        lr=args.lr, gamma=args.gamma,
        epsilon_decay=args.epsilon_decay,
        target_update_freq=args.target_update_freq,
        buffer_size=args.buffer_size,
        batch_size=args.batch_size,
        rng=rng,
    )
    dqn_stats = train_dqn(env_dqn, dqn_agent, args.episodes)

    # Train Tabular Baseline
    rng_tab = np.random.default_rng(args.seed)
    env_tab = CartPole(rng=rng_tab)
    tabular_agent = TabularQAgent(
        num_actions=2, num_bins=10,
        epsilon_decay=args.epsilon_decay,
        rng=rng_tab,
    )
    tabular_stats = train_tabular(env_tab, tabular_agent, args.episodes)

    if args.json:
        output = {
            "config": vars(args),
            "dqn": {
                "final_avg_reward": round(
                    sum(dqn_stats["episode_rewards"][-100:]) / min(100, len(dqn_stats["episode_rewards"])), 2
                ),
                "best_reward": max(dqn_stats["episode_rewards"]),
                "final_epsilon": dqn_stats["final_epsilon"],
                "buffer_size": dqn_stats["buffer_size"],
                "learning_curve": compute_learning_curve(dqn_stats["episode_rewards"]),
                "success_rate": compute_success_rate(dqn_stats["episode_lengths"]),
            },
            "tabular": {
                "final_avg_reward": round(
                    sum(tabular_stats["episode_rewards"][-100:]) / min(100, len(tabular_stats["episode_rewards"])), 2
                ),
                "best_reward": max(tabular_stats["episode_rewards"]),
                "final_epsilon": tabular_stats["final_epsilon"],
                "table_size": tabular_stats["table_size"],
                "learning_curve": compute_learning_curve(tabular_stats["episode_rewards"]),
                "success_rate": compute_success_rate(tabular_stats["episode_lengths"]),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_report(dqn_stats, tabular_stats))


if __name__ == "__main__":
    main()
