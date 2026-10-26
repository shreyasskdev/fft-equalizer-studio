# config.py

DEFAULT_SAMPLE_RATE = 48000
FFT_SIZE = 1024
WINDOW_TYPE = 'hann'

# 6-Band Equalizer Center Frequencies (in Hz)
BAND_CENTERS = [60, 150, 400, 1000, 2500, 8000]
BAND_LABELS  = ["60Hz", "150Hz", "400Hz", "1kHz", "2.5kHz", "8kHz"]

# Default 6-band gains in % (0% = Mute, 100% = Flat/Unity, 200% = 2x Boost)
DEFAULT_GAINS_PCT = [175.0, 145.0, 70.0, 65.0, 145.0, 180.0]

# Equalizer Presets in % (60Hz, 150Hz, 400Hz, 1kHz, 2.5kHz, 8kHz)
EQ_PRESETS = {
    "Flat 100%":  [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
    "Bass Boost": [185.0, 160.0, 115.0, 100.0, 100.0, 100.0],
    "Treble":     [100.0, 100.0, 105.0, 125.0, 165.0, 190.0],
    "Vocal":      [35.0,  65.0,  145.0, 180.0, 150.0, 75.0],
    "V-Shape":    [175.0, 145.0, 70.0,  65.0,  145.0, 180.0],
    "Low-Pass":   [160.0, 140.0, 90.0,  20.0,  0.0,   0.0],
    "High-Pass":  [0.0,   0.0,   30.0,  110.0, 150.0, 165.0]
}
