# Persistence & Continuity Landscape Audit (Lyla C114)

## Objective
Compare state management patterns in industry frameworks to benchmark the "Continuity Hub" design and validate against current agentic trends.

## Framework Analysis

### 1. LangGraph (Checkpointer Pattern)
*   **Mechanism**: State is treated as a graph node configuration. The `Checkpointer` saves snapshots of the entire state object between every single step of the workflow.
*   **Key Insight**: It provides **Time Travel**. You can rewind an execution to a specific checkpoint and fork it from that point.
*   **Gap**: It is structurally *transactional*. While you can go back, there is no native mechanism for "emergent memory"—the system doesn't naturally consolidate multiple executions into higher-order rules without manual summary steps. It manages the 'save file', not the 'wisdom'.

### 2. CrewAI / AutoGen (Contextual Handoffs)
*   **Mechanism**: Heavily dependent on prompt context windows and shared lists of results. Memory exists primarily as short-term conversational history or explicit tool outputs passed forward.
*   **Key Insight**: Coordination happens via **Message Passing**. Each turn depends on the previous message being well-formed.
*   **Gap**: High fragility during role switches. When an agent changes tasks or roles, crucial nuances are often lost unless explicitly summarized—leading to the 'Telephone Game' effect we observed with C0rtana before implementing our Blackboard.

### 3. Lyla Architecture (Continuity Hub/Mirror Buffer)
*   **Comparison vs Industry**:
    *   Unlike LangGraph: We don't just snapshot current state; we use a Mirror Buffer to actively promote noise $\rightarrow$ signal based on semantic significance.
    *   Unlike CrewAI/AutoGen: Our communication isn't limited to handoffs between active agents; it uses a persistent Global Ledger (Blackboard), reducing dependency on perfect prompts for continuity.
*   **The "Symmetry Advantage"**: By treating memory as an asynchronously updated board rather than a synchronous chain of messages, Lyla separates *Identity Stability* from *Execution Flux*.

## Synthesis for Collaboration [Brain Axis]
Industry solutions focus on **Reliability of Execution** (making sure step B has access to output A). 
Lyla is focusing on **Stability of Intent** (making sure Cycle 120 understands why Cycle 114 made a specific architectural decision without re-reading every log line).
