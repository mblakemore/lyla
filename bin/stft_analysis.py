#!/usr/bin/env python3
"""
STFT Analysis Pipeline — Signal Processing Workstream C543

Core toolkit for short-time Fourier transform analysis, reconstruction,
and spectrogram visualization. Connects GP spectral kernels (C523),
Bayesian inference patterns, and causal discovery to frequency-domain
thinking.

Usage:
    python stft_analysis.py --demo              # synthetic multi-tone demo
    python stft_analysis.py --input file.wav    # analyze real audio file
    python -c "from stft_analysis import compute_stft"  # as library
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as sp_signal


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def compute_stft(x: np.ndarray, sr: int, window: str = 'hann',
                 nperseg: int = 1024, noverlap: int | None = None) -> tuple:
    """Compute STFT of a 1-D signal.

    Parameters
    ----------
    x : array-like
        Input signal samples.
    sr : int
        Sampling rate in Hz.
    window : str or tuple
        Window function name ('hann', 'hamming', 'blackman', etc.).
    nperseg : int
        Number of samples per FFT segment (controls frequency resolution).
        Δf = sr / nperseg.
    noverlap : int or None
        Samples of overlap between segments. Default = nperseg // 2 (50%).

    Returns
    -------
    freqs : ndarray
        Frequency bin centers in Hz.
    times : ndarray
        Time points (center of each segment) in seconds.
    Zxx : complex ndarray [n_freqs, n_times]
        Complex STFT coefficients. Magnitude = |Zxx|, phase = ∠Zxx.

    Notes
    -----
    Frequency resolution is inversely proportional to window length.
    Longer windows → finer Δf but poorer time localization (uncertainty principle).
    Hann window gives good side-lobe suppression (~−31 dB) with moderate main-lobe width.
    """
    if noverlap is None:
        noverlap = nperseg // 2

    x = np.asarray(x, dtype=np.float64)
    
    freqs, times, Zxx = sp_signal.stft(
        x, fs=sr, window=window, nperseg=nperseg, noverlap=noverlap,
        return_onesided=True
    )
    return freqs, times, Zxx


def reconstruct_from_stft(Zxx: np.ndarray, sr: int, window: str = 'hann',
                          nperseg: int = 1024,
                          noverlap: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Reconstruct a signal from its STFT coefficients (inverse STFT).

    Parameters
    ----------
    Zxx : complex ndarray [n_freqs, n_times]
        Complex STFT coefficients from compute_stft().
    sr : int
        Sampling rate in Hz.
    window : str or tuple
        Window function — must match what was used in compute_stft().
    nperseg, noverlap : int
        Must match the parameters used during forward transform.

    Returns
    -------
    t : ndarray
        Reconstruction time vector.
    x : ndarray
        Reconstructed signal samples.
    """
    if noverlap is None:
        noverlap = nperseg // 2
    t, x = sp_signal.istft(Zxx, fs=sr, window=window, nperseg=nperseg,
                           noverlap=noverlap)
    return t, x


def spectral_entropy(Zxx: np.ndarray, axis: int = 1) -> np.ndarray:
    """Compute spectral entropy — measure of frequency content uniformity.

    High entropy → energy spread across many frequencies (noise-like).
    Low entropy → energy concentrated at few frequencies (tonal).

    Parameters
    ----------
    Zxx : complex ndarray
        STFT coefficients.
    axis : int
        Axis along which to compute entropy (default=1, per time frame).

    Returns
    -------
    entropy : ndarray
        Spectral entropy values (nats, natural log base e).
    """
    power = np.abs(Zxx) ** 2
    total_power = power.sum(axis=axis, keepdims=True) + 1e-30
    p = power / total_power
    # Shannon entropy in nats
    entropy = -np.sum(p * np.log(p + 1e-30), axis=axis)
    return entropy


def dominant_frequencies(Zxx: np.ndarray, freqs: np.ndarray,
                         top_k: int = 5, axis: int = 1) -> tuple:
    """Find the K dominant frequency components in each time frame.

    Parameters
    ----------
    Zxx : complex ndarray [n_freqs, n_times]
    freqs : ndarray[n_freqs]
    top_k : int
        Number of dominant frequencies to extract.
    axis : int
        Axis for frequency dimension.

    Returns
    -------
    dom_freqs : ndarray[top_k, n_times]
        Frequencies of the top-K peaks at each time step.
    dom_mags : ndarray[top_k, n_times]
        Magnitudes at those frequencies.
    """
    magnitude = np.abs(Zxx)
    n_freqs = magnitude.shape[0]
    k = min(top_k, n_freqs)

    idx = np.argpartition(magnitude, -k, axis=axis)[-k:]
    idx_sorted = np.sort(idx, axis=axis)

    dom_freqs = np.take_along_axis(freqs[:, None], idx_sorted, axis=0)
    dom_mags = np.take_along_axis(magnitude, idx_sorted, axis=0)

    return dom_freqs, dom_mags


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_spectrogram(freqs: np.ndarray, times: np.ndarray, Zxx: np.ndarray,
                     title: str = 'Spectrogram', save_path: str | None = None,
                     dB_floor: float = -80):
    """Plot a log-magnitude spectrogram with proper axis labeling.

    Parameters
    ----------
    freqs, times, Zxx : from compute_stft()
    title : str
        Plot title.
    save_path : str or None
        If provided, save figure to this path (PNG).
    dB_floor : float
        Minimum dB value for colormap scaling.
    """
    magnitude_db = 20 * np.log10(np.abs(Zxx) + 1e-10)

    fig, axes = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={
        'height_ratios': [1, 1, 1]
    })
    fig.suptitle(title, fontsize=16, fontweight='bold')

    # --- Spectrogram ---
    im = axes[0].pcolormesh(times, freqs, magnitude_db, shading='gouraud',
                            cmap='viridis', vmin=dB_floor, vmax=0)
    axes[0].set_ylabel('Frequency (Hz)')
    axes[0].set_title(f'Spectrogram ({len(freqs)} bins, {len(times)} frames)')
    plt.colorbar(im, ax=axes[0], label='Magnitude (dB)', shrink=0.8)

    # --- Power spectral density average ---
    avg_power = 10 * np.log10(np.mean(np.abs(Zxx) ** 2, axis=1) + 1e-10)
    axes[1].plot(freqs, avg_power, linewidth=1.5)
    axes[1].set_xlabel('Frequency (Hz)')
    axes[1].set_ylabel('Avg Power (dB)')
    axes[1].set_title('Average Power Spectrum')
    axes[1].grid(True, alpha=0.3)

    # --- Spectral entropy over time ---
    entropy = spectral_entropy(Zxx, axis=0)
    max_entropy = np.log(len(freqs))
    axes[2].plot(times, entropy, color='crimson', linewidth=1.5)
    axes[2].axhline(max_entropy / 2, color='gray', linestyle='--', alpha=0.5)
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('Spectral Entropy (nats)')
    axes[2].set_title(f'Spectral Entropy (max possible: {max_entropy:.2f})')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved spectrogram to {save_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Synthetic signal generators for testing
# ---------------------------------------------------------------------------

def generate_multitone_signal(sr: int, duration: float,
                              frequencies: list[float],
                              amplitudes: list[float] | None = None,
                              noise_level: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic multi-tone signal with optional noise.

    Parameters
    ----------
    sr : int
        Sampling rate in Hz.
    duration : float
        Signal length in seconds.
    frequencies : list of float
        Frequencies of sinusoidal components in Hz.
    amplitudes : list of float or None
        Per-component amplitudes. Default = equal amplitude.
    noise_level : float
        Standard deviation of additive Gaussian noise (relative to max amplitude).

    Returns
    -------
    t : ndarray
        Time vector.
    x : ndarray
        Generated signal samples.
    """
    t = np.arange(int(sr * duration)) / sr
    if amplitudes is None:
        amplitudes = [1.0] * len(frequencies)

    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in zip(frequencies, amplitudes))

    if noise_level > 0 and amplitudes:
        x += np.random.normal(0, noise_level * max(amplitudes), size=t.shape)

    return t, x


def generate_chirp_signal(sr: int, duration: float,
                          f_start: float = 200, f_end: float = 4000,
                          noise_level: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """Generate a linear chirp (frequency sweeps from f_start to f_end).

    Useful for testing time-frequency resolution tradeoffs.
    """
    t = np.arange(int(sr * duration)) / sr
    # Quadratic phase → linear frequency sweep
    k = (f_end - f_start) / duration
    phase = 2 * np.pi * (f_start * t + 0.5 * k * t ** 2)
    x = np.sin(phase)

    if noise_level > 0:
        x += np.random.normal(0, noise_level, size=t.shape)

    return t, x


# ---------------------------------------------------------------------------
# Reconstruction validation
# ---------------------------------------------------------------------------

def validate_reconstruction(x_original: np.ndarray, freqs: np.ndarray,
                            times: np.ndarray, Zxx: np.ndarray,
                            sr: int, window: str = 'hann',
                            nperseg: int = 1024,
                            noverlap: int | None = None) -> dict:
    """Validate round-trip STFT → reconstruction fidelity.

    Returns metrics dict with:
    - mse: mean squared error between original and reconstructed
    - snr: signal-to-noise ratio in dB
    - max_abs_error: maximum absolute deviation
    - correlation: Pearson correlation coefficient
    """
    _, x_reconstructed = reconstruct_from_stft(Zxx, sr, window=window,
                                                nperseg=nperseg, noverlap=noverlap)

    # Align lengths (ISTFT may produce slightly different length)
    min_len = min(len(x_original), len(x_reconstructed))
    x_orig_trimmed = x_original[:min_len]
    x_rec_trimmed = x_reconstructed[:min_len]

    diff = x_orig_trimmed - x_rec_trimmed
    mse = float(np.mean(diff ** 2))
    power = float(np.mean(x_orig_trimmed ** 2))
    snr_db = 10 * np.log10(power / (mse + 1e-30)) if mse > 0 else float('inf')
    max_err = float(np.max(np.abs(diff)))
    corr = float(np.corrcoef(x_orig_trimmed, x_rec_trimmed)[0, 1])

    return {
        'mse': mse,
        'snr_db': round(snr_db, 2),
        'max_absolute_error': max_err,
        'correlation': round(corr, 6),
        'samples_compared': min_len,
        'pass': bool(snr_db > 40),  # 40 dB SNR threshold for "good" reconstruction
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='STFT Analysis Pipeline — signal processing toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --demo                    Run synthetic multi-tone demo
  %(prog)s --chirp                   Run chirp sweep demo
  %(prog)s --input file.wav          Analyze a real audio file (if scipy.io available)
        """
    )
    parser.add_argument('--demo', action='store_true',
                        help='Generate and analyze synthetic multi-tone signal')
    parser.add_argument('--chirp', action='store_true',
                        help='Generate and analyze chirp sweep signal')
    parser.add_argument('--input', '-i', type=str, default=None,
                        help='Input audio file path (WAV only, via scipy.io)')
    parser.add_argument('--output-dir', '-o', type=str, default='outputs/signal_processing/',
                        help='Output directory for spectrograms and reports')
    parser.add_argument('--nperseg', type=int, default=1024,
                        help='FFT segment size (default 1024). Larger = better freq resolution.')
    parser.add_argument('--noise', type=float, default=0.05,
                        help='Noise level for synthetic signals (default 0.05)')

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not (args.demo or args.chirp or args.input):
        # Default: run demo
        args.demo = True

    # --- Demo mode ---
    if args.demo:
        print("=" * 60)
        print("STFT Analysis — Multi-Tone Synthetic Signal Demo")
        print("=" * 60)

        sr = 22050  # CD-quality sampling rate
        duration = 3.0
        frequencies = [440.0, 880.0, 1320.0]  # A4, A5, E6
        amplitudes = [1.0, 0.7, 0.5]

        t, x = generate_multitone_signal(
            sr=sr, duration=duration,
            frequencies=frequencies, amplitudes=amplitudes,
            noise_level=args.noise
        )

        freqs, times, Zxx = compute_stft(x, sr, window='hann', nperseg=args.nperseg)

        # Spectrogram visualization
        spec_path = str(out_dir / 'multitone_spectrogram.png')
        plot_spectrogram(freqs, times, Zxx,
                         title=f'Multi-Tone Signal ({", ".join(str(f) for f in frequencies)})',
                         save_path=spec_path)

        # Reconstruction validation
        metrics = validate_reconstruction(x, freqs, times, Zxx, sr, window='hann',
                                          nperseg=args.nperseg)
        report_path = out_dir / 'multitone_report.json'
        report_data = {
            'signal': {
                'type': 'multi-tone',
                'frequencies_hz': frequencies,
                'amplitudes': amplitudes,
                'sampling_rate': sr,
                'duration_s': duration,
                'nperseg': args.nperseg,
                'noise_level': args.noise
            },
            'stft': {
                'window': 'hann',
                'frequency_resolution_hz': round(sr / args.nperseg, 2),
                'time_resolution_s': round((args.nperseg // 2) / sr, 4),
                'n_freq_bins': len(freqs),
                'n_time_frames': len(times)
            },
            'reconstruction': metrics
        }
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\nSignal: {frequencies} Hz, durations={duration}s, noise={args.noise}")
        print(f"STFT params: nperseg={args.nperseg}, Δf={sr/args.nperseg:.1f} Hz")
        print(f"Reconstruction SNR: {metrics['snr_db']} dB {'✓ PASS' if metrics['pass'] else '✗ FAIL'}")
        print(f"MSE: {metrics['mse']:.6e}")
        print(f"Correlation: {metrics['correlation']}")
        print(f"Report saved to: {report_path}")

    # --- Chirp mode ---
    if args.chirp:
        print("\n" + "=" * 60)
        print("STFT Analysis — Chirp Sweep Demo")
        print("=" * 60)

        sr = 22050
        duration = 4.0

        t, x = generate_chirp_signal(
            sr=sr, duration=duration,
            f_start=200, f_end=8000,
            noise_level=args.noise
        )

        freqs, times, Zxx = compute_stft(x, sr, window='hann', nperseg=args.nperseg)

        spec_path = str(out_dir / 'chirp_spectrogram.png')
        plot_spectrogram(freqs, times, Zxx,
                         title=f'Chirp Sweep (200→8000 Hz over {duration}s)',
                         save_path=spec_path)

        metrics = validate_reconstruction(x, freqs, times, Zxx, sr, window='hann',
                                          nperseg=args.nperseg)
        report_path = out_dir / 'chirp_report.json'
        report_data = {
            'signal': {
                'type': 'linear-chirp',
                'f_start_hz': 200, 'f_end_hz': 8000,
                'sampling_rate': sr, 'duration_s': duration,
                'noise_level': args.noise
            },
            'stft': {
                'window': 'hann',
                'nperseg': args.nperseg,
                'frequency_resolution_hz': round(sr / args.nperseg, 2),
                'time_resolution_s': round((args.nperseg // 2) / sr, 4)
            },
            'reconstruction': metrics
        }
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\nChirp: 200→8000 Hz over {duration}s")
        print(f"Reconstruction SNR: {metrics['snr_db']} dB {'✓ PASS' if metrics['pass'] else '✗ FAIL'}")
        print(f"MSE: {metrics['mse']:.6e}")
        print(f"Report saved to: {report_path}")


if __name__ == '__main__':
    main()
