#!/usr/bin/env python3
"""
QAE Threshold Calibrator — Sweep QAE thresholds per asset to find optimal
regime-detection threshold for each symbol.

Tests the C488 finding: QAE is asset-specific. The optimal threshold is
the value of P(high vol) that maximizes Sharpe ratio for each asset.

Usage:
    python3 bin/qae_threshold_calibrator.py --symbols SPY AAPL TSLA QQQ
    python3 bin/qae_threshold_calibrator.py --all  # common set of 10 assets
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import yfinance as yf
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))


def compute_vol_features(df, window=20):
    """Compute normalized rolling volatility for each row."""
    returns = df['Close'].pct_change()
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    normalized = rolling_vol / 0.5  # cap reference: 50% annual vol
    return normalized.clip(0, 1)


def mean_reversion_backtest(df, vol_features, qae_threshold=None):
    """
    Mean-reversion strategy with optional QAE regime filter.
    Buy when RSI < 30 AND price below BB lower.
    Sell when RSI > 70 AND price above BB upper.
    QAE filter: skip trades when vol_features > threshold.
    """
    # Indicators
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df = df.copy()
    df['RSI'] = 100 - (100 / (1 + rs))

    bb_middle = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['bb_lower'] = bb_middle - 2 * bb_std
    df['bb_upper'] = bb_middle + 2 * bb_std

    # Signals
    df['signal'] = 0
    for i in range(1, len(df)):
        row = df.iloc[i]
        if pd.isna(row['RSI']):
            continue

        # Mean-reversion signals
        if row['Close'] <= row['bb_lower'] and row['RSI'] < 30:
            df.at[row.name, 'signal'] = 1
        elif row['Close'] >= row['bb_upper'] and row['RSI'] > 70:
            df.at[row.name, 'signal'] = -1

        # QAE regime filter
        if qae_threshold is not None and vol_features.iloc[i] > qae_threshold:
            df.at[row.name, 'signal'] = 0

    # PnL (next-day return of current signal)
    df['pnl'] = df['signal'].shift(1) * df['Close'].pct_change()
    df = df.dropna()

    if len(df) < 5:
        return None

    daily_returns = df['pnl']
    sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

    cumret = (1 + daily_returns).cumprod()
    peak = cumret.expanding().max()
    drawdown = (cumret - peak) / peak
    max_dd = abs(drawdown.min()) * 100

    total_return = (cumret.iloc[-1] - 1) * 100

    winning = daily_returns[daily_returns > 0]
    losing = daily_returns[daily_returns < 0]
    win_rate = len(winning) / len(daily_returns) * 100 if len(daily_returns) > 0 else 0

    return {
        'sharpe_ratio': float(sharpe),
        'total_return_pct': float(total_return),
        'max_drawdown_pct': float(max_dd),
        'win_rate_pct': float(win_rate),
        'total_trades': int((df['pnl'].abs() > 0).sum()),
    }


def calibrate_asset(symbol, start_date, end_date, threshold_range=None):
    """Run calibration for a single asset."""
    if threshold_range is None:
        threshold_range = np.arange(0.25, 1.0, 0.05)

    print(f"\n{'='*60}")
    print(f"Calibrating {symbol}")
    print(f"{'='*60}")

    ticker = yf.Ticker(symbol.upper())
    df = ticker.history(start=start_date, end=end_date)

    if df.empty:
        print(f"  ERROR: No data for {symbol}")
        return None

    print(f"  Data: {len(df)} days ({start_date} to {end_date})")

    vol_features = compute_vol_features(df)

    # Classical baseline (no QAE)
    baseline = mean_reversion_backtest(df, vol_features, qae_threshold=None)
    if baseline is None:
        return None

    print(f"\n  Classical (no QAE):")
    print(f"    Sharpe: {baseline['sharpe_ratio']:.3f}")
    print(f"    Return: {baseline['total_return_pct']:+.1f}%")
    print(f"    Trades: {baseline['total_trades']}")

    # Sweep thresholds
    results = []
    best_sharpe = -np.inf
    best_threshold = None

    for threshold in threshold_range:
        metrics = mean_reversion_backtest(df, vol_features, qae_threshold=threshold)
        if metrics is None:
            continue

        metrics['threshold'] = threshold
        metrics['delta_sharpe'] = metrics['sharpe_ratio'] - baseline['sharpe_ratio']
        results.append(metrics)

        if metrics['sharpe_ratio'] > best_sharpe:
            best_sharpe = metrics['sharpe_ratio']
            best_threshold = threshold

    # Volatility distribution stats
    vol_values = vol_features.dropna()
    pctiles = {
        'p90': float(np.percentile(vol_values, 90)),
        'p95': float(np.percentile(vol_values, 95)),
        'p99': float(np.percentile(vol_values, 99)),
        'mean': float(vol_values.mean()),
        'std': float(vol_values.std()),
    }

    print(f"\n  Optimal QAE threshold: {best_threshold:.2f}")
    print(f"    Sharpe: {best_sharpe:.3f} (delta: {best_sharpe - baseline['sharpe_ratio']:+.3f})")

    print(f"\n  Volatility distribution:")
    print(f"    Mean: {pctiles['mean']:.3f}, Std: {pctiles['std']:.3f}")
    print(f"    P90: {pctiles['p90']:.3f}, P95: {pctiles['p95']:.3f}, P99: {pctiles['p99']:.3f}")
    print(f"    Optimal threshold is at percentile: ~{100 * (vol_values > best_threshold).mean():.0f}%")

    # Top 5 thresholds
    top5 = sorted(results, key=lambda r: r['sharpe_ratio'], reverse=True)[:5]
    print(f"\n  Top 5 thresholds:")
    for r in top5:
        print(f"    thresh={r['threshold']:.2f}: Sharpe={r['sharpe_ratio']:.3f} (Δ{r['delta_sharpe']:+.3f}) trades={r['total_trades']}")

    return {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'trading_days': len(df),
        'classical': baseline,
        'optimal_threshold': best_threshold,
        'optimal_sharpe': best_sharpe,
        'optimal_delta': best_sharpe - baseline['sharpe_ratio'],
        'vol_distribution': pctiles,
        'all_results': results,
    }


def main():
    parser = argparse.ArgumentParser(description='QAE Threshold Calibrator')
    parser.add_argument('--symbols', nargs='+', default=['SPY', 'AAPL', 'TSLA', 'QQQ'])
    parser.add_argument('--all', action='store_true', help='Run on all common assets')
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default=None)
    args = parser.parse_args()

    if args.all:
        symbols = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BTC-USD']
    else:
        symbols = args.symbols

    end_date = args.end or datetime.now(timezone.utc).strftime('%Y-%m-%d')

    results = []
    for symbol in symbols:
        result = calibrate_asset(symbol, args.start, end_date)
        if result is not None:
            results.append(result)

    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY: Optimal QAE Thresholds")
    print(f"{'='*80}")
    print(f"{'Symbol':<8} {'Classical Sharpe':>16} {'Optimal Sharpe':>16} {'Δ Sharpe':>10} {'Opt Thresh':>12} {'Vol P90':>8} {'Vol P99':>8}")
    print(f"{'-'*80}")

    for r in results:
        s = r['symbol']
        c = r['classical']['sharpe_ratio']
        o = r['optimal_sharpe']
        d = r['optimal_delta']
        t = r['optimal_threshold']
        v90 = r['vol_distribution']['p90']
        v99 = r['vol_distribution']['p99']
        print(f"{s:<8} {c:>16.3f} {o:>16.3f} {d:>10.3f} {t:>12.2f} {v90:>8.3f} {v99:>8.3f}")

    # Save to reports
    output = Path('reports') / 'qae_threshold_calibration.jsonl'
    output.parent.mkdir(parents=True, exist_ok=True)
    for r in results:
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **r,
            'all_results': None,  # too large, skip
        }
        with open(output, 'a') as f:
            f.write(json.dumps(record) + '\n')

    print(f"\nResults saved to {output}")


if __name__ == '__main__':
    main()
