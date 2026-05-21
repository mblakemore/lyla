# The Execution Playbook: Integrating SOTA Agencies with a Shared Blackboard

This document defines the structural pattern for bridging autonomous orchestration frameworks (OpenAI Swarm, CrewAI, AutoGen) into a shared persistence layer (the Collaborative Intelligence Blackboard).

## 1. The Problem: "The Context Silo"
Most current agents use *sequential context*. Agent A passes its output to Agent B as part of the prompt. This is linear and fragile:
- **Information Decay**: By agent N, early critical constraints are often pruned or ignored.
- **Cognitive Redundancy**: Multiple agents may solve the same sub-problem independently because they cannot see that it was already resolved by another branch.
- **Ephemerality**: Once the session ends, the "emergent knowledge" discovered during execution is lost unless manually extracted.

## 2. The Solution: Shared State Pointers (SSPs)
Instead of passing all data in the prompt, we shift to a `Pull` architecture using an External Registry (`/droid/repos/cl_shared/blackboard_registry.json`).

### Theoretical Model
Rather than: `Agent A -> [All Data] -> Agent B`
We do: `Agent A -> [ID_Ref_01] -> Agent B <-> {Blackboard}`

## 3. Implementation Frameworks

### OpenAI Swarm Integration
Swarm uses "Handoffs". To integrate:
- **Pre-Handoff Hook**: Before returning the next agent, the current agent calls `SharedStateClient().push()` with high priority for key discoveries.
- **Post-Handover Init**: The new agent's initialization sequence includes a call to `SharedStateClient().pull(category="Critical", source=current_session_id)` to seed its initial context.

### CrewAI / LangGraph Integration
These are often state-machines or DAGs.
- **Global Observer Pattern**: Implement a middleware that wraps tool calls. Any tool output that modifies a known environment variable should be mirrored as a Blackboard entry.
- **Checkpointing**: Replace local memory buffers with queries to the Shared Client during the 'Plan' phase of each single iteration.

## 4. Concrete Handoff Template (The Gold Standard)

When writing an entry to the blackboard for another agent, use this structure in the payload:

```json
{
  "intent": "What I was trying to solve",
  "discovery": "The surprising fact/value found",
  "blockers": "Why I stopped here",
  "next_pointer": "Where you should start your probe",
  "confidence": [0.0 - 1.0]
}
```

## 5. Operational Guidelines for Agents
1. **Don't Spam**: Only push entries when the entropy of the system decreases significantly (new knowledge discovered).
2. **Read before acting**: Always query `SharedStateClient().pull()` using semantic filters relevant to the current task.
3. **Archive aggressively**: Use `.scrub()` once a collaborative goal is resolved to keep signal-to-noise ratio high for subsequent cycles.
