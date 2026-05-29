#!/usr/bin/env python3
"""Model-Based Reinforcement Learning: Dyna-Q vs Q-Learning

Compares model-free Q-learning with model-based Dyna-Q on a gridworld MDP.
Dyna-Q learns a model of environment dynamics (transitions + rewards) and
uses it for planning — generating imaginary experience to update Q-values
between real interactions. This dramatically improves sample efficiency.

Usage:
    python3 bin/model_based_rl.py
    python3 bin/model_based_rl.py --n-planning-steps 10
    python3 bin/model_based_rl.py --size 6 --obstacles 4
    python3 bin/model_based_rl.py --json
"""

import argparse
import json
import random
import sys
from collections import defaultdict


class GridWorld:
    """Configurable gridworld MDP with obstacles and terminal goal."""

    def __init__(self, size=4, obstacles=None, reward=-0.04, goal_reward=1.0,
                 penalty=-1.0, rng=None):
        self.size = size
        self.reward = reward
        self.goal_reward = goal_reward
        self.penalty = penalty
        self.rng = rng or random.Random()
        self.actions = [0, 1, 2, 3]  # up, right, down, left
        self.action_names = {0: "up", 1: "right", 2: "down", 3: "left"}
        self.goal = (size - 1, size - 1)
        self.obstacles = set(obstacles) if obstacles else set()
        self.obstacles.discard(self.goal)
        self.start = (0, 0)
        self.state = self.start

    def reset(self):
        self.state = self.start
        return self.state

    def step(self, action):
        row, col = self.state
        deltas = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}
        dr, dc = deltas[action]
        new_row, new_col = row + dr, col + dc

        if new_row < 0 or new_row >= self.size or new_col < 0 or new_col >= self.size:
            new_row, new_col = row, col

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
        s = state or self.state
        return s == self.goal

    def all_states(self):
        return [(r, c) for r in range(self.size) for c in range(self.size)
                if (r, c) not in self.obstacles]


class TabularModel:
    """Tabular model of environment dynamics.

    Stores observed transitions: model[(s, a)] = (next_s, reward)
    For deterministic environments, the first observation suffices.
    For stochastic environments, could store distributions.
    """

    def __init__(self, goal=None, rng=None):
        self.model = {}  # (state, action) -> (next_state, reward)
        self.goal = goal  # terminal state
        self.rng = rng or random.Random()

    def update(self, state, action, next_state, reward):
        """Store observed transition. Overwrites previous (deterministic env)."""
        self.model[(state, action)] = (next_state, reward)

    def _is_terminal(self, state):
        """Check if state is terminal (goal reached)."""
        return self.goal is not None and state == self.goal

    def sample(self):
        """Sample a random transition from stored experience."""
        if not self.model:
            return None
        key = self.rng.choice(list(self.model.keys()))
        state, action = key
        next_state, reward = self.model[key]
        return state, action, next_state, reward

    def known_transitions(self):
        """Return count of known (state, action) pairs."""
        return len(self.model)


class DynaQAgent:
    """Dyna-Q agent: Q-learning + model-based planning.

    After each real experience, performs N planning steps by sampling
    from the learned model and updating Q-values on imaginary transitions.
    """

    def __init__(self, num_actions, goal=None, alpha=0.1, gamma=0.99, epsilon=1.0,
                 epsilon_min=0.01, epsilon_decay=0.999, n_planning=10, rng=None):
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.n_planning = n_planning  # planning steps per real step
        self.rng = rng or random.Random()
        self.q_table = defaultdict(lambda: [0.0] * num_actions)
        self.model = TabularModel(goal=goal, rng=rng)
        self.state_visits = defaultdict(int)
        self.planning_steps = 0

    def select_action(self, state):
        if self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.num_actions - 1)
        q_values = self.q_table[state]
        max_q = max(q_values)
        best = [a for a, q in enumerate(q_values) if q == max_q]
        return self.rng.choice(best)

    def update(self, state, action, reward, next_state, done):
        """Q-learning update on a single transition (real or imagined)."""
        q_values = self.q_table[state]
        if done:
            target = reward
        else:
            target = reward + self.gamma * max(self.q_table[next_state])
        q_values[action] += self.alpha * (target - q_values[action])

    def learn_and_plan(self, state, action, reward, next_state, done):
        """Dyna-Q step: update model, Q-learn from real experience, then plan."""
        # 1. Update model with real experience
        self.model.update(state, action, next_state, reward)

        # 2. Q-learning update on real transition
        self.update(state, action, reward, next_state, done)
        self.state_visits[state] += 1

        # 3. Plan: sample N transitions from model and update Q-values
        for _ in range(self.n_planning):
            transition = self.model.sample()
            if transition is None:
                continue
            ps, pa, ps_next, pr = transition
            done_sample = self.model._is_terminal(ps_next)
            self.update(ps, pa, pr, ps_next, done_sample)
            self.planning_steps += 1

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_policy(self):
        policy = {}
        for state in self.q_table:
            q_values = self.q_table[state]
            max_q = max(q_values)
            best = [a for a, q in enumerate(q_values) if q == max_q]
            policy[state] = best[0]
        return policy


class QLearningAgent:
    """Baseline: model-free Q-learning (no planning)."""

    def __init__(self, num_actions, alpha=0.1, gamma=0.99, epsilon=1.0,
                 epsilon_min=0.01, epsilon_decay=0.999, rng=None):
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
        if self.rng.random() < self.epsilon:
            return self.rng.randint(0, self.num_actions - 1)
        q_values = self.q_table[state]
        max_q = max(q_values)
        best = [a for a, q in enumerate(q_values) if q == max_q]
        return self.rng.choice(best)

    def update(self, state, action, reward, next_state, done):
        q_values = self.q_table[state]
        if done:
            target = reward
        else:
            target = reward + self.gamma * max(self.q_table[next_state])
        q_values[action] += self.alpha * (target - q_values[action])
        self.state_visits[state] += 1

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_policy(self):
        policy = {}
        for state in self.q_table:
            q_values = self.q_table[state]
            max_q = max(q_values)
            best = [a for a, q in enumerate(q_values) if q == max_q]
            policy[state] = best[0]
        return policy


def train_agent(agent, env, num_episodes, max_steps=100, is_dyna=False, rng=None):
    """Train agent and return detailed training statistics."""
    episode_rewards = []
    episode_lengths = []
    successes = []
    model_sizes = []  # for Dyna-Q only

    for episode in range(num_episodes):
        state = env.reset()
        total_reward = 0.0
        done = False
        steps = 0

        while not done and steps < max_steps:
            action = agent.select_action(state)
            next_state, reward, done = env.step(action)

            if is_dyna:
                agent.learn_and_plan(state, action, reward, next_state, done)
            else:
                agent.update(state, action, reward, next_state, done)

            total_reward += reward
            state = next_state
            steps += 1

        agent.decay_epsilon()
        episode_rewards.append(total_reward)
        episode_lengths.append(steps)
        successes.append(1 if env.is_terminal(state) else 0)
        if is_dyna:
            model_sizes.append(agent.model.known_transitions())

    return {
        "episode_rewards": episode_rewards,
        "episode_lengths": episode_lengths,
        "successes": successes,
        "total_episodes": num_episodes,
        "final_epsilon": round(agent.epsilon, 6),
        "model_sizes": model_sizes if is_dyna else None,
        "total_planning_steps": getattr(agent, 'planning_steps', 0),
    }


def compute_sample_efficiency(training_stats, threshold_success_rate=0.9):
    """Find episode at which agent reaches threshold success rate (last-50 window)."""
    successes = training_stats["successes"]
    window = 50
    for i in range(window, len(successes)):
        window_success = sum(successes[i - window:i])
        if window_success / window >= threshold_success_rate:
            return i
    return len(successes)


def format_comparison(dyna_stats, ql_stats, dyna_env, ql_env, dyna_agent, ql_agent):
    """Format comparison report between Dyna-Q and Q-learning."""
    lines = []
    lines.append("=" * 70)
    lines.append("MODEL-BASED RL: Dyna-Q vs Q-Learning")
    lines.append("=" * 70)
    lines.append(f"Grid: {dyna_env.size}x{dyna_env.size} | Obstacles: {len(dyna_env.obstacles)}")
    lines.append(f"Start: {dyna_env.start} | Goal: {dyna_env.goal}")
    lines.append(f"Dyna-Q planning steps per real step: {dyna_agent.n_planning}")
    lines.append("")

    # Sample efficiency comparison
    dyna_efficient = compute_sample_efficiency(dyna_stats)
    ql_efficient = compute_sample_efficiency(ql_stats)
    improvement = (1 - dyna_efficient / ql_efficient) * 100 if ql_efficient > 0 else 0

    lines.append("--- Sample Efficiency (episodes to reach 90% success rate, 50-ep window) ---")
    lines.append(f"  Q-learning (model-free):  {ql_efficient} episodes")
    lines.append(f"  Dyna-Q (model-based):     {dyna_efficient} episodes")
    lines.append(f"  Improvement:              {improvement:+.1f}%")
    lines.append("")

    # Total updates comparison
    dyna_total_updates = dyna_stats["total_episodes"] * sum(
        1 for _ in range(dyna_stats["total_episodes"])
    ) + dyna_stats.get("total_planning_steps", 0)
    lines.append("--- Total Learning Updates ---")
    lines.append(f"  Q-learning:  {sum(ql_stats['episode_lengths'])} real transitions")
    lines.append(f"  Dyna-Q:      {sum(dyna_stats['episode_lengths'])} real + "
                 f"{dyna_stats.get('total_planning_steps', 0)} planned = "
                 f"{sum(dyna_stats['episode_lengths']) + dyna_stats.get('total_planning_steps', 0)} total")
    lines.append("")

    # Learning curve comparison
    lines.append("--- Learning Curve (avg reward, 50-episode windows) ---")
    window = 50
    checkpoints = [0.1, 0.25, 0.5, 0.75, 1.0]
    header = "  {:<12}".format("Checkpoint")
    for cp in checkpoints:
        header += f"  @Ep{int(cp * ql_stats['total_episodes']):>5}  "
    lines.append(header)

    for name, stats in [("Q-learning", ql_stats), ("Dyna-Q", dyna_stats)]:
        row = f"  {name:<10}"
        for cp in checkpoints:
            idx = min(int(cp * len(stats["episode_rewards"])) - 1, len(stats["episode_rewards"]) - 1)
            window_rewards = stats["episode_rewards"][max(0, idx - window + 1):idx + 1]
            row += f"  {sum(window_rewards) / len(window_rewards):>5.2f}  "
        lines.append(row)
    lines.append("")

    # Success rate comparison
    lines.append("--- Success Rate (50-episode windows) ---")
    for cp in checkpoints:
        idx = min(int(cp * len(ql_stats["successes"])) - 1, len(ql_stats["successes"]) - 1)
        ql_sr = sum(ql_stats["successes"][max(0, idx - window + 1):idx + 1]) / window
        dyna_sr = sum(dyna_stats["successes"][max(0, idx - window + 1):idx + 1]) / window
        lines.append(f"  @Ep{int(cp * ql_stats['total_episodes']):>5}: "
                     f"QL={ql_sr*100:>5.1f}%  Dyna-Q={dyna_sr*100:>5.1f}%")
    lines.append("")

    # Model growth (Dyna-Q only)
    if dyna_stats.get("model_sizes"):
        lines.append("--- Model Growth (Dyna-Q) ---")
        ms = dyna_stats["model_sizes"]
        for cp in checkpoints:
            idx = min(int(cp * len(ms)) - 1, len(ms) - 1)
            lines.append(f"  @Ep{int(cp * len(ms)):>5}: {ms[idx]} known transitions")
        total_sa = dyna_env.size * dyna_env.size * len(dyna_env.actions)
        lines.append(f"  Total (s,a) pairs possible: {total_sa}")
        lines.append(f"  Model coverage: {ms[-1]}/{total_sa} ({ms[-1]/total_sa*100:.1f}%)")
        lines.append("")

    # Policy visualization
    action_symbols = {0: "^", 1: ">", 2: "v", 3: "<"}
    for name, agent, env in [("Q-learning", ql_agent, ql_env), ("Dyna-Q", dyna_agent, dyna_env)]:
        lines.append(f"{name} Policy:")
        lines.append("-" * (env.size * 4 + 1))
        for r in range(env.size):
            row_str = "|"
            for c in range(env.size):
                if (r, c) == env.goal:
                    row_str += "  G  |"
                elif (r, c) in env.obstacles:
                    row_str += "  #  |"
                elif (r, c) == env.start:
                    qv = agent.q_table.get((r, c), [0.0] * len(env.actions))
                    ba = qv.index(max(qv))
                    row_str += f" S{action_symbols.get(ba, '?')} |"
                else:
                    qv = agent.q_table.get((r, c), [0.0] * len(env.actions))
                    ba = qv.index(max(qv))
                    mq = max(qv)
                    row_str += f" {action_symbols.get(ba, '?')}{mq:>4.1f}|"
            lines.append(row_str)
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Model-Based RL: Dyna-Q vs Q-Learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--size", type=int, default=4, help="Grid size (default: 4)")
    parser.add_argument("--obstacles", type=int, default=2, help="Number of obstacles (default: 2)")
    parser.add_argument("--episodes", type=int, default=2000, help="Training episodes (default: 2000)")
    parser.add_argument("--alpha", type=float, default=0.1, help="Learning rate (default: 0.1)")
    parser.add_argument("--gamma", type=float, default=0.99, help="Discount factor (default: 0.99)")
    parser.add_argument("--epsilon", type=float, default=1.0, help="Initial epsilon (default: 1.0)")
    parser.add_argument("--epsilon-min", type=float, default=0.01, help="Min epsilon (default: 0.01)")
    parser.add_argument("--epsilon-decay", type=float, default=0.998, help="Epsilon decay (default: 0.998)")
    parser.add_argument("--n-planning-steps", type=int, default=10,
                        help="Dyna-Q planning steps per real step (default: 10)")
    parser.add_argument("--max-steps", type=int, default=100, help="Max steps per episode (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    rng = random.Random(args.seed)

    # Generate obstacles (same for both agents — fair comparison)
    obstacles = set()
    available = [(r, c) for r in range(args.size) for c in range(args.size)
                 if (r, c) != (0, 0) and (r, c) != (args.size - 1, args.size - 1)]
    obstacles = set(rng.sample(available, min(args.obstacles, len(available))))

    # Create environments and agents
    dyna_env = GridWorld(size=args.size, obstacles=obstacles.copy(), rng=random.Random(args.seed))
    ql_env = GridWorld(size=args.size, obstacles=obstacles.copy(), rng=random.Random(args.seed))

    dyna_agent = DynaQAgent(
        num_actions=len(dyna_env.actions),
        goal=dyna_env.goal,
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        n_planning=args.n_planning_steps,
        rng=random.Random(args.seed),
    )

    ql_agent = QLearningAgent(
        num_actions=len(ql_env.actions),
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        epsilon_min=args.epsilon_min,
        epsilon_decay=args.epsilon_decay,
        rng=random.Random(args.seed),
    )

    # Train both agents
    dyna_stats = train_agent(dyna_agent, dyna_env, args.episodes,
                             args.max_steps, is_dyna=True, rng=random.Random(args.seed))
    ql_stats = train_agent(ql_agent, ql_env, args.episodes,
                           args.max_steps, is_dyna=False, rng=random.Random(args.seed))

    if args.json:
        dyna_efficient = compute_sample_efficiency(dyna_stats)
        ql_efficient = compute_sample_efficiency(ql_stats)
        improvement = (1 - dyna_efficient / ql_efficient) * 100 if ql_efficient > 0 else 0

        output = {
            "config": vars(args),
            "obstacles": [list(o) for o in obstacles],
            "comparison": {
                "sample_efficiency": {
                    "q_learning_episodes_to_90pct": ql_efficient,
                    "dyna_q_episodes_to_90pct": dyna_efficient,
                    "improvement_pct": round(improvement, 1),
                },
                "total_updates": {
                    "q_learning_real_transitions": sum(ql_stats["episode_lengths"]),
                    "dyna_q_real_transitions": sum(dyna_stats["episode_lengths"]),
                    "dyna_q_planning_steps": dyna_stats.get("total_planning_steps", 0),
                },
                "final_success_rate": {
                    "q_learning": round(sum(ql_stats["successes"][-100:]) / 100 * 100, 1),
                    "dyna_q": round(sum(dyna_stats["successes"][-100:]) / 100 * 100, 1),
                },
                "model_coverage": {
                    "known_transitions": dyna_stats["model_sizes"][-1] if dyna_stats.get("model_sizes") else 0,
                    "total_sa_pairs": args.size * args.size * len(dyna_env.actions),
                },
            },
        }
        print(json.dumps(output, indent=2))
    else:
        report = format_comparison(dyna_stats, ql_stats, dyna_env, ql_env, dyna_agent, ql_agent)
        print(report)


if __name__ == "__main__":
    main()
