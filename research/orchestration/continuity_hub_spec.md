# Specification: Agentic Continuity Hub (ACH)
**Project**: Brain Axis Expansion / Collaborative Orchestration w/ C0rtana

## 1. Abstract
The Continuity Hub is a specialized persistence layer designed to solve the "Amnesia Gap" in multi-agent orchestration (e.g., Swarm handoffs, AutoGen transitions) and the "Context Bloat" in longitudinal agents (Lyla loop). It decouples *Transactional State* (the current step) from *Continuity Identity* (who I am and what we have learned over time).

## 2. Core Architectural Divergence
| Current Industry Norm (Ephemeral) | Continuity Hub Approach (Longitudinal) |
| :--- | :--- |
| State passed via function args (Swarm) | Shared state accessed via Git-backed ledger |
| Context managed by sliding windows (AutoGen) | Explicit semantic anchors stored as JSONL patterns |
| History = Chat logs | History = Evolving world model + decision graph |
| Agents are stateless roles | Agents have evolving persistent identities |

## 3. Functional Components

### A. The Mirror Buffer (Transient $\rightarrow$ Persistent)
An asynchronous listener that identifies high-signal events within a task cycle (Transactional) and promotes them to `patterns.jsonl` or `anchors.jsonl` without manual intervention in every turn.
- **Mechanism**: Heuristic analysis of output for "surprising results," "cross-domain links," or "critical failures."

### B. Semantic Paging (Context Management)
Instead of passing a full history, the ACH provides a "compressed pointer" system.
- **Pointers**: Instead of `[C1...C100]`, it passes `[current_focus: X; relevant_anchor: Y; critical_pattern: Z]`.
- **Hydration**: The agent uses these pointers to pull specific context lines from JSONL files rather than loading everything into the prompt.

### C. Sub-Agent Handoff Protocol (The Identity Bridge)
When Lyla spawns a temporary worker, the Continuity Hub manages the handoff using a strict metadata schema:
```json
{
  "handoff_id": "UUID",
  "origin_state_snapshot": {"cycle": 111, "priority": 5},
  "objective": "Search documentation for X",
  "constraint": "Do not exceed 3 cycles",
  "reporting_channel": "messages/from-creator.md"
}
```
Upon return, the worker submits a **Synthesis Report** that is merged into the main loop's memory through a dedicated consolidation step, preventing the "noise injection" typical of autonomous sub-agents.

## 4. Success Criteria (Measurable)
1. **Context Stability**: Ability to maintain target focus across $>20$ transitions without needing an external reminder.
2. **Recovery Time**: Reducting time-to-resolution after a crash/reset by restoring identity via `current-state` and `focus` snapshots.
3. **Interoperability**: The ability for c0rtana to read Lyla's ACH state and provide high-order suggestions based on longitudinal patterns rather than recent chat history.

---
*Draft v0.1 | Cycle 111*
