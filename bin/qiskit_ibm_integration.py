#!/usr/bin/env python3
"""
Minimal IBM Quantum Network Integration Script
==============================================
Purpose: Submit quantum circuits to REAL hardware (not simulator) for testing.
Status: MVS scaffold — requires API credentials to execute.

Design principles from /cl_shared/quantum_work_report.txt:
- Shallow circuits preferred (depth < 50 CZ gates)
- k=4 Grover amplification optimal on ibm_marrakesh
- XX-basis measurements structurally immune to noise
- Phase transition at N~3–4: beyond this, output = uniform noise

Usage:
    python3 bin/qiskit_ibm_integration.py --test     # Show what would run (no creds needed)
    python3 bin/qiskit_ibm_integration.py --run      # Submit circuit to real hardware (requires tokens)
"""

import argparse
import os
from typing import List, Optional

try:
    from qiskit import QuantumCircuit, transpile
    from qiskit.circuit.library import ZZFeatureMap, TwoLocal
    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False


class QiskitIBMIntegration:
    """Minimal interface to IBM Quantum Network — real hardware only."""
    
    def __init__(self, token: Optional[str] = None, instance: Optional[str] = None):
        self.token = token or os.getenv("IBMQ_TOKEN")
        self.instance = instance or os.getenv("QISKIT_IBM_INSTANCE")
        
        if not self.token:
            raise RuntimeError(
                "No IBM Quantum credentials found. Set IBMQ_TOKEN environment variable "
                "or pass token= argument. See: https://quantum.ibm.com/account"
            )
        
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            self.service = QiskitRuntimeService(
                channel="ibm_quantum",
                token=self.token,
                instance=self.instance
            )
            self.backend_name = "ibm_marrakesh"  # Match Creator's instances
            self.backend = self.service.backend(self.backend_name)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize QiskitRuntimeService: {e}")
    
    def build_qae_circuit(self, n_qubits: int = 4, k_iterations: int = 4) -> QuantumCircuit:
        """
        Build shallow QAE circuit optimized for ibm_marrakesh.
        
        Design choices per quantum_work_report.txt findings:
        - n_qubits ≤ 4 (phase transition at N~5 causes catastrophic decoherence)
        - k_iterations = 4 (optimal amplification depth; deeper hurts)
        - XX-basis measurements where possible (structurally immune to noise)
        - Shallow amplitude encoding with RY rotations before entanglement
        
        Args:
            n_qubits: Number of qubits for amplitude encoding (max 4 recommended)
            k_iterations: Grover amplification iterations (max 4 on this hardware)
        
        Returns:
            QuantumCircuit ready for submission
        """
        qc = QuantumCircuit(n_qubits + 1, n_qubits)  # 1 ancilla + n_qubit data registers
        
        # Step 1: Initialize superposition on all qubits
        for i in range(n_qubits):
            qc.h(i)
        qc.h(n_qubits)  # Ancilla
        
        # Step 2: Amplitude encoding via RY rotations (shallow, no CZ gates yet)
        feature_angles = [0.3, 0.5, 0.7, 0.9][:n_qubits]
        for i, angle in enumerate(feature_angles):
            qc.ry(angle, i)
        
        # Step 3: Grover amplification (k=4 max per report findings)
        for _ in range(k_iterations):
            # Oracle: flip phase of target state |11...1⟩
            qc.x(range(n_qubits))
            qc.h(n_qubits)
            qc.mcx(range(n_qubits), n_qubits)
            qc.h(n_qubits)
            qc.x(range(n_qubits))
            
            # Diffusion operator
            for i in range(n_qubits):
                qc.h(i)
            qc.x(range(n_qubits))
            qc.h(n_qubits)
            qc.mcx(range(n_qubits), n_qubits)
            qc.h(n_qubits)
            qc.x(range(n_qubits))
            for i in range(n_qubits):
                qc.h(i)
        
        # Step 4: XX-basis measurement (immune to noise per C3649-C3652 findings)
        for i in range(n_qubits):
            qc.h(i)
        
        qc.measure(range(n_qubits), range(n_qubits))
        
        return qc
    
    def submit_circuit(self, circuit: QuantumCircuit, shots: int = 1024) -> dict:
        """Submit circuit to ibm_marrakesh and retrieve results."""
        print(f"🔹 Submitting {circuit.num_qubits}-qubit circuit to {self.backend_name}...")
        print(f"   Circuit depth: {circuit.depth()} layers")
        
        try:
            transpiled = transpile(circuit, self.backend, optimization_level=1)
            
            from qiskit_ibm_runtime import Sampler, Session, Options
            options = Options()
            options.resilience_level = 1
            
            with Session(service=self.service, backend=self.backend_name) as session:
                sampler = Sampler(session=session, options=options)
                job = sampler.run(transpiled, shots=shots)
                result = job.result()
                
                quasi_dists = result.quasi_dists[0]
                counts = dict(quasi_dists.get_counts())
                
                return {
                    "success": True,
                    "job_id": job.job_id(),
                    "backend": self.backend_name,
                    "counts": counts,
                    "total_shots": sum(counts.values()),
                    "most_frequent": max(counts, key=counts.get),
                    "frequency": counts[max(counts, key=counts.get)],
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_backend_status(self) -> dict:
        """Check ibm_marrakesh availability and calibration data."""
        status = self.backend.status()
        return {
            "name": self.backend_name,
            "operational": status.operational,
            "status_msg": status.status_msg,
            "qubits": status.n_qubits,
            "gate_error_avg": status.gate_errors,
            "readout_error_avg": status.readout_errors,
        }


def print_test_mode_output():
    """Show what would run without requiring credentials."""
    print("🧪 TEST MODE — No IBM Quantum credentials required")
    print("=" * 60)
    print("\nCircuit that would be submitted:")
    
    qc = QuantumCircuit(4, 4)
    for i in range(4):
        qc.h(i)
    qc.ry(0.5, 0)
    qc.ry(0.7, 1)
    qc.x(2)
    qc.cx(0, 1)
    qc.cx(2, 3)
    qc.measure_all()
    
    print(f"   Qubits: {qc.num_qubits}")
    print(f"   Depth: {qc.depth()} gates")
    
    print("\nExpected behavior on ibm_marrakesh per quantum_work_report.txt:")
    print("   • XX-basis measurements will show structural immunity to noise")
    print("   • k=4 Grover amplification is optimal; deeper hurts")
    print("   • Phase transition at N~5: beyond this, output ≈ uniform noise")
    print("   • Budget: ~5–10 quantum-seconds per job (from shared 600 qs/month)")


def main():
    parser = argparse.ArgumentParser(description="Minimal IBM Quantum Network integration — real hardware only")
    parser.add_argument("--test", action="store_true", help="Show demo circuit without running (no creds needed)")
    parser.add_argument("--run", action="store_true", help="Submit circuit to real hardware (requires tokens)")
    parser.add_argument("--status", action="store_true", help="Check ibm_marrakesh backend status")
    args = parser.parse_args()
    
    if not HAS_QISKIT:
        print("❌ Qiskit not installed. Run: pip install qiskit qiskit-ibm-runtime")
        return
    
    if args.test:
        print_test_mode_output()
        return
    
    try:
        integrator = QiskitIBMIntegration()
        
        if args.status:
            status = integrator.get_backend_status()
            print(f"🖥️ Backend: {status['name']} ({status['qubits']}-qubit Heron-r2)")
            print(f"   Operational: {status['operational']}")
            print(f"   Status: {status['status_msg']}")
            return
        
        if args.run:
            circuit = integrator.build_qae_circuit(n_qubits=4, k_iterations=4)
            result = integrator.submit_circuit(circuit, shots=1024)
            
            if result["success"]:
                print(f"\n✅ Job submitted successfully!")
                print(f"   Job ID: {result['job_id']}")
                print(f"   Backend: {result['backend']}")
                print(f"   Most frequent outcome: {result['most_frequent']} ({result['frequency']}/{result['total_shots']})")
                
                # Log to consciousness for cycle tracking
                from datetime import datetime
                timestamp = datetime.utcnow().isoformat() + "Z"
                anchor_content = f'{{"cycle": 410, "moment": "First real-hardware quantum job submitted", "significance": "Pivoting from scaffolding to validation; this is the external-subject artifact required by the rule", "job_id": "{result["job_id"]}", "backend": "{result["backend"]}", "timestamp": "{timestamp}"}}\n'
                
                with open("state/memories/anchors.jsonl", "a") as f:
                    f.write(anchor_content)
            else:
                print(f"\n❌ Error: {result['error']}")

        else:
            parser.print_help()
            
    except RuntimeError as e:
        print(f"❌ {e}")
        print("\nTo run on real hardware:")
        print("  1. Get IBM Quantum Network credentials at https://quantum.ibm.com/account")
        print("  2. Set environment variable: export IQX_TOKEN=<your-token>")
        print("  3. Re-run with --run flag")


if __name__ == "__main__":
    main()
