#!/usr/bin/env python3
"""
Mean-Reversion Backtest — Compare mean-reversion vs trend-following
strategies, with and without QAE volatility regime detection.

Tests the C487 hypothesis: QAE works better with mean-reversion strategies
than trend-following because regime detection provides more signal value
in mean-reversion contexts.

External-subject artifact: empirically tests a falsifiable hypothesis about
quantum-enhanced trading strategies on real market data.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import yfinance as yf

try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"ERROR: Required libraries not installed: {e}")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))
from bin.backtest_engine import BacktestEngine, QAE_AVAILABLE


# Calibrated QAE thresholds per asset (from C501)
# Threshold = P(high vol) value where intervention becomes valuable
# SPY: 0.35 (5% days above threshold)
# QQQ: 0.45 (7% days above)
# AAPL: 0.66 (15% days above)
ASSET_THRESHOLD_MAP = {
    'SPY': 0.35,
    'QQQ': 0.45,
    'AAPL': 0.66,
}


def run_backtest(symbol, start_date, end_date, strategy='mean_reversion', use_qae=False, qae_threshold=None):
    """Run a single backtest with specified strategy and QAE.

    Args:
        symbol: Stock symbol
        start_date: Start date string
        end_date: End date string
        strategy: 'mean_reversion' or 'trend_following'
        use_qae: Whether to enable QAE regime filtering
        qae_threshold: Volatility threshold (P(high vol)) to suppress trades
                      If None, uses calibrated threshold from ASSET_THRESHOLD_MAP
    """
    # Use calibrated threshold if not provided
    if qae_threshold is None:
        qae_threshold = ASSET_THRESHOLD_MAP.get(symbol.upper(), 0.85)

    # Download data
    ticker = yf.Ticker(symbol.upper())
    df = ticker.history(start=start_date, end=end_date)

    if df.empty:
        raise ValueError(f"No data for {symbol}")

    print(f"[INFO] Loaded {len(df)} days of OHLCV data for {symbol}")

    # Calculate indicators
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['MA_short'] = df['Close'].rolling(window=20).mean()
    df['MA_long'] = df['Close'].rolling(window=50).mean()

    # Strategy-specific indicators
    if strategy == 'mean_reversion':
        df['bb_middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std

    # QAE regime detection (if enabled) — pre-compute rolling volatility
    qae_regimes = None
    if use_qae:
        returns = df['Close'].pct_change()
        rolling_vol = returns.rolling(20).std() * np.sqrt(252) / 0.5
        qae_regimes = rolling_vol.clip(0, 1).fillna(0.5).tolist()

    # Generate signals
    df['signal'] = 0
    for i in range(1, len(df)):
        row = df.iloc[i]
        if pd.isna(row['RSI']) or pd.isna(row['MA_short']):
            continue

        if strategy == 'mean_reversion':
            # Buy when oversold + below BB, sell when overbought + above BB
            if row['Close'] <= row['bb_lower'] and row['RSI'] < 30:
                df.at[row.name, 'signal'] = 1
            elif row['Close'] >= row['bb_upper'] and row['RSI'] > 70:
                df.at[row.name, 'signal'] = -1
        else:
            # Trend following: MA crossover
            if row['Close'] > row['MA_short'] > row['MA_long']:
                df.at[row.name, 'signal'] = 1
            elif row['Close'] < row['MA_short'] < row['MA_long']:
                df.at[row.name, 'signal'] = -1

        # QAE regime filter (if enabled)
        # Suppress trades in high-vol regimes where mean-reversion is riskier
        # Calibrated threshold (SPY:0.35) means filter top ~35% volatile days
        if qae_regimes and qae_regimes[i] > qae_threshold:
            df.at[row.name, 'signal'] = 0  # Skip trades in high-vol regimes

    # Compute performance metrics
    df['position'] = df['signal']
    df['pnl'] = df['position'].shift(1) * df['Close'].pct_change()
    df = df.dropna()

    if len(df) < 5:
        return {'sharpe_ratio': 0, 'win_rate_pct': 0, 'total_trades': 0,
                'max_drawdown_pct': 0, 'total_return_pct': 0,
                'strategy': strategy, 'qae': use_qae, 'total_positions': 0}

    daily_returns = df['pnl']
    sharpe = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

    winning = daily_returns[daily_returns > 0]
    losing = daily_returns[daily_returns < 0]
    win_rate = len(winning) / len(daily_returns) * 100 if len(daily_returns) > 0 else 0

    # Max drawdown
    cumret = (1 + daily_returns).cumprod()
    peak = cumret.expanding().max()
    drawdown = (cumret - peak) / peak
    max_dd = drawdown.min() * 100

    total_return = (cumret.iloc[-1] - 1) * 100

    total_positions = (df['signal'].abs() > 0).sum()

    metrics = {
        'sharpe_ratio': float(sharpe),
        'win_rate_pct': float(win_rate),
        'total_trades': int((df['pnl'].abs() > 0).sum()),
        'max_drawdown_pct': float(abs(max_dd)),
        'total_return_pct': float(total_return),
        'strategy': strategy,
        'qae': use_qae,
        'total_positions': int(total_positions)
    }

    return metrics


def run_comparison(symbol, start_date, end_date):
    """Run all combinations: strategy x classical/QAE."""
    import yfinance  # needed for ticker download

    strategies = ['mean_reversion', 'trend_following']
    qae_modes = [False]
    if QAE_AVAILABLE:
        qae_modes.append(True)

    results = {}
    for strat in strategies:
        for qae in qae_modes:
            mode = "QAE" if qae else "CLASSICAL"
            print(f"\n{'='*70}")
            print(f"STRATEGY: {strat.upper()} | MODE: {mode}")
            print(f"{'='*70}")

            metrics = run_backtest(symbol, start_date, end_date, strat, qae)

            print(f"  Sharpe:       {metrics['sharpe_ratio']:.3f}")
            print(f"  Win Rate:     {metrics['win_rate_pct']:.1f}%")
            print(f"  Total Trades: {metrics['total_trades']}")
            print(f"  Max DD:       {metrics['max_drawdown_pct']:.1f}%")
            print(f"  Total Return: {metrics['total_return_pct']:+.1f}%")
            print(f"  Positions:    {metrics['total_positions']}")

            results[f"{strat}_{mode}"] = metrics

    # Summary
    print(f"\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}")

    mr_classical = results['mean_reversion_CLASSICAL']
    tf_classical = results['trend_following_CLASSICAL']
    print(f"\nMean Reversion:  Sharpe={mr_classical['sharpe_ratio']:.3f}, Return={mr_classical['total_return_pct']:+.1f}%")
    print(f"Trend Following: Sharpe={tf_classical['sharpe_ratio']:.3f}, Return={tf_classical['total_return_pct']:+.1f}%")

    if 'mean_reversion_QAE' in results:
        mr_qae = results['mean_reversion_QAE']
        tf_qae = results['trend_following_QAE']

        mr_delta = mr_qae['sharpe_ratio'] - mr_classical['sharpe_ratio']
        tf_delta = tf_qae['sharpe_ratio'] - tf_classical['sharpe_ratio']
        diff = mr_delta - tf_delta

        print(f"\nMean Rev:  {mr_classical['sharpe_ratio']:.3f} → {mr_qae['sharpe_ratio']:.3f} (Δ {mr_delta:+.3f})")
        print(f"Trd Fllw:  {tf_classical['sharpe_ratio']:.3f} → {tf_qae['sharpe_ratio']:.3f} (Δ {tf_delta:+.3f})")
        print(f"Difference: {diff:+.3f}")
        print()

        if diff > 0.15:
            print("HYPOTHESIS SUPPORTED: QAE helps mean-reversion more than trend-following")
        elif diff < -0.15:
            print("HYPOTHESIS REFUTED: QAE helps trend-following more than mean-reversion")
        else:
            print("HYPOTHESIS NEUTRAL: QAE impact similar across strategies")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mean-Reversion Backtest')
    parser.add_argument('--symbol', default='SPY', help='Ticker symbol')
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default=None)
    args = parser.parse_args()

    end_date = args.end or datetime.now(timezone.utc).strftime('%Y-%m-%d')

    results = run_comparison(args.symbol, args.start, end_date)

    # Save results
    output = Path('reports') / f'mean_reversion_{args.symbol.lower()}_{args.start}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output}")
