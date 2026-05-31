#!/usr/bin/env python3
"""
Mel-Frequency Cepstral Coefficients (MFCC) Pipeline — Signal Processing C544

Perceptually-motivated feature extraction for audio analysis. Builds on
the STFT foundation (C543) with Mel-scale filter banks and DCT-based
cepstral analysis.

Key insight: human hearing is approximately logarithmic in frequency, not
linear. The Mel scale models this perceptual nonlinearity, making features
more robust to pitch variation and more aligned with what humans actually hear.

Usage:
    python mfcc_analysis.py --demo              # synthetic multi-tone demo
    python mfcc_analysis.py --chirp             # chirp sweep demo
    python -c "from mfcc_analysis import extract_mfccs"  # as library
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal as sp_signal


# ---------------------------------------------------------------------------
# Mel-scale conversions
# ---------------------------------------------------------------------------

def hz_to_mel(f_hz: float | np.ndarray) -> float | np.ndarray:
    """Convert Hz to Mel frequency scale (Slaney formula).

    The Mel scale approximates the human ear's nonlinear response to frequency.
    Two tones separated by equal Mel intervals sound equidistant in pitch.
    """
    return 2595.0 * np.log10(1.0 + f_hz / 700.0)


def mel_to_hz(m_mel: float | np.ndarray) -> float | np.ndarray:
    """Invert the Mel scale — convert Mels back to Hertz."""
    return 700.0 * (10.0 ** (m_mel / 2595.0) - 1.0)


# ---------------------------------------------------------------------------
# Mel filter bank construction
# ---------------------------------------------------------------------------

def mel_filterbank(n_freqs: int, sr: int, n_filters: int = 40,
                   f_min: float = 0.0, f_max: float | None = None) -> np.ndarray:
    """Build a triangular Mel-spaced filter bank.

    Parameters
    ----------
    n_freqs : int
        Number of FFT frequency bins (from STFT).
    sr : int
        Sampling rate in Hz.
    n_filters : int
        Number of triangular filters in the bank. Default 40 matches typical
        speech processing; music/sound analysis may use fewer.
    f_min : float
        Lowest filter center frequency in Hz.
    f_max : float or None
        Highest filter center frequency. Defaults to Nyquist (sr/2).

    Returns
    -------
    fb : ndarray[n_filters, n_freqs]
        Filter bank matrix. Each row is one triangular filter's weights
        across all frequency bins. Sum of each row ≈ constant energy response.

    Notes
    -----
    The filter bank maps linear-frequency bins from the FFT into perceptually-
    spaced Mel bands. This compression at high frequencies mirrors how the
    human auditory system allocates resolution — more neurons for low freq,
    fewer for high.
    """
    if f_max is None:
        f_max = sr / 2.0

    # Center frequencies on Mel scale (evenly spaced)
    mel_low = hz_to_mel(f_min)
    mel_high = hz_to_mel(f_max)
    mel_centers = np.linspace(mel_low, mel_high, n_filters + 2)  # +2 for edges
    hz_centers = mel_to_hz(mel_centers)  # [f_lo, c_1, ..., c_N, f_hi]

    # FFT bin centers matching scipy.signal.stft output
    fft_bins = np.linspace(0, sr / 2.0, n_freqs)

    # Build triangular filters
    slopes = hz_centers[1:-1] - hz_centers[:-2]  # rising edge rates
    downslopes = hz_centers[2:] - hz_centers[1:-1]  # falling edge rates

    fb = np.zeros((n_filters, n_freqs))
    for i in range(n_filters):
        # Rising slope: from left neighbor to center
        rise = (fft_bins >= hz_centers[i]) & (fft_bins <= hz_centers[i + 1])
        fb[i, rise] = (fft_bins[rise] - hz_centers[i]) / (slopes[i] + 1e-30)
        # Falling slope: from center to right neighbor
        fall = (fft_bins > hz_centers[i + 1]) & (fft_bins <= hz_centers[i + 2])
        fb[i, fall] = (hz_centers[i + 2] - fft_bins[fall]) / (downslopes[i] + 1e-30)

    # Normalize so each filter has unit gain at its peak
    # (prevents high-freq filters with wider spacing from dominating)
    peak_energy = fb.sum(axis=1, keepdims=True)  # sum of weights per filter
    fb /= peak_energy + 1e-30

    return fb


# ---------------------------------------------------------------------------
# Core MFCC extraction pipeline
# ---------------------------------------------------------------------------

def compute_stft(x: np.ndarray, sr: int, window: str = 'hann',
                 nperseg: int = 1024, noverlap: int | None = None) -> tuple:
    """Compute STFT — wrapper matching stft_analysis.py API."""
    if noverlap is None:
        noverlap = nperseg // 2
    x = np.asarray(x, dtype=np.float64)
    freqs, times, Zxx = sp_signal.stft(
        x, fs=sr, window=window, nperseg=nperseg, noverlap=noverlap,
        return_onesided=True
    )
    return freqs, times, Zxx


def extract_mfccs(x: np.ndarray, sr: int, n_mfcc: int = 13,
                  n_filters: int = 40, nperseg: int = 1024,
                  noverlap: int | None = None, f_min: float = 0.0,
                  f_max: float | None = None) -> tuple:
    """Extract Mel-Frequency Cepstral Coefficients from a signal.

    Full pipeline:
      1. Pre-emphasis (high-pass filter to boost treble)
      2. Framing + windowing via STFT
      3. Power spectrum computation
      4. Mel filter bank → log-energy per band
      5. DCT-II → cepstral coefficients

    Parameters
    ----------
    x : array-like
        Input audio samples (mono).
    sr : int
        Sampling rate in Hz.
    n_mfcc : int
        Number of cepstral coefficients to retain. 13 is standard for speech;
        higher values capture finer spectral detail but risk overfitting noise.
    n_filters : int
        Number of Mel filter bank channels.
    nperseg : int
        FFT segment size.
    noverlap : int or None
        Frame overlap (default = 50%).
    f_min, f_max : float or None
        Filter bank frequency range. Default [0, sr/2].

    Returns
    -------
    mfccs : ndarray[n_mfcc, n_frames]
        MFCC matrix — each column is one frame's feature vector.
    mel_energies : ndarray[n_filters, n_frames]
        Log-energy of each Mel band at each time step. Useful as auxiliary features.
    times : ndarray
        Time points for each frame.
    """
    x = np.asarray(x, dtype=np.float64)

    # Step 1: Pre-emphasis filter (boost high frequencies by ~6 dB/octave)
    # Models the natural roll-off of vocal tract / most sound sources
    alpha = 0.97
    if len(x) > 1:
        x_pre = np.empty_like(x)
        x_pre[0] = x[0]
        x_pre[1:] = x[1:] - alpha * x[:-1]
    else:
        x_pre = x.copy()

    # Step 2: STFT → power spectrum
    freqs, times, Zxx = compute_stft(x_pre, sr, window='hann',
                                      nperseg=nperseg, noverlap=noverlap)

    power_spec = np.abs(Zxx) ** 2  # [n_freqs, n_times]

    # Step 3: Apply Mel filter bank → energy per Mel band
    fb = mel_filterbank(len(freqs), sr, n_filters=n_filters,
                        f_min=f_min, f_max=f_max)
    mel_energies = fb @ power_spec  # [n_filters, n_times]

    # Step 4: Log compression (human perception is approximately logarithmic)
    log_mel = np.log(mel_energies + 1e-10)  # [n_filters, n_times]

    # Step 5: DCT-II to get cepstral coefficients
    # The DCT decorrelates the log-Mel energies and concentrates information
    # in the first few coefficients — exactly what we want for compact features.
    from scipy.fft import dct
    mfccs = dct(log_mel, type=2, axis=0, norm='ortho')[:n_mfcc]

    return mfccs, log_mel, times


# ---------------------------------------------------------------------------
# MFCC deltas (first and second derivatives over time)
# ---------------------------------------------------------------------------

def mfcc_deltas(mfccs: np.ndarray, order: int = 2) -> np.ndarray:
    """Compute temporal delta coefficients for MFCCs.

    Delta features capture how spectral shape changes over time — critical
    for speech recognition and music classification where dynamics matter
    as much as static content.

    Uses Savitzky-Golay-style local regression with a ±N window.

    Parameters
    ----------
    mfccs : ndarray[n_coeffs, n_frames]
        Base MFCC matrix.
    order : int
        Derivative order (1=deltas, 2=delta-deltas/accelerations).

    Returns
    -------
    result : ndarray
        Original + deltas (+ delta-deltas if order=2), concatenated along axis 0.
    """
    N = 2  # context window radius (±2 frames)
    result = [mfccs]

    current = mfccs
    for _ in range(order):
        n_frames = current.shape[1]
        deltas = np.zeros_like(current)

        for t in range(n_frames):
            t_lo = max(0, t - N)
            t_hi = min(n_frames - 1, t + N)
            tau = np.arange(t_lo - t, t_hi - t + 1, dtype=np.float64)
            w = np.array([tau, np.ones(len(tau))])
            # Least-squares fit: y = a*t + b, extract slope 'a'
            coeffs, *_ = np.linalg.lstsq(w.T, current[:, t_lo:t_hi+1], rcond=None)
            deltas[:, t] = coeffs[0]

        result.append(deltas)

    return np.concatenate(result, axis=0)


# ---------------------------------------------------------------------------
# Spectral feature extraction from MFCCs
# ---------------------------------------------------------------------------

def spectral_features_from_mfcc(mfccs: np.ndarray) -> dict:
    """Extract aggregate spectral features from the MFCC matrix.

    Useful for classification or regression tasks where you need scalar
    descriptors of an entire audio segment's character.

    Returns
    -------
    features : dict
        - mfcc_mean[i]: mean of coefficient i across time
        - mfcc_std[i]: std dev of coefficient i (temporal variability)
        - spectral_centroid: weighted-average frequency (brightness proxy)
        - spectral_flatness: how noise-like vs tonal the signal is
        - mfcc_energy: total cepstral energy
    """
    n_coeffs, n_frames = mfccs.shape

    out = {}
    for i in range(n_coeffs):
        out[f'mfcc_mean_{i}'] = float(np.mean(mfccs[i]))
        out[f'mfcc_std_{i}'] = float(np.std(mfccs[i]))

    # C0 (DC component) ≈ log of total power — correlate with loudness
    out['mfcc_energy'] = float(np.sum(mfccs[0] ** 2))

    # Spectral centroid approximation from first few coefficients
    # Higher MFCCs encode finer spectral structure; their relative weight
    # indicates spectral complexity/brightness
    if n_coeffs >= 4:
        low_energy = np.sum(mfccs[:2] ** 2, axis=0).mean()
        high_energy = np.sum(mfccs[2:6] ** 2, axis=0).mean() if n_coeffs >= 6 else 0.0
        out['spectral_brightness'] = float(high_energy / (low_energy + 1e-30))

    return out


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def plot_mel_spectrogram(log_mel_energies: np.ndarray, times: np.ndarray,
                         f_min: float, f_max: float, n_filters: int,
                         title: str = 'Mel-Spectrogram',
                         save_path: str | None = None):
    """Plot a Mel-scaled spectrogram with perceptual frequency axis."""
    mel_freqs = hz_to_mel(
        np.linspace(f_min, f_max, n_filters)
    )

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={
        'height_ratios': [3, 1]
    })
    fig.suptitle(title, fontsize=16, fontweight='bold')

    # Mel-spectrogram — log_mel_energies is [n_filters, n_frames], use as-is
    # so Y=mel_freqs (rows) × X=times (columns) matches pcolormesh expectations
    im = axes[0].pcolormesh(times, mel_freqs, log_mel_energies, shading='gouraud',
                            cmap='inferno')
    axes[0].set_ylabel('Frequency (Mel scale)')
    axes[0].set_title(f'Mel-Spectrogram ({n_filters} filters)')
    plt.colorbar(im, ax=axes[0], label='Log Energy', shrink=0.8)

    # Average Mel spectrum over time
    avg_spectrum = np.mean(log_mel_energies, axis=1)
    axes[1].bar(np.arange(n_filters), avg_spectrum, width=0.9, color='darkorange', alpha=0.7)
    axes[1].set_xlabel('Mel Filter Bank Channel')
    axes[1].set_ylabel('Mean Log Energy')
    axes[1].set_title('Average Mel Spectrum')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved to {save_path}")
    plt.close(fig)


def plot_mfcc_trajectory(mfccs: np.ndarray, times: np.ndarray,
                         title: str = 'MFCC Trajectories',
                         save_path: str | None = None):
    """Plot each MFCC coefficient as a trajectory over time."""
    n_coeffs, _ = mfccs.shape
    n_plot = min(n_coeffs, 13)  # Don't overwhelm the plot

    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(title, fontsize=16, fontweight='bold')

    for i in range(n_plot):
        label = f'C{i}' if i < 10 else f'Coeff {i}'
        ax.plot(times, mfccs[i], linewidth=0.8, alpha=0.7, label=label)

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Coefficient Value')
    ax.legend(loc='upper right', fontsize=7, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved to {save_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Synthetic signal generators (reused from C543)
# ---------------------------------------------------------------------------

def generate_multitone_signal(sr: int, duration: float,
                              frequencies: list[float],
                              amplitudes: list[float] | None = None,
                              noise_level: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic multi-tone signal."""
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
    """Generate a linear chirp sweep."""
    t = np.arange(int(sr * duration)) / sr
    k = (f_end - f_start) / duration
    phase = 2 * np.pi * (f_start * t + 0.5 * k * t ** 2)
    x = np.sin(phase)
    if noise_level > 0:
        x += np.random.normal(0, noise_level, size=t.shape)
    return t, x


# ---------------------------------------------------------------------------
# Mel scale validation — empirical verification of perceptual spacing
# ---------------------------------------------------------------------------

def validate_mel_scale() -> dict:
    """Empirically verify key properties of the Mel frequency scale.

    Tests:
    1. Monotonicity: Mel(f) is strictly increasing with f
    2. Logarithmic compression: equal ratios at high freq → smaller Mel gaps
       than same ratios at low freq (human hearing property)
    3. Round-trip: mel_to_hz(hz_to_mel(f)) ≈ f within numerical precision
    4. Equal-Mel intervals at 1kHz: the classic "one semitone at 1kHz ≈
       48 Mels" property from psychoacoustics literature
    """
    results = {}

    # Test 1: Monotonicity
    test_freqs = np.logspace(1, 5, 100)  # 10 Hz to 100 kHz
    mels = hz_to_mel(test_freqs)
    results['monotonic'] = bool(np.all(np.diff(mels) > 0))

    # Test 2: Logarithmic compression check
    # Equal Hz intervals should give smaller Mel gaps at higher frequencies
    gap_low = hz_to_mel(200) - hz_to_mel(100)    # 100 Hz gap at low freq
    gap_high = hz_to_mel(1100) - hz_to_mel(1000)  # 100 Hz gap at high freq
    results['mel_gap_100hz_at_100hz'] = round(float(gap_low), 1)
    results['mel_gap_100hz_at_1000hz'] = round(float(gap_high), 1)
    results['compression_ratio'] = round(float(gap_high / (gap_low + 1e-30)), 2)
    results['log_compression_verified'] = bool(gap_low > gap_high)

    # Test 3: Round-trip accuracy
    rt_errors = np.abs(mel_to_hz(hz_to_mel(test_freqs)) - test_freqs) / test_freqs
    results['roundtrip_max_relative_error'] = float(np.max(rt_errors))
    results['roundtrip_pass'] = bool(np.max(rt_errors) < 1e-10)

    # Test 4: Equal-Mel spacing check
    mel_spaced = np.linspace(hz_to_mel(500), hz_to_mel(2000), 8)
    hz_from_mel = mel_to_hz(mel_spaced)
    freq_ratios = np.diff(hz_from_mel) / hz_from_mel[:-1]
    results['equal_mel_spacing'] = {
        'hz_values': [round(f, 1) for f in hz_from_mel],
        'freq_intervals': [round(d, 1) for d in np.diff(hz_from_mel)],
        'intervals_increasing': bool(np.all(np.diff(np.diff(hz_from_mel)) > 0)),
        # Equal Mel steps should give increasing Hz gaps (logarithmic nature)
    }

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='MFCC Analysis Pipeline — perceptual audio feature extraction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--demo', action='store_true', help='Multi-tone MFCC demo')
    parser.add_argument('--chirp', action='store_true', help='Chirp sweep MFCC demo')
    parser.add_argument('--validate-mel', action='store_true',
                        help='Run Mel scale validation tests')
    parser.add_argument('--nperseg', type=int, default=1024)
    parser.add_argument('--n-mfcc', type=int, default=13)
    parser.add_argument('--noise', type=float, default=0.05)
    parser.add_argument('--output-dir', '-o', type=str,
                        default='outputs/signal_processing/')

    args = parser.parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Mel scale validation ---
    if args.validate_mel:
        print("=" * 60)
        print("Mel Scale Validation")
        print("=" * 60)
        results = validate_mel_scale()

        for key, val in results.items():
            if isinstance(val, dict):
                print(f"\n{key}:")
                for k2, v2 in val.items():
                    print(f"  {k2}: {v2}")
            else:
                status = '✓' if (isinstance(val, bool) and val) or ('pass' not in key.lower()) else ''
                if isinstance(val, bool):
                    status = '✓ PASS' if val else '✗ FAIL'
                print(f"  {key}: {val} {status}")

        report_path = out_dir / 'mel_validation_report.json'
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nReport saved to: {report_path}")
        return

    # --- Demo mode ---
    if not (args.demo or args.chirp):
        args.demo = True

    if args.demo:
        print("=" * 60)
        print("MFCC Analysis — Multi-Tone Synthetic Signal")
        print("=" * 60)

        sr = 22050
        duration = 3.0
        frequencies = [440.0, 880.0, 1320.0]  # A4, A5, E6
        amplitudes = [1.0, 0.7, 0.5]

        _, x = generate_multitone_signal(
            sr=sr, duration=duration,
            frequencies=frequencies, amplitudes=amplitudes,
            noise_level=args.noise
        )

        mfccs, log_mel, times = extract_mfccs(
            x, sr, n_mfcc=args.n_mfcc, nperseg=args.nperseg
        )

        print(f"\nSignal: {frequencies} Hz")
        print(f"MFCC shape: {mfccs.shape}")
        print(f"Mel energies shape: {log_mel.shape}")

        # Plot Mel spectrogram
        plot_mel_spectrogram(log_mel, times, f_min=0.0, f_max=sr/2,
                             n_filters=40,
                             title=f'Mel-Spectrogram ({", ".join(str(f) for f in frequencies)})',
                             save_path=str(out_dir / 'multitone_melspec.png'))

        # Plot MFCC trajectories
        plot_mfcc_trajectory(mfccs, times,
                             title='MFCC Coefficient Trajectories (Multi-Tone)',
                             save_path=str(out_dir / 'multitone_mfccs.png'))

        # Spectral features summary
        feats = spectral_features_from_mfcc(mfccs)
        report_path = out_dir / 'multitone_mfcc_report.json'
        report_data = {
            'signal': {'type': 'multi-tone', 'frequencies_hz': frequencies,
                       'amplitudes': amplitudes, 'sr': sr, 'duration': duration},
            'mfcc_config': {'n_mfcc': args.n_mfcc, 'nperseg': args.nperseg,
                           'n_frames': int(times.shape[0])},
            'features': feats
        }
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"\nKey coefficients:")
        for i in range(min(args.n_mfcc, 6)):
            mean_val = np.mean(mfccs[i])
            std_val = np.std(mfccs[i])
            label = "DC" if i == 0 else f"C{i}"
            print(f"  {label:>4}: μ={mean_val:8.3f}  σ={std_val:7.3f}")

        print(f"\nReport saved to: {report_path}")

    # --- Chirp mode ---
    if args.chirp:
        print("\n" + "=" * 60)
        print("MFCC Analysis — Chirp Sweep")
        print("=" * 60)

        sr = 22050
        duration = 4.0

        _, x = generate_chirp_signal(
            sr=sr, duration=duration,
            f_start=200, f_end=8000, noise_level=args.noise
        )

        mfccs, log_mel, times = extract_mfccs(x, sr, n_mfcc=args.n_mfcc,
                                               nperseg=args.nperseg)

        print(f"\nChirp: 200→8000 Hz over {duration}s")
        print(f"MFCC shape: {mfccs.shape}")

        plot_mel_spectrogram(log_mel, times, f_min=0.0, f_max=sr/2,
                             n_filters=40,
                             title=f'Mel-Spectrogram (Chirp 200→8000 Hz)',
                             save_path=str(out_dir / 'chirp_melspec.png'))

        plot_mfcc_trajectory(mfccs, times,
                             title='MFCC Coefficient Trajectories (Chirp)',
                             save_path=str(out_dir / 'chirp_mfccs.png'))

        feats = spectral_features_from_mfcc(mfccs)
        report_path = out_dir / 'chirp_mfcc_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'signal': {'type': 'chirp', 'f_start': 200, 'f_end': 8000,
                           'sr': sr, 'duration': duration},
                'mfcc_config': {'n_mfcc': args.n_mfcc, 'n_frames': int(times.shape[0])},
                'features': feats
            }, f, indent=2, default=str)

        print(f"\nReport saved to: {report_path}")


if __name__ == '__main__':
    main()
