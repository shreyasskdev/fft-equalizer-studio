# audio_utils.py
import os
import shutil
import subprocess
import tempfile
import numpy as np
from scipy.io import wavfile
import sounddevice as sd

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
os.makedirs(EXPORTS_DIR, exist_ok=True)

_record_proc = None
_play_proc = None
_temp_raw_path = os.path.join(tempfile.gettempdir(), "dsp_eq_live_capture.pcm")
_temp_play_wav = os.path.join(tempfile.gettempdir(), "dsp_eq_active_play.wav")

def generate_test_signal(duration=3.0, fs=48000):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    env1 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.8 * t)
    env2 = 0.5 + 0.5 * np.cos(2 * np.pi * 1.5 * t)
    sig = (
        0.35 * env1 * np.sin(2 * np.pi * 60 * t) +
        0.30 * env2 * np.sin(2 * np.pi * 150 * t) +
        0.25 * env1 * np.sin(2 * np.pi * 400 * t) +
        0.25 * env2 * np.sin(2 * np.pi * 1000 * t) +
        0.20 * env1 * np.sin(2 * np.pi * 2500 * t) +
        0.15 * env2 * np.sin(2 * np.pi * 8000 * t)
    )
    sig = sig / np.max(np.abs(sig)) * 0.85
    return fs, sig.astype(np.float32)

def get_input_devices():
    input_list = [(-1, "Default Mic (PipeWire / Pulse)", 48000)]
    try:
        devices = sd.query_devices()
        for idx, d in enumerate(devices):
            if d.get('max_input_channels', 0) > 0:
                name = d['name']
                sr = int(d.get('default_samplerate', 48000))
                input_list.append((idx, f"{idx}: {name}", sr))
    except Exception:
        pass
    return input_list, 0

def load_wav(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    fs, data = wavfile.read(filepath)
    if data.ndim > 1:
        data = np.mean(data, axis=1)
    if np.issubdtype(data.dtype, np.integer):
        max_val = np.iinfo(data.dtype).max
        data = data.astype(np.float32) / max_val
    else:
        data = data.astype(np.float32)
    peak = float(np.max(np.abs(data))) if len(data) > 0 else 0.0
    if 1e-5 < peak < 0.25:
        data = (data / peak) * 0.85
    return int(fs), data

def save_wav(filename_or_path, fs, data, stereo=False):
    """Saves WAV file inside exports/ unless an absolute path is given."""
    if not os.path.isabs(filename_or_path):
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        filepath = os.path.join(EXPORTS_DIR, filename_or_path)
    else:
        filepath = filename_or_path

    clipped = np.clip(data, -1.0, 1.0)
    int_data = (clipped * 32767).astype(np.int16)
    if stereo and int_data.ndim == 1:
        int_data = np.column_stack((int_data, int_data))
    wavfile.write(filepath, int(fs), int_data)
    return filepath

def start_native_playback(fs, mono_slice):
    """
    Writes a 2-channel stereo WAV slice and plays it via PipeWire / PulseAudio / FFmpeg.
    Stereo ensures hardware sinks that reject mono streams always play sound.
    """
    global _play_proc
    stop_native_playback()
    save_wav(_temp_play_wav, fs, mono_slice, stereo=True)

    if shutil.which("pw-play"):
        _play_proc = subprocess.Popen(["pw-play", _temp_play_wav])
    elif shutil.which("paplay"):
        _play_proc = subprocess.Popen(["paplay", _temp_play_wav])
    elif shutil.which("ffplay"):
        _play_proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", _temp_play_wav]
        )
    elif shutil.which("aplay"):
        _play_proc = subprocess.Popen(["aplay", "-q", _temp_play_wav])
    else:
        stereo_float = np.column_stack((mono_slice, mono_slice))
        sd.play(stereo_float, int(fs))

def stop_native_playback():
    global _play_proc
    if _play_proc is not None:
        if _play_proc.poll() is None:
            _play_proc.terminate()
            try:
                _play_proc.wait(timeout=0.3)
            except subprocess.TimeoutExpired:
                _play_proc.kill()
        _play_proc = None
    try:
        sd.stop()
    except Exception:
        pass

def start_pipewire_raw_recording():
    global _record_proc
    if os.path.exists(_temp_raw_path):
        os.remove(_temp_raw_path)

    if shutil.which("parecord"):
        _record_proc = subprocess.Popen(
            ["parecord", "--raw", "--rate=48000", "--channels=1", "--format=s16le", "--latency-msec=20", _temp_raw_path]
        )
    elif shutil.which("pw-record"):
        _record_proc = subprocess.Popen(
            ["pw-record", "--rate=48000", "--channels=1", "--format=s16", _temp_raw_path]
        )
    else:
        raise RuntimeError("Neither parecord nor pw-record found on system.")

def read_live_pipewire_samples():
    if not os.path.exists(_temp_raw_path):
        return np.zeros(0, dtype=np.float32)
    try:
        raw_bytes = open(_temp_raw_path, "rb").read()
        if len(raw_bytes) > 44 and raw_bytes[:4] == b"RIFF":
            raw_bytes = raw_bytes[44:]
        n_samples = len(raw_bytes) // 2
        if n_samples == 0:
            return np.zeros(0, dtype=np.float32)
        pcm16 = np.frombuffer(raw_bytes[:n_samples * 2], dtype=np.int16)
        return (pcm16.astype(np.float32) / 32768.0)
    except Exception:
        return np.zeros(0, dtype=np.float32)

def stop_pipewire_raw_recording():
    global _record_proc
    if _record_proc is not None:
        if _record_proc.poll() is None:
            _record_proc.terminate()
            try:
                _record_proc.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                _record_proc.kill()
        _record_proc = None

    data = read_live_pipewire_samples()
    if len(data) < 100:
        raise RuntimeError("No audio captured from microphone.")

    peak = float(np.max(np.abs(data)))
    if peak > 1e-4:
        data = (data / peak) * 0.90
    return 48000, data
