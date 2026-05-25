#!/usr/bin/env python3
"""
Hybrid Backtest Runner — Compare Classical vs QAE-modulated strategies
on identical historical data.

External-subject artifact: empirically measures whether quantum volatility
regime detection improves trading performance over classical baseline.

Usage:
    python hybrid_backtest_with_qae.py --symbol AAPL --start 2024-01-01 --end 2026-05-24
    python hybrid_backtest_with_qae.py --symbol SPY --compare-all
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"ERROR: Required libraries not installed")
    print("Install via: pip install yfinance pandas numpy")
    sys.exit(1)

# Import backtest engine and its QAE availability flag
sys.path.insert(0, str(Path(__file__).parent.parent))
from bin.backtest_engine import BacktestEngine, QAE_AVAILABLE


def run_comparison(symbol: str, start_date: str, end_date: str, compare_all: bool = False):
    """Run side-by-side comparison of classical and QAE-modulated strategies."""
    
    results = {}
    
    # Mode 1: Classical (no QAE)
    print("\n" + "="*70)
    print("MODE 1: CLASSICAL STRATEGY (RSI + MA crossover only)")
    print("="*70)
    
    engine_classical = BacktestEngine(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        use_qae_regimes=False
    )
    metrics_classical = engine_classical.execute_backtest()
    results["classical"] = metrics_classical
    
    print(f"\n[CLASSICAL] Final Sharpe: {metrics_classical['sharpe_ratio']:.3f}")
    print(f"[CLASSICAL] Win Rate: {metrics_classical['win_rate_pct']:.1f}%")
    print(f"[CLASSICAL] Total Trades: {metrics_classical['total_trades']}")
    
    # Mode 2: QAE-modulated
    if QAE_AVAILABLE:
        print("\n" + "="*70)
        print("MODE 2: QAE-MODULATED STRATEGY (regime-aware signal gating)")
        print("="*70)
        
        engine_qae = BacktestEngine(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            use_qae_regimes=True
        )
        metrics_qae = engine_qae.execute_backtest()
        results["qae"] = metrics_qae
        
        print(f"\n[QAE] Final Sharpe: {metrics_qae['sharpe_ratio']:.3f}")
        print(f"[QAE] Win Rate: {metrics_qae['win_rate_pct']:.1f}%")
        print(f"[QAE] Total Trades: {metrics_qae['total_trades']}")
        
        # Compute delta
        sharpe_delta = metrics_qae['sharpe_ratio'] - metrics_classical['sharpe_ratio']
        winrate_delta = metrics_qae['win_rate_pct'] - metrics_classical['win_rate_pct']
        trades_delta = metrics_qae['total_trades'] - metrics_classical['total_trades']
        
        classical_sharpe = metrics_classical['sharpe_ratio']
        pct_change = (sharpe_delta / classical_sharpe * 100) if classical_sharpe != 0 else float('nan')
        
        print("\n" + "="*70)
        print("DELTA: QAE vs Classical")
        print("="*70)
        print(f"Sharpe ratio:    {sharpe_delta:+.3f} ({'+' if sharpe_delta >= 0 else ''}{pct_change:.1f}%)")
        print(f"Win rate:        {winrate_delta:+.1f}%")
        print(f"Total trades:    {trades_delta:+d}")
        
        results["delta"] = {
            "sharpe_delta": round(sharpe_delta, 3),
            "winrate_delta": round(winrate_delta, 1),
            "trades_delta": int(trades_delta),
            "qae_outperforms": sharpe_delta > 0,
            "pct_improvement": round(pct_change, 1) if not np.isnan(pct_change) else None
        }
    
    elif compare_all:
        print("\n[WARNING] QAEVolatilityEstimator not available — running classical-only mode")
        results["note"] = "QAE unavailable; classical results only"
    
    return results


def save_comparison_report(results: dict, output_path: str):
    """Save comparison results to JSONL and markdown report."""
    
    # Helper to convert numpy types to native Python types for JSON
    def json_serial(obj):
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    
    # Save to backtests.jsonl
    log_path = Path("reports/backtests.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comparison_type": "classical_vs_qae",
    }
    # Deep copy and convert numpy types
    import copy
    results_copy = copy.deepcopy(results)
    for key in results_copy:
        if isinstance(results_copy[key], dict):
            for subkey in results_copy[key]:
                val = results_copy[key][subkey]
                if isinstance(val, (np.bool_, np.integer, np.floating)):
                    results_copy[key][subkey] = json_serial(val)
    
    record.update(results_copy)
    
    with open(log_path, "a") as f:
        f.write(json.dumps(record, default=json_serial) + "\n")
    
    print(f"\n[INFO] Results saved to {log_path}")
    
    # Generate markdown summary for C462 report reference
    md_lines = [
        "# Hybrid Backtest Comparison Report\n",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n",
        ""
    ]
    
    if "delta" in results:
        delta = results["delta"]
        verdict = "✅ QAE improves performance" if delta["qae_outperforms"] else "⏳ Classical baseline holds"
        
        md_lines.extend([
            f"**Verdict:** {verdict}\n",
            "",
            "| Metric | Classical | QAE-Modulated | Delta |",
            "|--------|-----------|---------------|-------|"
        ])
        
        classical = results.get("classical", {})
        qae = results.get("qae", {})
        
        md_lines.append(f"| Sharpe Ratio | {classical.get('sharpe_ratio', 'N/A'):.3f} | {qae.get('sharpe_ratio', 'N/A'):>7.3f} | {delta['sharpe_delta']:+.3f} |")
        md_lines.append(f"| Win Rate | {classical.get('win_rate_pct', 'N/A'):.1f}% | {qae.get('win_rate_pct', 'N/A'):>8.1f}% | {delta['winrate_delta']:+.1f}% |")
        md_lines.append(f"| Total Trades | {classical.get('total_trades', 'N/A')} | {qae.get('total_trades', 'N/A'):>9d} | {delta['trades_delta']:>+d} |")
    
    return "\n".join(md_lines)


def main():
    parser = argparse.ArgumentParser(description="Compare Classical vs QAE-modulated backtesting strategies")
    parser.add_argument("--symbol", "-s", default="AAPL", help="Stock symbol (default: AAPL)")
    parser.add_argument("--start", default="2024-01-01", help="Start date (YYYY-MM-DD, default: 2024-01-01)")
    parser.add_argument("--end", default=None, help="End date (YYYY-MM-DD, defaults to today)")
    parser.add_argument("--compare-all", action="store_true", help="Run full comparison if QAE available, else classical-only")
    
    args = parser.parse_args()
    
    end_date = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    print("\n" + "="*70)
    print("HYBRID BACKTEST RUNNER — CLASSICAL VS QAE COMPARISON")
    print("="*70)
    print(f"Symbol: {args.symbol}")
    print(f"Date range: {args.start} → {end_date}")
    print("="*70)
    
    results = run_comparison(
        symbol=args.symbol,
        start_date=args.start,
        end_date=end_date,
        compare_all=args.compare_all
    )
    
    # Save markdown summary
    md_report = save_comparison_report(results, "reports/C462_quantum_vs_classical_benchmark.md")
    
    report_path = Path("reports/C462_quantum_vs_classical_benchmark.md")
    with open(report_path, "w") as f:
        f.write(md_report)
    
    print(f"\n[INFO] Markdown summary saved to {report_path}")
    
    # Final verdict line
    if "delta" in results and "qae_outperforms" in results["delta"]:
        if results["delta"]["qae_outperforms"]:
            print(f"\n✅ RESULT: QAE-modulated strategy outperforms classical by Sharpe {results['delta']['sharpe_delta']:+.3f}")
        else:
            print(f"\n⏳ RESULT: Classical baseline holds (Sharpe delta: {results['delta']['sharpe_delta']:+.3f})")


if __name__ == "__main__":
    main()
