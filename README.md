# 🎛️ FFT Equalizer Studio

A desktop parametric audio equalizer and real-time STFT signal visualizer built with **Python**, **NumPy/SciPy**, and **Qt 6 (QML)**.

It processes audio in the frequency domain using Short-Time Fourier Transform (STFT), applies a smooth 6-band monotonic cubic spline filter (`PCHIP`), and reconstructs the time-domain waveform via Inverse FFT with 50% Overlap-Add (OLA).

---

## 📸 Screenshot

<!-- Paste your screenshot right below this line on GitHub (Ctrl+V) -->
<img width="1250" height="740" alt="image" src="https://github.com/user-attachments/assets/d3b26af6-5733-47e6-ad02-f54f48d944eb" />



---

## ✨ Features

- **6-Band Parametric Spline Equalizer (`60Hz`, `150Hz`, `400Hz`, `1kHz`, `2.5kHz`, `8kHz`):**
  - Interactive node-based curve editor with monotonic cubic spline interpolation in log-frequency space (`0%` mute to `200%` boost) for smooth filtering without harsh band-edge artifacts.
- **Built-In Presets:**
  - *Flat (100%)*, *Bass Boost*, *Treble*, *Vocal*, *V-Shape*, *Low-Pass*, and *High-Pass*.
- **Live STFT Frame & 50% Overlap-Add Visualizer:**
  - Displays a smooth 60+ FPS hardware-accelerated playhead alongside the quantized discrete STFT sample window (`Hop = N/2`), showing exact frame boundaries and 50% overlap in real time.
- **Configurable DSP Engine:**
  - **Window Functions:** `Hann`, `Hamming`, and `Rectangular`
  - **FFT Frame Sizes ($N$):** `512`, `1024`, and `2048` samples
- **Live Microphone Capture & WAV I/O:**
  - Real-time microphone recording and live waveform plotting (PipeWire / PulseAudio / PortAudio), persistent input device selection, `.wav` import/export, and independent timeline zoom (`1x` to `64x`).

---

## 🛠️ Signal Processing Pipeline

```text
Audio Input (.wav / Mic)
   │
   ▼
Framing + Windowing (w[n] · x[n], 50% Overlap Hop = N/2)
   │
   ▼
Fast Fourier Transform (RFFT: Time ──► Frequency Domain)
   │
   ▼
6-Band Cubic Spline Gain Multiplication (H[k] · X[k])
   │
   ▼
Inverse FFT (IRFFT: Frequency ──► Time Domain) + Overlap-Add
   │
   ▼
Equalized Output Signal y[n]
```

---

## 📂 Project Structure

```text
├── main.py          # Qt 6 QML application entry point
├── ui.qml           # GPU-accelerated QtQuick / QML interface
├── backend.py       # Qt QObject bridge, 60 FPS playback clock, zoom & STFT frame quantization
├── equalizer.py     # Core DSP: Windowing, RFFT, PCHIP spline gain mask, IRFFT, Overlap-Add
├── audio_utils.py   # WAV I/O, synthetic test wave generator, PipeWire/ALSA mic & playback
├── config.py        # Frequency bands, default parameters, and equalizer presets
└── exports/         # Recorded & exported .wav audio files
```

---

## 🚀 Installation & Usage

### Arch Linux
```bash
sudo pacman -S pyside6 qt6-declarative qt6-multimedia python-numpy python-scipy portaudio ffmpeg
paru -S python-sounddevice
```

### Other Linux / Windows / macOS
```bash
pip install PySide6 numpy scipy sounddevice
```

### Run
```bash
python main.py
```
