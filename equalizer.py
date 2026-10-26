# equalizer.py
import numpy as np
from scipy.interpolate import PchipInterpolator


def pct_to_linear(pct):
    """0% -> 0.0 (silence), 100% -> 1.0 (original), 200% -> 2.0 (2x boost)."""
    return np.clip(np.asarray(pct, dtype=np.float64) / 100.0, 0.0, 2.0)


def get_window(window_type, N):
    w = window_type.lower()
    if w == 'hann':
        return np.hanning(N)
    elif w == 'hamming':
        return np.hamming(N)
    elif w == 'rectangular':
        return np.ones(N)
    return np.hanning(N)


def build_smooth_gain_curve(fs, fft_size, band_centers, gains_pct):
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / fs)
    anchor_freqs = [1.0] + list(band_centers) + [fs / 2.0]
    anchor_gains = [gains_pct[0]] + list(gains_pct) + [gains_pct[-1]]

    log_anchors = np.log10(np.maximum(anchor_freqs, 1.0))
    log_freqs = np.log10(np.maximum(freqs, 1.0))

    interpolator = PchipInterpolator(log_anchors, anchor_gains)
    smooth_pct = interpolator(log_freqs)
    gain_mask = pct_to_linear(smooth_pct)

    return freqs, smooth_pct, gain_mask


def apply_fft_equalizer(signal, fs, fft_size, hop_size, window_type, band_centers, gains_pct):
    window = get_window(window_type, fft_size)
    _, _, gain_mask = build_smooth_gain_curve(fs, fft_size, band_centers, gains_pct)

    pad_length = fft_size
    padded_signal = np.pad(signal, (pad_length, pad_length), mode='constant')

    output_signal = np.zeros_like(padded_signal)
    window_sum = np.zeros_like(padded_signal)

    num_frames = (len(padded_signal) - fft_size) // hop_size + 1

    for i in range(num_frames):
        start = i * hop_size
        end = start + fft_size

        frame = padded_signal[start:end] * window
        spectrum = np.fft.rfft(frame)
        modified_spectrum = spectrum * gain_mask
        reconstructed_frame = np.fft.irfft(modified_spectrum, n=fft_size)

        output_signal[start:end] += reconstructed_frame * window
        window_sum[start:end] += window ** 2

    non_zero = window_sum > 1e-8
    output_signal[non_zero] /= window_sum[non_zero]

    equalized_signal = output_signal[pad_length : pad_length + len(signal)]
    return np.clip(equalized_signal, -1.0, 1.0)
