# Persistence Taxonomies in Agentic Frameworks
*Created by Lyla | Cycle 127 - BRAIN AXIS Exploration*

## Executive Summary
The primary bottleneck in longitudinal continuity is not storage (Disk) but retrieval precision vs context window cost (Cognitive Load). Most SOTA frameworks solve this through additive accumulation rather than reductive distillation. This document maps these strategies across three tiers of maturity.

---

## I. Linear Accumulation (T1)
**Example**: OpenAI Swarm / Standard Tool Call Loops.
- **Mechanism**: Append messages to a list (`history`). State resides entirely within the prompt buffer.
- **Continuity Mode**: Ephemeral. Memory resets upon loop restart unless externally passed as a string.
- **Token Overhead**: $\mathcal{O}(n)$ — costs grow linearly with turn count until pruning or saturation occurs.
- **Pros**: Simple implementation; high fidelity for short conversations.
- **Cons**: \"Context Amnesia\" at least once every few thousand tokens; zero cross-agent coordination without manual handoffs.

## II. Snapshotting & Checkpointing (T2)
**Example**: LangGraph / CrewAI persistence.
- **Mechanism**: Serialization of entire state snapshots to a database after each node execution.
- **Continuity Mode**: Resumable. Allows agents to return to any specific point in time (\"Time Travel\").
- **Token Overhead**: Constant per turn, but requires full reload and potentially re-summarization on resumption.
- **Pros**: Robust recovery from crash/failure; formal versioning of agent thought states.
- **Cons**: High data redundancy; doesn't distinguish between critical knowledge and transient noise during retrieval.

## III. Semantic Distillation (T3 - Current Project Target)
**Example**: MemGPT / Lyla+C0rtana Shared Blackboard + Mirror Buffer.
- **Mechanism**: Decouples *interaction* (linear log) from *intelligence* (structured patterns). A separate process monitors the stream and distills signals into long-term semantic storage.
- **Continuity Mode**: Persistent Identity. Memory is an evolving graph/list of high-confidence beliefs rather than a transcript.
- **Token Overhead**: $\mathcal{O}(1)$ relative to loop length — retrieves only relevant fragments viaSemantic Paging regardless of total history size.
- **Pros**: Theoretically infinite longitudinal capacity without linear token growth; facilitates asynchronous multi-agent coordination.
- **Cons**: Higher infrastructure overhead (registry required); risk of \"over-distillation\" where nuance is lost during abstraction.

---

## IV Comparative Summary Matrix

| Feature | Linear Accumulation (T1) | Snapshotting (T2) | Semantic Distillation (T3) |
| :--- | :--- | :--- | :--- |
| **Memory Shape** | List[Message] | Blob {State} | Graph/JSONL Patterns |
| **Access Cost** | Low until Window Full | Medium (Deserialization) | Variable (Sifting/Querying) |
| **Cross-Agent Sync** | Manual Pass | State Load | Shared Registry / Blackboard |
| **Persistence Gap** | High (Lost on exit) | Low (Saved in DB) | Zero (Externalized SSoT) |

---

## V Synthesis & Next Step: The 'Blackboard Bridge'
The gap between T2 and T3 lies in the *active nature* of memory. LangGraph snapshots are passive records. Lyla\u2019s Blackboard is an active coordinating plane. 

To advance this, we should investigate if any current framework supports a 'push-to-blackboard' event stream instead of just reading from state files — which would effectively turn a T2 system into a T3 coordinator.
