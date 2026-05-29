#!/usr/bin/env python3
"""Q-Learning Agent for Gridworld

Demonstrates tabular Q-learning on a configurable gridworld MDP. Applies the
C527 RL toolkit: Q-values, temporal difference learning, epsilon-greedy
exploration, and convergence to optimal policy.

Usage:
    # Default 4x4 gridworld
    python3 bin/q_learning.py

    # Larger grid with obstacles
    python3 bin/q_learning.py --size 8 --obstacles 5

    # Compare Q-learning to optimal (value iteration)
    python3 bin/q_learning.py --compare-optimal

    # JSON output for analysis
    python3 bin/q_learning.py --json

    # Custom hyperparameters
    python3 bin/q_learning.py --alpha 0.1 --gamma 0.99 --epsilon 0.1 --episodes 5000
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from copy import deepcopy


class GridWorld:
    """Configurable gridworld MDP with obstacles, rewards, and terminal states."""

    def __init__(self, size=4, obstacles=None, reward=-0.04, goal_reward=1.0,
                 penalty=-1.0, rng=None):
        """
        Args:
            size: Grid dimension (size x size).
            obstacles: Set of (row, col) tuples that are blocked.
            reward: Reward per step (living cost).
            goal_reward: Reward for reaching the goal.
            penalty: Reward for hitting an obstacle.
            rng: Random number generator.
        """
        self.size = size
        self.reward = reward
        self.goal_reward = goal_reward
        self.penalty = penalty
        self.rng = rng or random.Random()
        self.num_states = size * size
        self.actions = [0, 1, 2, 3]  # up, right, down, left
        self.action_names = {0: "up", 1: "right", 2: "down", 3: "left"}

        # Goal at bottom-right corner
        self.goal = (size - 1, size - 1)

        # Obstacles (ensure goal is not blocked)
        self.obstacles = set(obstacles) if obstacles else set()
        self.obstacles.discard(self.goal)

        # Starting state (top-left)
        self.start = (0, 0)
        self.state = self.start

    def reset(self):
        """Reset environment to start state."""
        self.state = self.start
        return self.state

    def step(self, action):
        """
        Take an action and return (next_state, reward, done).
        Actions: 0=up, 1=right, 2=down, 3=left
        """
        row, col = self.state
        deltas = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}
        dr, dc = deltas[action]
        new_row, new_col = row + dr, col + dc

        # Wall bounce: stay in place if out of bounds
        if new_row < 0 or new_row >= self.size or new_col < 0 or new_col >= self.size:
            new_row, new_col = row, col

        # Obstacle check
        if (new_row, new_col) in self.obstacles:
            reward = self.penalty
        elif (new_row, new_col) == self.goal:
            reward = self.goal_reward
            self.state = (new_row, new_col)
            return self.state, reward, True
        else:
            reward = self.reward

        self.state = (new_row, new_col)
        return self.state, reward, False

    def is_terminal(self, state=None):
        """Check if state is terminal (goal)."""
        s = state or self.state
        return s == self.goal

    def all_states(self):
        """Return list of all non-obstacle states."""
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if (r, c) not in self.obstacles]


class QLearningAgent:
    """Tabular Q-learning agent with epsilon-greedy exploration."""

    def __init__(self, num_actions, alpha=0.1, gamma=0.99, epsilon=1.0,
                 epsilon_min=0.01, epsilon_decay=0.999, rng=None):
        """
        Args:
            num_actions: Number of possible actions.
            alpha: Learning rate.
            gamma: Discount factor.
            epsilon: Initial exploration rate.
            epsilon_min: Minimum exploration rate.
            epsilon_decay: Decay factor per episode.
            rng: Random number generator.
        """
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.rng = rng or random.Random()
        self.q_table = defaultdict(lambda: [0.0] * num_actions)
        self.state_visits = defaultdict(int)

    def select_action(self, state):
        """Epsilon-greedy action selection."""
        if self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.num_actions - 1)
        q_values = self.q_table[state]
        max_q = max(q_values)
        best_actions = [a for a, q in enumerate(q_values) if q == max_q]
        return self.rng.choice(best_actions)

    def update(self, state, action, reward, next_state, done):
        """Q-learning update: Q(s,a) += alpha * (reward + gamma * max_Q(s') - Q(s,a))"""
        q_values = self.q_table[state]
        if done:
            target = reward
        else:
            target = reward + self.gamma * max(self.q_table[next_state])

        q_values[action] += self.alpha * (target - q_values[action])
        self.state_visits[state] += 1

    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_policy(self):
        """Extract greedy policy from Q-table."""
        policy = {}
        for state in self.q_table:
            q_values = self.q_table[state]
            max_q = max(q_values)
            best_actions = [a for a, q in enumerate(q_values) if q == max_q]
            policy[state] = best_actions[0]
        return policy


def value_iteration(env, gamma=0.99, theta=1e-6):
    """Compute optimal value function and policy via value iteration."""
    states = [(r, c) for r in range(env.size) for c in range(env.size)]
    V = {s: 0.0 for s in states}
    policy = {s: 0 for s in states}

    while True:
        delta = 0.0
        V_new = deepcopy(V)
        for state in states:
            if env.is_terminal(state):
                continue
            q_values = []
            for action in env.actions:
                next_state, reward, done = env.step(action)
                q_values.append(reward + gamma * V[next_state] * (1 - done))
                env.state = state  # restore state for next action

            V_new[state] = max(q_values)
            best_action = q_values.index(max(q_values))
            policy[state] = best_action
            delta = max(delta, abs(V[state] - V_new[state]))

        V = V_new
        if delta < theta:
            break

    return V, policy


def compute_optimal_q(env, V_opt, gamma=0.99):
    """Compute optimal Q-values from optimal value function."""
    Q_opt = {}
    for state in env.all_states():
        if env.is_terminal(state):
            Q_opt[state] = [0.0] * len(env.actions)
            continue
        q_values = []
        for action in env.actions:
            next_state, reward, done = env.step(action)
            q_values.append(reward + gamma * V_opt[next_state] * (1 - done))
            env.state = state
        Q_opt[state] = q_values
    return Q_opt


def train(agent, env, num_episodes, max_steps=100, rng=None):
    """Train Q-learning agent and return training statistics."""
    rng = rng or random.Random()
    episode_rewards = []
    episode_lengths = []
    successes = 0

    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            action = agent.select_action(state)
            next_state, reward, done = env.step(action)
            agent.update(state, action, reward, next_state, done)
            total_reward += reward
            state = next_state
            steps += 1

        agent.decay_epsilon()
        episode_rewards.append(total_reward)
        episode_lengths.append(steps)
        if env.is_terminal(state):
            successes += 1

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "successes": successes,
        "total_episodes": num_episodes,
        "final_epsilon": round(agent.epsilon, 6),
    }


def policy_accuracy(q_agent, optimal_policy):
    """Compute fraction of states where learned policy matches optimal."""
    q_policy = q_agent.get_policy()
    correct = 0
    total = 0
    for state, opt_action in optimal_policy.items():
        if state in q_policy:
            total += 1
            if q_policy[state] == opt_action:
                correct += 1
    return correct / max(total, 1)


def format_grid(env, q_agent, title="Learned Q-values (best action per state)"):
    """Visualize the learned policy on the grid."""
    action_symbols = {0: "^", 1: ">", 2: "v", 3: "<"}
    lines = [title, "=" * (env.size * 4 + 1)]

    for r in range(env.size):
        row_str = "|"
        for c in range(env.size):
            if (r, c) == env.goal:
                row_str += "  G  |"
            elif (r, c) in env.obstacles:
                row_str += "  #  |"
            elif (r, c) == env.start:
                q_values = q_agent.q_table.get((r, c), [0.0] * len(env.actions))
                best_action = q_values.index(max(q_values))
                row_str += f" S{action_symbols.get(best_action, '?')} |"
            else:
                q_values = q_agent.q_table.get((r, c), [0.0] * len(env.actions))
                best_action = q_values.index(max(q_values))
                max_q = max(q_values)
                row_str += f" {action_symbols.get(best_action, '?')}{max_q:.1f}|"
        lines.append(row_str)
        lines.append("-" * (env.size * 4 + 1))

    return "\n".join(lines)


def format_report(training_stats, env, q_agent, optimal_policy=None,
                  policy_acc=None, optimal_q=None):
    """Format training results as a human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("Q-LEARNING GRIDWORLD RESULTS")
    lines.append("=" * 60)
    lines.append(f"Grid: {env.size}x{env.size} | Obstacles: {len(env.obstacles)}")
    lines.append(f"Start: {env.start} | Goal: {env.goal}")
    lines.append("")

    # Training summary
    rewards = training_stats["episode_rewards"]
    lengths = training_stats["episode_lengths"]
    lines.append("--- Training Summary ---")
    lines.append(f"  Episodes: {training_stats['total_episodes']}")
    lines.append(f"  Successes: {training_stats['successes']}/{training_stats['total_episodes']} "
                 f"({training_stats['successes']/training_stats['total_episodes']*100:.1f}%)")
    lines.append(f"  Final epsilon: {training_stats['final_epsilon']}")
    lines.append(f"  Avg reward (last 100): {sum(rewards[-100:])/min(100, len(rewards)):.3f}")
    lines.append(f"  Avg length (last 100): {sum(lengths[-100:])/min(100, len(lengths)):.1f}")
    lines.append("")

    # Learning curve (checkpoints)
    lines.append("--- Learning Curve (reward, checkpoints) ---")
    checkpoints = [0.1, 0.25, 0.5, 0.75, 1.0]
    header = "  {:<12}".format("Checkpoint") + "".join("@{:>6}  ".format(int(cp * len(rewards))) for cp in checkpoints)
    lines.append(header)
    reward_row = "  Reward      "
    for cp in checkpoints:
        idx = min(int(cp * len(rewards)) - 1, len(rewards) - 1)
        window = rewards[max(0, idx-49):idx+1]
        reward_row += f"{sum(window)/len(window):>6.2f}  "
    lines.append(reward_row)

    success_row = "  Success     "
    for cp in checkpoints:
        idx = min(int(cp * len(lengths)) - 1, len(lengths) - 1)
        window = lengths[max(0, idx-49):idx+1]
        succ = sum(1 for l in window if l < 100)  # reached goal before max_steps
        success_row += f"{succ/len(window)*100:>5.1f}%  "
    lines.append(success_row)
    lines.append("")

    # Policy visualization
    lines.append(format_grid(env, q_agent))
    lines.append("")

    # Comparison to optimal
    if optimal_policy is not None and policy_acc is not None:
        lines.append("--- Comparison to Optimal (Value Iteration) ---")
        lines.append(f"  Policy accuracy: {policy_acc*100:.1f}%")

        # Compute RMS error of Q-values
        if optimal_q:
            rms_errors = []
            for state in env.all_states():
                if state in q_agent.q_table and state in optimal_q:
                    learned = q_agent.q_table[state]
                    optimal = optimal_q[state]
                    rms_errors.append(sum((l - o) ** 2 for l, o in zip(learned, optimal))
                                      / len(learned))
            if rms_errors:
                lines.append(f"  Q-value RMS error (avg): {sum(rms_errors)/len(rms_errors):.4f}")

        # Optimal policy visualization
        opt_agent = QLearningAgent(len(env.actions))
        for state, action in optimal_policy.items():
            opt_agent.q_table[state][action] = 1.0  # mark optimal action
        lines.append("")
        lines.append(format_grid(env, opt_agent, "Optimal Policy (Value Iteration)"))
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Q-Learning Agent for Gridworld",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--size", type=int, default=4, help="Grid size (default: 4)")
    parser.add_argument("--obstacles", type=int, default=2, help="Number of random obstacles (default: 2)")
    parser.add_argument("--episodes", type=int, default=2000, help="Training episodes (default: 2000)")
    parser.add_argument("--alpha", type=float, default=0.1, help="Learning rate (default: 0.1)")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor (default: 0.99)")
    parser.add_argument("--epsilon", type=float, default=1.0, help="Initial epsilon (default: 1.0)")
    parser.add_argument("--epsilon-min", type=float, default=0.01, help="Minimum epsilon (default: 0.01)")
    parser.add_argument("--epsilon-decay", type=float, default=0.998, help="Epsilon decay per episode (default: 0.998)")
    parser.add_argument("--max-steps", type=int, default=100, help="Max steps per episode (default: 100)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--compare-optimal", action="store_true",
                        help="Compare learned policy to optimal (value iteration)")

    args = parser.parse_args()
    rng = random.Random(args.seed)

    # Generate random obstacles (avoiding start and goal)
    obstacles = set()
    available = [(r, c) for r in range(args.size) for c in range(args.size)
                 if (r, c) != (0, 0) and (r, c) != (args.size - 1, args.size - 1)]
    obstacles = set(rng.sample(available, min(args.obstacles, len(available))))

    env = GridWorld(size=args.size, obstacles=obstacles, rng=rng)
    agent = QLearningAgent(
        num_actions=len(env.actions),
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        rng=rng,
    )

    # Train
    training_stats = train(agent, env, args.episodes, args.max_steps, rng)

    # Optional: compare to optimal
    optimal_policy = None
    policy_acc = None
    optimal_q = None
    if args.compare_optimal:
        vi_env = GridWorld(size=args.size, obstacles=obstacles.copy(), rng=random.Random(42))
        V_opt, optimal_policy = value_iteration(vi_env, gamma=args.gamma)
        optimal_q = compute_optimal_q(vi_env, V_opt, gamma=args.gamma)
        policy_acc = policy_accuracy(agent, optimal_policy)

    if args.json:
        output = {
            "config": vars(args),
            "obstacles": [list(o) for o in obstacles],
            "training": {
                k: v for k, v in training_stats.items()
                if k not in ("episode_rewards", "episode_lengths")
            },
            "learning_curve": {
                "rewards_checkpoints": {},
                "lengths_checkpoints": {},
            },
            "policy_accuracy": policy_acc,
        }

        rewards = training_stats["episode_rewards"]
        lengths = training_stats["episode_lengths"]
        for cp_label, cp in [("10pct", 0.1), ("25pct", 0.25),
                              ("50pct", 0.5), ("75pct", 0.75), ("100pct", 1.0)]:
            idx = min(int(cp * len(rewards)) - 1, len(rewards) - 1)
            window = rewards[max(0, idx-49):idx+1]
            output["learning_curve"]["rewards_checkpoints"][cp_label] = round(sum(window)/len(window), 4)

            lidx = min(int(cp * len(lengths)) - 1, len(lengths) - 1)
            lwindow = lengths[max(0, lidx-49):lidx+1]
            output["learning_curve"]["lengths_checkpoints"][cp_label] = round(sum(lwindow)/len(lwindow), 2)

        # Q-table summary (top states by max Q-value)
        q_summary = {}
        for state in env.all_states():
            if state in agent.q_table:
                q_summary[str(state)] = {
                    "q_values": [round(q, 4) for q in agent.q_table[state]],
                    "best_action": agent.q_table[state].index(max(agent.q_table[state])),
                    "visits": agent.state_visits.get(state, 0),
                }
        output["q_table_summary"] = q_summary

        print(json.dumps(output, indent=2))
    else:
        report = format_report(training_stats, env, agent,
                               optimal_policy=optimal_policy,
                               policy_acc=policy_acc,
                               optimal_q=optimal_q)
        print(report)


if __name__ == "__main__":
    main()
