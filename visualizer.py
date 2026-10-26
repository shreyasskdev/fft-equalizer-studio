# visualizer.py
import io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

class PlotImageProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.images = {}

    def requestImage(self, id_str, size, requestedSize):
        plot_type = id_str.split('?')[0]
        if plot_type in self.images:
            return self.images[plot_type]
        img = QImage(800, 500, QImage.Format.Format_RGBA8888)
        img.fill(0x1a203c)
        return img

    def update_plot(self, name, qimage):
        self.images[name] = qimage

def fig_to_qimage(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    img = QImage()
    img.loadFromData(buf.getvalue(), 'PNG')
    return img

def render_all_plots(provider, orig_sig, eq_sig, fs, bands, gains_db, fft_size, window_type):
    plt.style.use('dark_background')
    bg_color = '#161b33'

    # 1. Dashboard (2x2 Grid)
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.8), facecolor=bg_color)
    for ax in axes.flat:
        ax.set_facecolor('#1e2544')

    _draw_waveform(axes[0, 0], orig_sig, eq_sig, fs)
    _draw_spectrum(axes[0, 1], orig_sig, eq_sig, fs, bands)
    _draw_spectrogram(fig, axes[1, 0], eq_sig, fs, fft_size)
    _draw_gains(axes[1, 1], gains_db)
    fig.tight_layout(pad=2.0)
    provider.update_plot("dashboard", fig_to_qimage(fig))

    # 2. Individual High-Res Tabs
    for name, draw_fn in [
        ("waveform", lambda f, ax: _draw_waveform(ax, orig_sig, eq_sig, fs)),
        ("spectrum", lambda f, ax: _draw_spectrum(ax, orig_sig, eq_sig, fs, bands)),
        ("spectrogram", lambda f, ax: _draw_spectrogram(f, ax, eq_sig, fs, fft_size)),
        ("gains", lambda f, ax: _draw_gains(ax, gains_db))
    ]:
        f, ax = plt.subplots(figsize=(9, 5.2), facecolor=bg_color)
        ax.set_facecolor('#1e2544')
        draw_fn(f, ax)
        f.tight_layout()
        provider.update_plot(name, fig_to_qimage(f))

def _draw_waveform(ax, orig_sig, eq_sig, fs):
    t = np.arange(len(orig_sig)) / fs
    zoom = min(len(orig_sig), int(0.035 * fs))
    ax.plot(t[:zoom] * 1000, orig_sig[:zoom], label="Original", color="#4cc9f0", alpha=0.8, lw=1.5)
    ax.plot(t[:zoom] * 1000, eq_sig[:zoom], label="Equalized", color="#f72585", alpha=0.85, lw=1.5, ls="--")
    ax.set_title("Time-Domain Waveform (35 ms Slice)", fontsize=11, fontweight='bold', color='#e0e6ed')
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.2)

def _draw_spectrum(ax, orig_sig, eq_sig, fs, bands):
    N = len(orig_sig)
    freqs = np.fft.rfftfreq(N, d=1.0 / fs)
    orig_db = 20 * np.log10(np.abs(np.fft.rfft(orig_sig)) / N + 1e-12)
    eq_db = 20 * np.log10(np.abs(np.fft.rfft(eq_sig)) / N + 1e-12)

    ax.plot(freqs, orig_db, label="Original", color="#4cc9f0", alpha=0.65, lw=1.2)
    ax.plot(freqs, eq_db, label="Equalized", color="#f72585", alpha=0.8, lw=1.2)
    ax.set_xscale('log')
    ax.set_xlim(20, fs / 2)
    ax.set_ylim(-100, 5)
    ax.set_title("Magnitude Spectrum (Before vs. After)", fontsize=11, fontweight='bold', color='#e0e6ed')
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    for _, (f_low, f_high) in bands.items():
        ax.axvline(f_high, color='#64dfdf', linestyle=':', alpha=0.4)
    ax.legend(loc="upper right")
    ax.grid(True, which="both", alpha=0.2)

def _draw_spectrogram(fig, ax, eq_sig, fs, fft_size):
    Pxx, freqs, bins, im = ax.specgram(eq_sig, NFFT=fft_size, Fs=fs, noverlap=fft_size // 2, cmap='magma')
    ax.set_title("Equalized Signal Spectrogram", fontsize=11, fontweight='bold', color='#e0e6ed')
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_ylim(0, 10000)
    fig.colorbar(im, ax=ax, label="dB")

def _draw_gains(ax, gains_db):
    names = list(gains_db.keys())
    vals = [gains_db[k] for k in names]
    colors = ['#4cc9f0' if v >= 0 else '#f72585' for v in vals]
    bars = ax.bar(names, vals, color=colors, width=0.45, edgecolor='white')
    ax.axhline(0, color='white', lw=0.8)
    ax.set_ylim(-14, 14)
    ax.set_title("Applied Band Gains (dB)", fontsize=11, fontweight='bold', color='#e0e6ed')
    ax.set_ylabel("Gain (dB)")
    ax.grid(True, axis='y', alpha=0.2)
    for bar, v in zip(bars, vals):
        y = v + (0.6 if v >= 0 else -1.4)
        ax.text(bar.get_x() + bar.get_width() / 2, y, f"{v:+.1f} dB", ha='center', fontweight='bold', color='white')
