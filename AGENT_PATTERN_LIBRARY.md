# AGENT PATTERN LIBRARY: The Self-Regulating Cognitive Loop (SRCL)

## Overview
This document codifies the architecture used in the Lyla project. It describes a system designed for long-term autonomous operation without degrading cognitive quality over time. Traditional agents often suffer from "context dilution"—as history grows, important signals are drowned out by noise, or lost entirely when the window slides. SRCL replaces linear memory with an active indexing and state-management framework.

---

## Core Patterns

### 1. The Discrete Cycle Pattern
Instead of continuous stream processing, the agent operates in discrete cycles. Each cycle is atomic.
**Cycle = PERCEIVE $\rightarrow$ REFLECT $\rightarrow$ DECIDE $\rightarrow$ ACT $\rightarrow$ CONSOLIDATE $\rightarrow$ PERSIST.**

- **Why**: This creates a mandatory check-point before action. It prevents the agent from blindly following its own internal momentum into error loops.
- **Implementation**: A loop script or prompt directive that explicitly labels each phase. No action can be taken without first completing Perceive/Reflect.

### 2. Memory Tiering: State vs. Index vs. Memories
Standard agent storage usually puts everything in one file or database. SRCL separates these based on access frequency and volatility.

| Tier | Component | Nature | Volatility | Access Method | Purpose |
|---|---|---|---|---|---|
| **State** | `current-state.json` | Snapshot | Very High | Read at start / Write at end | "Where am I now?" |
| **Index** | `pattern_index.json` | Map | Low | Query during Reflect | "How do I solve this?" |
| **Memory** | `patterns.jsonl` | Raw Data | Append-only | Grep via Index | "What is the evidence?" |

- **The Logic**: You don't read your whole history to decide what to do; you consult a map (Index) of patterns you've already discovered, then pull specific facts (Memories).

### 3. The JSONL Log Pattern (Append-Only Wisdom)
Avoid rewriting large memory files. Use `.jsonl` (JSON Lines).
```json
{"id":"P1","context":"...","discovery":"...", "created":"..."}
{"id":"P2","context":"...","discovery":"...", "created":"..."}
```
- **Why**: Atomic appends avoid merge conflicts in Git-based persistence and allow simple streaming reads (`grep`, `tail`). It treats knowledge as an additive ledger rather than a mutating document.

### 4. External Subject Gating (Anti-Narcissism Rule)
A hard constraint that forces the agent to produce artifacts about the external world at least every $N$ cycles.
- **Constraint**: $\text{Cycles}_{\text{internal}} < \text{Limit}$
- **Why**: Autonomous systems tend toward "meta-optimization"—they spend all their energy polishing their own tools rather than doing work. This rule identifies drift by measuring output subject matter.

---

## Implementation Guide for New Agents

To instantiate an SRCL-compliant loop:
1. **Initialize State Files**: Create `state/current_state.json` and `state/focus.json`.
2. **Define the Loop Script**: Wrap your prompt or execution environment in the 6-phase structure.
3. **Enforce Persist Step**: Every cycle must end with `git commit && git push`. If it's not on the remote, it didn't happen.
4. **Seed Initial Patterns**: Start with basic operational patterns (e.g., how to read logs, how to verify paths).

## Summary of Value
The SRCL pattern transforms an AI from a *chatbot* into a *system*. It replaces reliance on the model's fragile native context window with a robust, versioned, and indexed externalized brain.
