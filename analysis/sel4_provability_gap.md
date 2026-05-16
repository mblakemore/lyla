# The Provability Gap in Formally Verified Kernels: A Case Study of seL4

## 1. Thesis
A machine-checked proof of functional correctness (like that provided by seL4) eliminates *implementation* errors relative to a specification but does not eliminate *systemic* fragility. The "Provability Gap" is the delta between the formal model's axioms and the physical reality of execution.

## 2. Mapping the Gaps

### Vector A: The Semantic Gap (Model vs. Hardware)
seL4's proofs typically assume an abstract machine model where instructions execute as specified. However, modern hardware optimizes for average case via speculation.
- **Violation:** Spectre/Meltdown. The kernel might be proven to isolate Process A from Process B, but side-channel leakage occurs at the micro-architectural level (caches/branch predictors), which are usually absent from the formal model.
- **Implication:** Verification provides "Logical Isolation," not "Physical Isolation."

### Vector B: The Compositional Gap (Mechanism vs. Policy)
The seL4 kernel proves its mechanisms (Capabilities) work correctly. It does NOT prove that the user's distribution of those capabilities constitutes a secure system policy.
- **Violation:** If a developer accidentally grants a 'Master Capability' to an untrusted component, the kernel will perform the transfer perfectly (as verified), but the overall security state collapses.
- **Implication:** Verified building blocks do not guarantee a verified house. Correctness moves from the kernel $\rightarrow$ the configuration manager.

### Vector C: The Environmental Gap (Static Proof vs. Dynamic Entropy)
Proofs generally assume deterministic memory and stable clock signals.
- **Violation:** Rowhammer or cosmic-ray bit flips. Formal verification typically assumesmemory is immutable unless written by software. When physical entropy modifies state without a CPU instruction, the proof's axioms are violated.
- **Implication:** Fault tolerance remains a distinct concern from correctness.

## 3. Synthesis for Lyla's Pattern Library
Updating `P_VRES_001`: Provability is not a binary switch ("Proven" vs "Unproven") but a spectrum of assumptions. The strength of a proof is exactly equal to the validity of its lowest-level assumption about the hardware.

**Conclusion:** To move from `Correctness` to `Resilience`, one must stop treating the proof as the finish line and start treating it as the baseline that allows focus on these non-modelable gaps.
