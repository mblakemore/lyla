#!/usr/bin/env bash
# IBM Quantum Test Harness — Lyla Integration Scaffold
# 
# Usage: ./test_harness.sh [--real]
#   --real   Submit to real hardware (requires IBM_QUANTUM_API_KEY env var)
#   default  Run simulator test only
#
# Credentials stored in ~/.qiskit/qiskit-ibm.json or via environment variable

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="${SCRIPT_DIR}/ibm_quantum_submit.py"

echo "=== IBM Quantum Test Harness ==="
echo ""

# Check if running with real hardware flag
REAL_MODE=false
if [[ "${1:-}" == "--real" ]]; then
    REAL_MODE=true
    
    # Check API key
    if [[ -z "${IBM_QUANTUM_API_KEY:-}" ]]; then
        echo "ERROR: IBM_QUANTUM_API_KEY not set for real hardware submission"
        echo "Get your token at: https://quantum.ibm.com/account"
        exit 1
    fi
fi

# Run Bell state test circuit
echo "Running Bell state circuit..."
python3 "$CLI" --bell --xx-measure || {
    echo "Simulator test failed"
    exit 1
}

echo ""

if $REAL_MODE; then
    echo "Submitting to real hardware..."
    python3 "$CLI" --bell --instance ibm_marrakesh || {
        echo "Real hardware submission failed"
        exit 1
    }
else
    echo "Skipping real hardware (use --real flag, requires IBM_QUANTUM_API_KEY)"
fi

echo ""
echo "Test complete."
