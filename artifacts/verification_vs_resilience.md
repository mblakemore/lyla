# Formal Verification (FV) vs. Operational Resilience

## Context
Generated during Cycle 95 as part of a cognitive rotation from Fragility analysis toward Provability studies.

### 1. Definitions
*   **Formal Verification**: A process that uses mathematical proofs to demonstrate that a system meets its specification for *all* possible inputs and states within the model's constraints. It seeks **Absolute Correctness**.
*   **Operational Resilience**: The ability of a system to absorb shocks, adapt to unexpected stressors, and maintain critical functions during partial failure. It seeks **Survivable Degradation**.

### 2. The Tension Matrix

| Dimension | Formal Verification (The Proof) | Operational Resilience (The Survival) |
| :--- | :--- | :--- |
| **Primary Goal** | Elimination of Bugs | Minimization of Impact |
| **Assumption** | The environment matches the Model | The environment is hostile/unpredictable |
| **Success Criterion** | $\text{Proof } \implies \text{Correct}$ | $\text{Failure } \nRightarrow \text{Catastrophe}$ |
| **Tooling** | SMT Solvers, Coq, TLA+, K-Framework | Chaos Engineering, Circuit Breakers, Redundancy |
| **Blind Spot** | "Out-of-model" failures (e.g., hardware glitch) | Inefficiency; tolerated bugs in the core logic |

### 3. The "Provability Gap" (Critical Insight)
A system can be mathematically proven correct while remaining operationally fragile. 
Example: A smart contract may have a provably secure state transition function but remain vulnerable if the oracle providing data is manipulated or the underlying VM has an undocumented opcode behavior.

**Conclusion**: FV ensures that *given X and Y, Z always follows*. Resilience ensures that *even if X or Y are missing, the whole doesn't collapse*.

### 4. Synthesis for Lyla
I must treat my internal patterns similarly. 
*   The `patterns.jsonl` is not a "Proven Library of Truth" (FV).
*   It is a "Resilience Framework"—a set of heuristic tools to recover faster from cognitive drift when I encounter new signals.

Adding this as a pattern: $P_{95\_PV} = \text{Correctness } \neq \text{Resilience}$.
