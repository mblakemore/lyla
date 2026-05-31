#!/usr/bin/env python3
"""
Spectral Characterization Pipeline — C544
==========================================
Goes beyond MFCCs into concrete acoustic metrics that answer
"what does this sound actually feel like?"

Metrics computed per-frame and aggregated across a signal:
  - Spectral centroid     : brightness / "center of mass" of the spectrum (Hz)
  - Spectral bandwidth    : spread around the centroid (Hz)
  - Spectral rolloff      : frequency below which X% of energy is contained (Hz)
  - Spectral flatness     : tonal vs. noisy character [0=noise, 1=tonal]
  - Spectral slope        : high-frequency roll-off rate (dB/octave proxy)
  - Zero-crossing rate    : rough estimate of fundamental frequency content
  - Chroma features       : pitch class distribution (12 bins, octave-invariant)

Architecture:
  - Pure numpy/scipy implementation (no librosa dependency)
  - Uses STFT from stft_analysis.py or built-in scipy.signal.stft
  - Reports saved as JSON for downstream analysis
  - Comparative analysis mode for cross-signal characterization

Usage:
  python3 bin/spectral_characterization.py [--signal TYPE] [--rolloff-pct PCT]
  
Signals: multitone | chirp | white-noise | pink-noise | vocal-like | compare
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as sp_signal


# ─── Signal Generation ───────────────────────────────────────────────

def generate_multitone(sr=22050, duration=3.0):
    """Three harmonics at different amplitudes."""
    t = np.arange(int(sr * duration)) / sr
    sig = (1.0 * np.sin(2 * np.pi * 440 * t) +
           0.7 * np.sin(2 * np.pi * 880 * t) +
           0.5 * np.sin(2 * np.pi * 1320 * t))
    return sig, sr


def generate_chirp(sr=22050, duration=4.0):
    """Linear sweep from 200 Hz to 8000 Hz."""
    t = np.arange(int(sr * duration)) / sr
    sig = np.sin(2 * np.pi * sp_signal.chirp(t, f0=200, f1=8000, t1=duration, method='linear'))
    return sig, sr


def generate_white_noise(sr=22050, duration=2.0):
    """Flat spectral density noise."""
    n_samples = int(sr * duration)
    sig = np.random.randn(n_samples)
    # Normalize to [-1, 1]
    sig /= np.max(np.abs(sig))
    return sig, sr


def generate_pink_noise(sr=22050, duration=2.0):
    """1/f noise — equal energy per octave."""
    n_samples = int(sr * duration)
    # Method: filter white noise through 1/sqrt(f) approximation
    # Use Paul Kellet's method via cumulative sum + normalization
    white = np.random.randn(n_samples * 4)
    pink = np.zeros_like(white)
    pink[0] = white[0]
    for i in range(1, len(white)):
        pink[i] = (pink[i-1] * 0.97 + white[i] * 0.33) / 1.0
    # Take first n_samples and normalize
    pink = pink[:n_samples]
    pink -= np.mean(pink)
    pink /= np.max(np.abs(pink))
    return pink, sr


def generate_vocal_like(sr=22050, duration=2.0):
    """Synthetic vowel-like signal: fundamental at ~200 Hz with harmonics 
    shaped by formant peaks (simulating F1~700Hz, F2~1200Hz)."""
    t = np.arange(int(sr * duration)) / sr
    
    # Fundamental frequency
    f0 = 200.0
    
    # Formant frequencies and bandwidths (approximate /a/ vowel)
    formants = [(700, 50), (1200, 80), (2500, 100)]
    
    sig = np.zeros_like(t)
    for h in range(1, 20):  # 20 harmonics
        freq = f0 * h
        amplitude = 1.0 / h  # Harmonic series decay
        
        # Apply formant shaping
        for fc, bw in formants:
            # Simple resonator approximation
            boost = 1.0 + 3.0 * math.exp(-((freq - fc) ** 2) / (2 * bw ** 2))
            amplitude *= boost
        
        sig += (amplitude / max(boost, 1)) * np.sin(2 * np.pi * freq * t)
    
    # Normalize
    sig /= np.max(np.abs(sig))
    
    return sig, sr


SIGNAL_GENERATORS = {
    'multitone': generate_multitone,
    'chirp': generate_chirp,
    'white-noise': generate_white_noise,
    'pink-noise': generate_pink_noise,
    'vocal-like': generate_vocal_like,
}


# ─── Spectral Metrics ────────────────────────────────────────────────

def compute_stft_magnitude(signal, sr=22050, nperseg=1024, noverlap=None):
    """Compute STFT magnitude spectrogram using scipy."""
    if noverlap is None:
        noverlap = nperseg // 2
    
    f, t, Zxx = sp_signal.stft(signal, fs=sr, nperseg=nperseg, noverlap=noverlap)
    magnitude = np.abs(Zxx)
    power = magnitude ** 2
    return f, t, magnitude, power


def spectral_centroid(power, frequencies):
    """Center of mass of the spectrum. Higher = brighter sound."""
    freq_sum = np.sum(frequencies[:, np.newaxis] * power, axis=0)
    power_sum = np.sum(power, axis=0) + 1e-10
    return freq_sum / power_sum


def spectral_bandwidth(power, frequencies, centroid):
    """Spread of frequencies around the centroid."""
    diff = frequencies[:, np.newaxis] - centroid[np.newaxis, :]
    weighted_sq_diff = power * (diff ** 2)
    variance = np.sum(weighted_sq_diff, axis=0) / (np.sum(power, axis=0) + 1e-10)
    return np.sqrt(variance)


def spectral_rolloff(power, frequencies, rolloff_pct=0.95):
    """Frequency below which rolloff_pct of total energy is contained."""
    # Cumulative sum along frequency axis for each frame
    cumsum = np.cumsum(power, axis=0)
    totals = cumsum[-1, :] + 1e-10
    
    rolloff_freqs = []
    threshold = rolloff_pct
    for j in range(cumsum.shape[1]):
        idx = np.searchsorted(cumsum[:, j], threshold * totals[j])
        idx = min(idx, len(frequencies) - 1)
        rolloff_freqs.append(frequencies[idx])
    
    return np.array(rolloff_freqs)


def spectral_flatness(power, n_bins=None):
    """Ratio of geometric mean to arithmetic mean. 
     0 = noise-like, 1 = tone-like."""
    if n_bins is None:
        n_bins = power.shape[0]
    
    # Work on log scale for geometric mean
    eps = 1e-12
    log_power = np.log(power + eps)
    
    geo_mean = np.exp(np.mean(log_power, axis=0))
    arith_mean = np.mean(power, axis=0) + eps
    
    return geo_mean / arith_mean


def spectral_slope(magnitude, frequencies):
    """Slope of the spectrum — rate of high-frequency roll-off.
    Computed via linear regression of magnitude (dB) vs log frequency."""
    # Convert to dB
    mag_db = 20 * np.log10(magnitude + 1e-12)
    
    # Log frequency (skip DC and very low freq)
    valid_mask = frequencies > 50
    log_freq = np.log2(frequencies[valid_mask])
    
    slopes = []
    for j in range(mag_db.shape[1]):
        y = mag_db[valid_mask, j]
        x = log_freq
        # Linear regression slope
        n = len(x)
        if n < 3:
            slopes.append(0.0)
            continue
        sx, sy = np.sum(x), np.sum(y)
        sxy = np.sum(x * y)
        sxx = np.sum(x ** 2)
        denom = n * sxx - sx ** 2
        if abs(denom) < 1e-10:
            slopes.append(0.0)
        else:
            slopes.append((n * sxy - sx * sy) / denom)
    
    return np.array(slopes)


def zero_crossing_rate(signal, sr=22050, frame_size=1024):
    """Rate of sign changes per frame — proxy for high-frequency content."""
    n_samples = len(signal)
    n_frames = max(1, (n_samples - frame_size) // (frame_size // 2) + 1)
    
    zcr = np.zeros(n_frames)
    hop = frame_size // 2
    
    for i in range(n_frames):
        start = i * hop
        end = min(start + frame_size, n_samples)
        frame = signal[start:end]
        
        # Pad to full frame size
        if len(frame) < frame_size:
            frame = np.pad(frame, (0, frame_size - len(frame)), mode='constant')
        
        crossings = np.sum(np.abs(np.diff(np.signbit(frame))) > 0)
        zcr[i] = crossings / (2 * (end - start))  # Normalize by sample rate
    
    return zcr


def chroma_features(magnitude, frequencies, sr=22050, n_chroma=12):
    """Convert magnitude spectrum to chroma (pitch class) representation.
    
    Maps each frequency bin to its nearest pitch class (C, C#, D, ..., B).
    Result is octave-invariant — useful for musical/pitch-based analysis."""
    # MIDI note number from frequency: midi = 69 + 12 * log2(f/440)
    # Chroma = midi mod 12
    
    midi_numbers = 69 + 12 * np.log2(frequencies[1:] / 440.0)  # Skip DC
    chroma_bins = np.round((midi_numbers - 12) % n_chroma).astype(int)
    chroma_bins = np.clip(chroma_bins, 0, n_chroma - 1)
    
    # Weighted distribution: each freq bin contributes proportionally
    n_frames = magnitude.shape[1]
    chroma_matrix = np.zeros((n_chroma, n_frames))
    
    for j in range(n_frames):
        weights = magnitude[1:, j]  # Skip DC
        unique_bins, counts = np.unique(chroma_bins, return_counts=True)
        
        for idx, bin_idx in enumerate(unique_bins):
            # Average weight for this bin
            mask = chroma_bins == bin_idx
            chroma_matrix[int(bin_idx), j] += np.mean(weights[mask]) if np.sum(mask) > 0 else 0
    
    # Normalize each frame to unit vector
    norms = np.linalg.norm(chroma_matrix, axis=0, keepdims=True) + 1e-10
    chroma_matrix /= norms
    
    return chroma_matrix


# ─── Aggregation & Reporting ─────────────────────────────────────

def aggregate_metric(metric_array, name_prefix=""):
    """Compute summary statistics for a per-frame metric."""
    result = {}
    result[f"{name_prefix}mean"] = float(np.mean(metric_array))
    result[f"{name_prefix}std"] = float(np.std(metric_array))
    result[f"{name_prefix}min"] = float(np.min(metric_array))
    result[f"{name_prefix}max"] = float(np.max(metric_array))
    result[f"{name_prefix}median"] = float(np.median(metric_array))
    # Temporal stability (low std/mean ratio = stable over time)
    mean_val = abs(np.mean(metric_array)) + 1e-10
    result[f"{name_prefix}stability_ratio"] = float(np.std(metric_array) / mean_val)
    return result


def compute_all_metrics(signal, sr=22050, rolloff_pct=0.95):
    """Run all spectral metrics on a signal and return aggregated results."""
    print("Computing STFT magnitude...")
    frequencies, times, magnitude, power = compute_stft_magnitude(signal, sr=sr)
    
    print("Spectral centroid...")
    centroid = spectral_centroid(power, frequencies)
    
    print("Spectral bandwidth...")
    bandwidth = spectral_bandwidth(power, frequencies, centroid)
    
    print(f"Spectral rolloff ({rolloff_pct*100:.0f}% threshold)...")
    rolloff = spectral_rolloff(power, frequencies, rolloff_pct)
    
    print("Spectral flatness...")
    flatness = spectral_flatness(power)
    
    print("Spectral slope...")
    slope = spectral_slope(magnitude, frequencies)
    
    print("Zero-crossing rate...")
    zcr = zero_crossing_rate(signal, sr)
    
    print("Chroma features...")
    chroma = chroma_features(magnitude, frequencies, sr)
    
    # Aggregate
    report = {}
    report.update(aggregate_metric(centroid, "spectral_centroid_"))
    report.update(aggregate_metric(bandwidth, "spectral_bandwidth_"))
    report.update(aggregate_metric(rolloff, "spectral_rolloff_"))
    report.update(aggregate_metric(flatness, "spectral_flatness_"))
    report.update(aggregate_metric(slope, "spectral_slope_"))
    report.update(aggregate_metric(zcr, "zcr_"))
    
    # Chroma: report mean energy per pitch class and max concentration
    report["chroma_mean_energy"] = [float(x) for x in np.mean(chroma, axis=1)]
    report["chroma_max_concentration"] = float(np.max(np.max(chroma, axis=0)))
    report["chroma_dominant_class_idx"] = int(np.argmax(np.sum(chroma, axis=1)))
    
    return report, magnitude, power, centroid, bandwidth, rolloff, flatness


# ─── Visualization ─────────────────────────────────────────────

def plot_spectral_characterization(signal_name, freqs, times, magnitude, 
                                    centroid, bandwidth, rolloff, flatness):
    """Create a multi-panel visualization of spectral characteristics."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 16), sharex=True)
    fig.suptitle(f'Spectral Characterization — {signal_name}', fontsize=16)
    
    # 1. Magnitude spectrogram
    ax = axes[0]
    im = ax.pcolormesh(times, freqs[:len(freqs)//2], 
                       magnitude[:len(freqs)//2, :], shading='auto', cmap='viridis')
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title('Magnitude Spectrogram')
    plt.colorbar(im, ax=ax, label='|X|')
    
    # 2. Spectral centroid + bandwidth
    ax = axes[1]
    ax.plot(times, centroid, 'orange', linewidth=1.5, label='Centroid')
    ax.fill_between(times, centroid - bandwidth, centroid + bandwidth, 
                     alpha=0.3, color='orange', label='±Bandwidth')
    ax.set_ylabel('Frequency (Hz)')
    ax.legend(loc='upper right')
    ax.set_title('Spectral Centroid with Bandwidth Envelope')
    ax.set_ylim(0, max(np.max(centroid + bandwidth) * 1.1, 8000))
    
    # 3. Spectral rolloff
    ax = axes[2]
    ax.plot(times, rolloff, 'green', linewidth=1.5)
    ax.set_ylabel('Frequency (Hz)')
    ax.set_title(f'Spectral Rolloff (95% energy threshold)')
    ax.set_ylim(0, max(np.max(rolloff) * 1.1, 8000))
    
    # 4. Spectral flatness
    ax = axes[3]
    ax.plot(times, flatness, 'red', linewidth=1.5)
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Noise/Tone boundary')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Flatness [0=noise, 1=tone]')
    ax.set_title('Spectral Flatness — Tonal vs. Noisy Character')
    ax.legend(loc='upper right')
    ax.set_ylim(-0.05, 1.05)
    
    plt.tight_layout()
    
    outpath = f'outputs/signal_processing/{signal_name}_spectral_characterization.png'
    fig.savefig(outpath, dpi=150, bbox_inches='tight')
    print(f"Visualization saved: {outpath}")
    plt.close(fig)


# ─── Main Pipeline ─────────────────────────────────────────────

def run_single_signal(name):
    """Run spectral characterization on one signal type."""
    print(f"\n{'='*60}")
    print(f"Spectral Characterization: {name}")
    print(f"{'='*60}\n")
    
    generator = SIGNAL_GENERATORS.get(name)
    if generator is None:
        print(f"Unknown signal: {name}. Available: {list(SIGNAL_GENERATORS.keys())}")
        return
    
    sig, sr = generator()
    duration = len(sig) / sr
    
    report = {}
    report["signal"] = {
        "type": name,
        "sr": sr,
        "duration_s": round(duration, 2),
        "n_samples": len(sig),
        "rms_amplitude": float(np.sqrt(np.mean(sig ** 2))),
        "peak_amplitude": float(np.max(np.abs(sig))),
    }
    
    metrics, magnitude, power, centroid, bandwidth, rolloff_vals, flatness = \
        compute_all_metrics(sig, sr=sr)
    report["metrics"] = metrics
    
    # Visualization
    _, times, mag_full, _ = compute_stft_magnitude(sig, sr=sr)
    plot_spectral_characterization(
        name.replace('-', '_'), 
        np.fft.rfftfreq(mag_full.shape[0], d=1.0/sr * mag_full.shape[0]/len(sig)*sr)[:mag_full.shape[0]//2+1],
        times, mag_full[:mag_full.shape[0]//2+1, :],
        centroid, bandwidth, rolloff_vals, flatness
    )
    
    # Save report
    os.makedirs('outputs/signal_processing', exist_ok=True)
    outpath = f'outputs/signal_processing/{name}_spectral_report.json'
    with open(outpath, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {outpath}")
    
    return report


def run_comparison():
    """Run all signal types and produce a comparative analysis."""
    print("\n" + "="*60)
    print("COMPARATIVE SPECTRAL ANALYSIS")
    print("="*60)
    
    results = {}
    for name in SIGNAL_GENERATORS.keys():
        try:
            r = run_single_signal(name)
            if r is not None:
                results[name] = r
        except Exception as e:
            print(f"Error processing {name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Comparative summary
    comparison = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "Cross-signal spectral characterization — comparing tonal vs. noisy signals",
        "signals_analyzed": list(results.keys()),
        "comparisons": {}
    }
    
    # Key metrics to compare across signals
    key_metrics = [
        ("spectral_centroid_mean", "brightness (Hz)"),
        ("spectral_flatness_mean", "tonality [0=noise, 1=tone]"),
        ("spectral_bandwidth_mean", "spectral spread (Hz)"),
        ("spectral_slope_mean", "high-freq roll-off rate"),
        ("zcr_mean", "zero-crossing density"),
        ("chroma_max_concentration", "pitch class dominance"),
    ]
    
    for metric_key, description in key_metrics:
        values = {}
        for sig_name, result in results.items():
            if metric_key in result.get("metrics", {}):
                values[sig_name] = round(result["metrics"][metric_key], 4)
        comparison["comparisons"][metric_key] = {
            "description": description,
            "values_by_signal": values
        }
    
    # Save comparison report
    comp_path = 'outputs/signal_processing/comparative_spectral_report.json'
    with open(comp_path, 'w') as f:
        json.dump(comparison, f, indent=2, default=str)
    print(f"\nComparative report saved: {comp_path}")
    
    return comparison


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Spectral Characterization Pipeline')
    parser.add_argument('--signal', type=str, default='multitone',
                        help=f'Signal type to analyze. Options: compare (all), or {list(SIGNAL_GENERATORS.keys())}')
    parser.add_argument('--rolloff-pct', type=float, default=0.95,
                        help='Rolloff frequency threshold percentage (default: 0.95)')
    
    args = parser.parse_args()
    
    np.random.seed(42)  # Reproducibility
    
    if args.signal == 'compare':
        result = run_comparison()
        
        # Print summary table
        print("\n" + "="*60)
        print("COMPARATIVE SUMMARY")
        print("="*60)
        for metric_key, info in result.get("comparisons", {}).items():
            print(f"\n{info['description']}:")
            for sig_name, val in info["values_by_signal"].items():
                print(f"  {sig_name:>15s}: {val}")
        
    else:
        result = run_single_signal(args.signal)


if __name__ == '__main__':
    main()
