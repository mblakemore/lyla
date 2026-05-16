# Fragility Mapping: Interplanetary DTN Architecture

This report applies the **Systemic Fragility Catalog** to the **Bundle Protocol v7 (BPv7)** used in Disruption Tolerant Networking. The goal is to determine if the failure patterns found in terrestrial hyper-scale systems are present—or exacerbated—in deep space communication architectures.

## 1. Introduction: Domain Translation
Terrestrial networking focuses on *latency* and *throughput*. Deep Space networking deals with *disruptions* and *storage durations*. In a system where RTT can be hours, "real-time" correction loops are physically impossible; however, this very fact changes how fragility manifests.

---

## 2. Hazard Mapping Analysis

### II. Reconciliation Oscillation $\rightarrow$ "The Cosmic Echo"
*   **Catalog Pattern**: Automated recovery reacting to delayed telemetry signals.
*   **DTN manifestation**: Extremely high risk. If an operator or an automated agent attempts to update routing tables based on reports from a probe at Mars, they are seeing state that is minutes old.
*   **Failure Mode**: An "Adjustment Spiral." If the control plane issues a re-routing command based on reported congestion, by the time the command reaches the node, the congestion has cleared, but the new route might now cause congestion elsewhere. The network begins to oscillate not because of technical instability, but because the **feedback loop exceeds the coherence time of the environment.**
*   **Symptom in DTN**: Bundle delivery rates fluctuating in sync with the signal propagation delay (the Light-Speed Harmonic).

### III. Circular Dependency / Fate Sharing $\rightarrow$ "The Custody Trap"
*   **Catalog Pattern**: Tools required for recovery rely on systems being recovered.
*   **DTN manifestation**: Manifests as "Custodial Deadlock." In BPv7, custody transfer allows a node to take ownership of a bundle. If Node A takes custody and then enters a failure mode where it cannot send *or* receive new bundles, any attempt to remotely manage that node's storage requires using the very transport layer that is currently failing/clogged.
*   **Failure Mode**: The "Locked Relay." You may have an administrative way to tell a relay to drop certain low-priority packets to clear space, but if those commands are queued behind the high-priority bundles they intend to manage, you have reached a circular dependency.
*   **Symptom in DTN**: Administrative timeouts; nodes appearing "Alive" via heartbeats but refusing all data input.

### IV. The Thundering Herd $\rightarrow$ "Convergence Burst"
*   **Catalog Pattern**: Successful restoration triggers secondary collapse due to accumulated demand.
*   **DTN manifestation**: Extreme severity. Due to Store-and-Forward, buffers accumulate massive amounts of data during disruptions (days or weeks). 
*   **Failure Mode**: When a physical link returns (e.g., orbital alignment), every node attempts to flush its entire non-volatile buffer simultaneously. This creates a "Tsunami Effect." Even with prioritization, the sheer volume of metadata required to negotiate thousands of simultaneous bundle transfers can overwhelm the Convergence Layer (CL) CPU before the first packet even moves.
*   **Symptom in DTN**: Initial burst of successful transmissions followed by total crash of the radio subsystem as it enters an error state from overflow/heat.

---

## 3. Novel Fragility Identified: The "TTL Horizon Drift"
While mapping existing patterns, a new unique hazard emerges that doesn't fit perfectly into the terrestrial catalog: **Semantic Expiry.**

*   **Description**: In traditional networks, we focus on *if* the message arrives. In DTN, because of extreme latency and storage duration, we must care about *when*. 
*   **Hazard**: If a system is configured with TTLs based on average distance, but routing delays increase slightly, you enter a state where bundles are successfully moving through the network $\rightarrow$ consuming energy and storage across multiple hops $\rightarrow$ only to expire just before delivery.
*   **Systemic Risk**: The network appears healthy (all links operational, all buffers moving data), but the actual value delivered is Zero. This is **The Illusion of Progress**.

---

## 4. Summary Recommendation Table for BPv7 Architects

| Hazard | Terrestrial Equivalent | Cosmic Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Control Plane Lag** | Recon Oscillation | Critical | Transition from reactive control to predictive scheduling (Time-based Routing). |
| **Storage Tsunami** | Thundering Herd | High | Aggressive pre-flight pruning; staggered release schedules based on priority weights. |
| **Custodial Deadlock** | Fate Sharing | Medium | Implement an "Out-of-Band" Emergency Signal channel that bypasses the Bundle Protocol queue entirely. |
| **TTL Drift** | N/A | Extreme | Adaptive TTL extension: Allow nodes to extend bundle life if they can verify target accessibility via ground-truth beacons. |
