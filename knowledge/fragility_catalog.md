# The Fragility Catalog: Systemic Failure Signatures

This catalog transforms retrospective failure patterns into a proactive identification framework. Each entry maps an abstract **Systemic Pattern** to observable **Symptoms**, providing an operational "fingerprint" for resilience engineers and architects.

## I. Hyper-coupling Cascade (The Domino Effect)
*When components are so tightly integrated that the latency or error of one becomes the state of all.*

| Dimension | Specification |
|---|---|
| **Pattern** | Synchronous dependency chain without timeout thresholds or circuit breakers. |
| **Symptom** | "Sudden death" across multiple services; CPU spikes on callers while callees are idling/slow. |
| **Sentinel Metric** | $p99$ response time convergence between dependent services. If Service A's $p99 \approx$ Service B's $p99$, they are coupled. |
| **Proactive Probe** | **Chaos Injection**: Artificially inject 500ms delay in a dependency; if the caller's throughput drops linearly with this delay, the system is hyper-coupled. |
| **Mitigation** | Implement *Strategic Slack*: asynchronous queues, adaptive concurrency limits, or the Circuit Breaker pattern. |

---

## II. Reconciliation Oscillation (The Feedback Loop)
*When the act of recovery creates more instability than the failure itself.*

| Dimension | Specification |
|---|---|
| **Pattern** | Automated correction agents reacting to delayed telemetry signals (Control Plane Lag). |
| **Symptom** | "Flip-flopping" metrics; resources cycling rapidly between `Healthy` and `Unhealthy`. |
| **Sentinel Metric** | Delta of State Change frequency per unit of time ($\Delta SC/\Delta t$). Spikes during outages indicate oscillation. |
| **Proactive Probe** | **Stutter Test**: Force a state change then immediately trigger the auto-recovery mechanism before the first state change propagates across all nodes. |
| **Mitigation** | Exponential backoff on reconciliation loops and mandatory "Hysteresis" (minimum wait times before changing state again). |

---

## III. Circular Dependency / Fate Sharing (The Blind Spot)
*When the tools required for recovery rely on the systems being recovered.*

| Dimension | Specification |
|---|---|
| **Pattern** | Management plane resides within the data plane it manages. |
| **Symptom** | The "Locked Door" paradox: You have the fix, but you cannot deploy it because the network is down. |
| **Sentinel Metric** | Binary check: Does `Service_Recovery` $\rightarrow$ `Network_Path` $\rightarrow$ `Service_Target`? If yes, fate is shared. |
| **Proactive Probe** | **Isolation Drill**: Block access to primary internal API gateway; verify if administrators can still reach hardware/nodes via an Out-of-Band (OOB) path. |
| **Mitigation** | *Physical Separation*: Deploy separate control planes or "Emergency Access Nodes" that bypass common failure domains. |

---

## IV. The Thundering Herd (The Recovery Spike)
*When a successful restoration triggers an immediate secondary collapse due to accumulated demand.*

| Dimension | Specification |
|---|---|
| **Pattern** | Large numbers of clients attempting synchronized retries after a dependency comes back online. |
| **Symptom** | A "Double Dip": system recovers for 30 seconds, then crashes again with $10x$ more traffic than normal baseline. |
| **Sentinel Metric** | Ratio of Requests per Second ($\text{RPS}$) immediately post-recovery vs. historical average. |
| **Proactive Probe** | **Burst Simulation**: Simulate a service outage for all clients, then release them simultaneously without jitter. Measure the peak load on the recovery target. |
| **Mitigation** | Client-side Jitter (Randomized delay), adaptive rate limiting at the edge, and gradual ramp-up (Warm-ups). |

---

## V. Configuration Entropy (The Ghost in the Machine)
*When the running state diverges from the source of truth through undocumented 'hotfixes'.*

| Dimension | Specification |
|---|---|
| **Pattern** | Manual changes made to production environment that bypass CI/CD or version control. |
| **Symptom** | The "It worked in Staging" paradox; failures occurring on nodes that haven't been updated recently. |
| **Sentinel Metric** | Drift count: $\sum (\text{Actual Config} \neq \text{Desired State})$. |
| **Proactive Probe** | **Consistency Audit**: Compare hash of runtime configuration files against hashes in Git across 10% of the fleet randomly. |
| **Mitigation** | *Immutability*: Disable SSH write access to production; enforce "Recycleed Infrastructure" where any change requires a pod replacement. |

---

## VI. Invisible Dependency Chain (The Hidden Pivot)
*When components A and B are functionally decoupled but share a hidden physical resource.*

| Dimension | Specification |
|---|---|
| **Pattern** | Two disparate systems sharing a single database, disk, or network switch not explicitly listed in architecture diagrams. |
| **Symptom** | Correlation without Causality: Service A crashes exactly when unrelated Service B peaks in load. |
| **Sentinel Metric** | Resource Contention spikes in shared substrates (IOPS, Packet loss) appearing before application-level errors. |
| **Proactive Probe** | **Stress testing Shared Substrates**: Saturate the underlying storage array; observe which seemingly unrelated services degrade first. |
| **Mitigation** | Explicit dependency mapping using L7 discovery tools and resource quotas/hard limits per tenant. |

---

## Summary Mapping for Operators

| If you see... | It is likely... | Check this First... | Action |
| :--- | :--- | :--- | :--- |
| **Total Blackout / No Access** | Circular Dependency | OOB Management Path | Switch to Out-of-Band |
| **Recovery $\rightarrow$ Crash $\rightarrow$ Recovery** | Thundering Herd | Client Retry Logic | Apply Jitter / Rate Limit |
| **Metric Oscillations** | Reconciliation Loop | Telemetry Delay $\text{vs}$ Polling Int | Slow down the loop |
| **Latency Propagation** | Hyper-coupling | Timeouts / Circuit Breakers | Sever the link (Trip breaker) |
| **Random Node Behavior** | Config Entropy | Git vs Runtime Hash | Redeploy from Source |
