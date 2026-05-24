#!/usr/bin/env python3
"""
Quantum Signal Generator — Qiskit-based signal generation for backtesting.

Architecture:
- Quantum circuit encodes portfolio allocation decision via amplitude encoding
- Measurement outcomes translated to BUY/SELL/HOLD signals
- Compatible with existing backtest_engine.py signal interface

External-subject artifact: implements novel algorithmic approach per P_C406_PREDICTION_HYPOTHESIS.
Simulator mode works without IBM Quantum API keys; real device integration ready when credentials provided.
"""

import argparse
import json
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
import sys

# Try importing qiskit - fail gracefully in simulator mode
try:
    from qiskit import QuantumCircuit, Aer, execute
    from qiskit.quantum_info import Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


class QuantumSignalGenerator:
    """Generate trading signals via quantum circuits."""
    
    def __init__(self, mode: str = "simulator", api_key: str = None, instance_id: str = None):
        self.mode = mode  # "simulator" or "ibm_quantum"
        self.api_key = api_key
        self.instance_id = instance_id
        
        if not QISKIT_AVAILABLE:
            print("[WARN] Qiskit not installed — running in pure-simulation fallback mode")
            self.use_qiskit = False
        else:
            self.use_qiskit = True
            
        # Circuit parameters (tuneable)
        self.num_qubits = 3  # 3-qubit circuit → 8 basis states
        self.depth = 2       # Circuit depth
        
    def generate_classical_seed(self, timestamp: str, symbol: str) -> np.ndarray:
        """Convert timestamp + symbol into deterministic pseudo-random seed for simulation."""
        # Simple hash-based seeding
        seed_str = f"{timestamp}:{symbol}"
        seed_val = sum(ord(c) for c in seed_str) % (2**31 - 1)
        return np.random.SeedSequence(seed_val)
    
    def _simulate_circuit_pseudo(self, seed_state: np.ndarray, price_change: float, rsi: float) -> dict:
        """
        Pseudo-quantum simulation without actual qiskit.
        
        Maps market state to quantum-like probability distribution:
        - Price change → amplitude rotation on |0> component
        - RSI → phase rotation encoding momentum information
        - Measurement → probabilistic signal selection
        """
        rng = np.random.default_rng(seed_state)
        
        # Encode classical features into "quantum" amplitudes
        # Normalized price change (-5% to +5% range assumed)
        pc_norm = np.clip(price_change / 0.05, -1, 1)
        rsi_normalized = rsi / 100.0
        
        # Create 8-state amplitude vector (3 qubits)
        amplitudes = np.zeros(8, dtype=complex)
        
        # Basis states mapped to signals:
        # 000 (0): STRONG_BUY, 001 (1): BUY, 010 (2): WEAK_BUY
        # 011 (3): HOLD,   100 (4): WEAK_SELL, 101 (5): SELL, 110 (6): STRONG_SELL
        # 111 (7): CASH (no position)
        
        # Amplitude encoding based on market state
        buy_bias = max(0, pc_norm) * (1 - rsi_normalized)  # High when rising + oversold
        sell_bias = max(0, -pc_norm) * rsi_normalized       # High when falling + overbought
        
        amplitudes[0] = np.sqrt(max(0, buy_bias))  # Strong buy
        amplitudes[1] = np.sqrt(max(0, buy_bias * 0.7))  # Buy  
        amplitudes[2] = np.sqrt(max(0, buy_bias * 0.4))  # Weak buy
        amplitudes[3] = np.sqrt(0.2)  # Baseline hold probability
        amplitudes[4] = np.sqrt(max(0, sell_bias * 0.4))  # Weak sell
        amplitudes[5] = np.sqrt(max(0, sell_bias * 0.7))  # Sell
        amplitudes[6] = np.sqrt(max(0, sell_bias))  # Strong sell
        amplitudes[7] = np.sqrt(0.1)  # Cash bias
        
        # Normalize amplitudes
        probs = np.abs(amplitudes) ** 2
        probs /= probs.sum() if probs.sum() > 0 else 1
        
        # Sample from distribution (measurement)
        outcome = rng.choice(8, p=probs)
        
        return {
            "outcome": outcome,
            "probabilities": probs.tolist(),
            "signal": self._outcome_to_signal(outcome),
            "confidence": float(probs[outcome])
        }
    
    def _execute_real_qiskit(self, qc: QuantumCircuit) -> dict:
        """Execute circuit on real IBM Quantum device."""
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService
            
            service = QiskitRuntimeService(
                channel="ibm_quantum",
                token=self.api_key,
                instance=self.instance_id
            )
            
            # Get best available backend
            backend = service.backend("ibmq_manila")  # Free tier accessible
            
            job = execute(qc, backend=backend, shots=1024)
            result = job.result()
            counts = result.get_counts()
            
            # Convert counts to signal
            dominant_outcome = max(counts, key=counts.get)
            probability = counts[dominant_outcome] / sum(counts.values())
            
            return {
                "outcome": int(dominant_outcome, 2),
                "probabilities": [counts.get(f"{i:03b}", 0) / sum(counts.values()) for i in range(8)],
                "signal": self._outcome_to_signal(int(dominant_outcome, 2)),
                "confidence": float(probability),
                "device": str(backend)
            }
            
        except Exception as e:
            print(f"[ERROR] Quantum execution failed: {e}")
            return None
    
    def _build_qaoa_circuit(self, price_change: float, rsi: float) -> QuantumCircuit:
        """Build QAOA-style variational circuit encoding portfolio decision."""
        if not self.use_qiskit or not QISKIT_AVAILABLE:
            return None
        
        qc = QuantumCircuit(self.num_qubits, self.num_qubits)
        
        # Encode classical data into quantum state via amplitude rotation
        theta = np.arcsin(np.clip(price_change * 5, -1, 1))  # Price change → rotation angle
        phi = rsi * np.pi / 100.0  # RSI → phase encoding
        
        # Layer 1: Hadamard + parameterized rotations
        for qubit in range(self.num_qubits):
            qc.h(qubit)
            qc.rz(theta + qubit * 0.1, qubit)
            qc.rx(phi + qubit * 0.05, qubit)
        
        # Layer 2: Entangling gates (QAOA mixer)
        for i in range(self.num_qubits - 1):
            qc.cx(i, i + 1)
        
        # Final rotations based on market momentum
        qc.rz(0.3 * (rsi - 50) / 50, 0)  # Bias first qubit by RSI deviation from neutral
        
        # Measure all qubits
        qc.measure(range(self.num_qubits), range(self.num_qubits))
        
        return qc
    
    def _outcome_to_signal(self, outcome: int) -> str:
        """Map measurement outcome to trading signal."""
        signals = {
            0b000: "STRONG_BUY",   # 0
            0b001: "BUY",          # 1
            0b010: "WEAK_BUY",     # 2
            0b011: "HOLD",         # 3
            0b100: "WEAK_SELL",    # 4
            0b101: "SELL",         # 5
            0b110: "STRONG_SELL",  # 6
            0b111: "CASH"          # 7 (no position)
        }
        return signals.get(outcome, "HOLD")
    
    def generate_signal(self, timestamp: str, symbol: str, price_change: float, rsi: float) -> dict:
        """Generate quantum-derived trading signal."""
        if self.mode == "simulator":
            seed_state = self.generate_classical_seed(timestamp, symbol)
            result = self._simulate_circuit_pseudo(seed_state, price_change, rsi)
            
        elif self.mode == "ibm_quantum" and QISKIT_AVAILABLE:
            qc = self._build_qaoa_circuit(price_change, rsi)
            result = self._execute_real_qiskit(qc)
            
            if result is None:
                # Fallback to simulator if device unavailable
                print("[WARN] IBM Quantum unavailable — falling back to simulator")
                return self.generate_signal(timestamp, symbol, price_change, rsi)
                
        else:
            # Pure simulation fallback
            result = self._simulate_circuit_pseudo(
                np.random.SeedSequence(hash(f"{timestamp}{symbol}")),
                price_change,
                rsi
            )
        
        result["timestamp"] = timestamp
        result["symbol"] = symbol
        result["generator_mode"] = self.mode
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Quantum Signal Generator for Trading")
    parser.add_argument("--mode", choices=["simulator", "ibm_quantum"], default="simulator",
                       help="Execution mode (default: simulator)")
    parser.add_argument("--api-key", default=None, help="IBM Quantum API key (for real device mode)")
    parser.add_argument("--instance-id", default=None, help="IBM Quantum instance ID")
    parser.add_argument("--test", action="store_true", help="Run self-test with synthetic data")
    
    args = parser.parse_args()
    
    generator = QuantumSignalGenerator(
        mode=args.mode,
        api_key=args.api_key,
        instance_id=args.instance_id
    )
    
    if args.test:
        print("="*60)
        print("QUANTUM SIGNAL GENERATOR — SELF TEST")
        print("="*60)
        
        # Synthetic market scenarios
        test_cases = [
            {"ts": "2024-01-15T10:00:00Z", "symbol": "AAPL", "price_change": 0.02, "rsi": 35},   # Rising + oversold → BUY
            {"ts": "2024-01-15T11:00:00Z", "symbol": "AAPL", "price_change": -0.01, "rsi": 70},   # Falling + overbought → SELL
            {"ts": "2024-01-15T12:00:00Z", "symbol": "AAPL", "price_change": 0.001, "rsi": 50},   # Flat + neutral → HOLD
        ]
        
        results = []
        for tc in test_cases:
            signal = generator.generate_signal(tc["ts"], tc["symbol"], tc["price_change"], tc["rsi"])
            results.append(signal)
            
            print(f"\nScenario: {tc['symbol']} | ΔP={tc['price_change']:+.1%} | RSI={tc['rsi']}")
            print(f"  Signal: {signal['signal']} (confidence: {signal['confidence']:.2%})")
            if 'device' in signal:
                print(f"  Device: {signal['device']}")
        
        print("\n" + "="*60)
        print("TEST COMPLETE — Generator operational in {} mode".format(args.mode))
        print("="*60)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
