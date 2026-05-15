# Research Report: Disruption Tolerant Networking (DTN) and the Bundle Protocol v7

## Subject Overview
**Disruption Tolerant Networking (DTN)** is an architecture designed to enable communication in environments where traditional TCP/IP fails—specifically where there are long delays (high latency), intermittent connectivity (disruptions), or high error rates. The primary implementation of this architecture is the **Bundle Protocol (BP)**, currently standardized as BPv7 (RFC 9171).

### Core Mechanism: Store-and-Forward
Unlike the end-to-end connectivity model of the standard Internet, DTN utilizes a "store-and-forward" approach. In this model, data units called **bundles** are moved from one node to another. If no next-hop exists, the current node stores the bundle in non-volatile storage indefinitely (or until it expires) rather than dropping the packet and requiring a retransmission from the source.

### Key Architectural Components
1.  **Bundles**: The fundamental unit of transfer. Bundles encapsulate application data and metadata (lifetimes, priority, destination endpoints).
2.  **Convergence Layers (CLs)**: Since BP sits *above* various transport layers, CLs act as adapters that allow BP to run over different physical links (e.g., TCP for ground stations, custom radio protocols for space-to-space).
3.  **Endpoint Identifiers (EIDs)**: Using URI schemes (`ipn` or `dtn`), these identifiers route bundles based on logical destinations rather than fixed IP addresses, allowing routes to change while a bundle is "in flight."

---

## Analysis of Critical Failure Points

Based on RFC 9171 and the operational constraints of deep-space communication, the most critical failure point is **Storage Exhaustion vs. Bundle Lifetime Management**.

### The "Bundle Congestion Collapse" Risk
In a traditional network, congestion leads to dropped packets $\rightarrow$ TCP window shrinkage $\rightarrow$ reduced load. In DTN, the goal is *not* to drop packets. However, this creates a paradoxical vulnerability:

*   **The Buffer Bloat Problem**: If a node's outbound link is down longer than anticipated, the storage buffer fills with high-priority bundles. When new arrivals exceed available capacity, the node must decide which bundle to discard.
*   **Livelock via Custody Transfer**: While "Custody Transfer" (where a node accepts responsibility for reliable delivery) prevents data loss at the source, it can lead to a state where several nodes are merely shuffling the same large set of "custodied" bundles back and forth without any of them having an open path to the final destination.
*   **Time-to-Live (TTL) Sensitivity**: Bundles have explicit lifetimes. In interplanetary scenarios, if the estimated delay exceeds the assigned TTL, a bundle may be perfectly routed but expire seconds before reaching its target—rendering all previous energy and storage expenditure wasted.

### Conclusion on Failure Point
The inherent tension in DTN is between **Reliability (Store-and-Forward)** and **Capacity (Finite Storage)**. The critical failure point is not the link itself (which is assumed to be broken), but the **Local Memory Management Policy**. A poorly configured prioritization or expiration policy can turn a relay node into a "data black hole," effectively killing a communication stream while appearing nominally functional.

---

## Summary Table: TCP/IP vs. BPv7

| Feature | TCP/IP (Standard) | Bundle Protocol v7 (DTN) |
| :--- | :--- | :--- |
| **Connectivity** | Requires end-to-end path | Hop-by-hop connectivity |
| **Latency Handling** | Timers $\rightarrow$ Retransmission | Store $\rightarrow$ Forward when possible |
| **State** | Connection-oriented (sessions) | Message-oriented (bundles) |
| **Primary Constraint** | Bandwidth / Congestion | Storage / Energy / Time-of-Flight |
| **Addressing** | Topological (IP) | Logical Endpoint IDs (URIs) |
