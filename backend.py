# backend.py
import os
import json
import time
from urllib.parse import unquote
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Slot, Signal, Property, QTimer

import config
from audio_utils import (
    EXPORTS_DIR, generate_test_signal, load_wav, save_wav,
    get_input_devices, start_native_playback, stop_native_playback,
    start_pipewire_raw_recording, read_live_pipewire_samples, stop_pipewire_raw_recording
)
from equalizer import apply_fft_equalizer, get_window

PREFS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_prefs.json")


class EqualizerBackend(QObject):
    inputWaveUpdated = Signal()
    eqWaveUpdated = Signal()
    inputCursorChanged = Signal()
    eqCursorChanged = Signal()
    windowFrameUpdated = Signal()
    playbackStateChanged = Signal()
    statusChanged = Signal()
    recordingChanged = Signal()

    def __init__(self):
        super().__init__()
        self.fs, self.orig_signal = generate_test_signal(duration=3.0, fs=config.DEFAULT_SAMPLE_RATE)
        self.eq_signal = self.orig_signal.copy()

        self._active_preset = "V-Shape"
        self.gains_pct = list(config.EQ_PRESETS.get(self._active_preset, config.DEFAULT_GAINS_PCT))
        self.fft_size = config.FFT_SIZE
        self.window_type = config.WINDOW_TYPE

        self._input_cursor = 0.0
        self._eq_cursor = 0.0

        self._current_frame_idx = -1
        self._frame_start_sample = 0
        self._box_start_in_view = 0.0

        self._input_zoom = 1.0
        self._input_view_start = 0.0
        self._input_view_end = 1.0

        self._eq_zoom = 1.0
        self._eq_view_start = 0.0
        self._eq_view_end = 1.0

        self._active_player = "none"
        self._play_wall_start = 0.0
        self._play_offset_norm = 0.0
        self._play_timer = QTimer(self)
        self._play_timer.setInterval(15)
        self._play_timer.timeout.connect(self._on_playback_frame)

        # Load Microphone Devices & Restore Last Saved Mic Preference
        self.input_devices, self.selected_mic_idx = get_input_devices()
        self._load_mic_preference()

        self._is_recording = False
        self._rec_stream = None
        self._rec_chunks = []
        self._rec_fs = 48000
        self._using_pipewire_rec = True

        self._live_rec_timer = QTimer(self)
        self._live_rec_timer.setInterval(45)
        self._live_rec_timer.timeout.connect(self._on_live_recording_tick)

        active_mic_label = self.input_devices[self.selected_mic_idx][1] if self.input_devices else "Default"
        self._status = f"Ready — True 1:1 STFT Frame Box (Zoom in to inspect individual N-sample frames)  •  Mic: {active_mic_label}"
        self._input_pts = []
        self._window_pts = []
        self._windowed_frame_pts = []
        self._eq_pts = []

        self.process_and_update()

    # ================= PERSISTENT MIC PREFERENCE =================
    def _load_mic_preference(self):
        if not os.path.exists(PREFS_FILE):
            return
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            saved_label = prefs.get("selected_mic_label", "")
            saved_idx = prefs.get("selected_mic_idx", 0)

            for i, (_, label, _) in enumerate(self.input_devices):
                if label == saved_label:
                    self.selected_mic_idx = i
                    return

            if 0 <= saved_idx < len(self.input_devices):
                self.selected_mic_idx = saved_idx
        except Exception:
            pass

    def _save_mic_preference(self):
        if not (0 <= self.selected_mic_idx < len(self.input_devices)):
            return
        try:
            prefs = {
                "selected_mic_idx": self.selected_mic_idx,
                "selected_mic_label": self.input_devices[self.selected_mic_idx][1]
            }
            with open(PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(prefs, f, indent=2)
        except Exception:
            pass

    # ================= QML PROPERTIES =================
    @Property(str, notify=statusChanged)
    def statusText(self):
        return self._status

    @Property(bool, notify=recordingChanged)
    def isRecording(self):
        return self._is_recording

    @Property(str, notify=playbackStateChanged)
    def activePlayer(self):
        return self._active_player

    @Property('QVariantList', constant=True)
    def presetNames(self):
        return list(config.EQ_PRESETS.keys())

    @Property(str, notify=eqWaveUpdated)
    def activePreset(self):
        return self._active_preset

    @Property(float, notify=inputCursorChanged)
    def inputCursorInView(self):
        span = max(1e-6, self._input_view_end - self._input_view_start)
        return max(0.0, min(1.0, (self._input_cursor - self._input_view_start) / span))

    @Property(float, notify=eqCursorChanged)
    def eqCursorInView(self):
        span = max(1e-6, self._eq_view_end - self._eq_view_start)
        return max(0.0, min(1.0, (self._eq_cursor - self._eq_view_start) / span))

    @Property(float, notify=windowFrameUpdated)
    def windowBoxWidthInView(self):
        """
        TRUE 1:1 mathematical width of N = self.fft_size samples relative to the current view!
        No artificial scaling: N=512 is exactly 512/total, N=1024 is 1024/total, N=2048 is 2048/total.
        """
        total = max(1, len(self.orig_signal))
        true_ratio = self.fft_size / float(total)
        span = max(1e-6, self._input_view_end - self._input_view_start)
        return max(0.002, min(1.0, true_ratio / span))

    @Property(float, notify=windowFrameUpdated)
    def windowBoxStartInView(self):
        return self._box_start_in_view

    @Property(float, notify=inputWaveUpdated)
    def inputZoomLevel(self):
        return self._input_zoom

    @Property(float, notify=eqWaveUpdated)
    def eqZoomLevel(self):
        return self._eq_zoom

    @Property(str, notify=inputCursorChanged)
    def inputTimeReadout(self):
        dur = len(self.orig_signal) / max(1, self.fs)
        cur = self._input_cursor * dur
        return f"{cur:.2f}s / {dur:.2f}s"

    @Property(str, notify=eqCursorChanged)
    def eqTimeReadout(self):
        dur = len(self.eq_signal) / max(1, self.fs)
        cur = self._eq_cursor * dur
        return f"{cur:.2f}s / {dur:.2f}s"

    @Property(str, notify=windowFrameUpdated)
    def currentSampleRangeText(self):
        total = len(self.orig_signal)
        start_idx = self._frame_start_sample
        end_idx = min(total, start_idx + self.fft_size)
        hop = self.fft_size // 2
        return f"Frame #{max(0, self._current_frame_idx)} (Hop={hop})  •  Samples [{start_idx} .. {end_idx}]"

    @Property('QVariantList', constant=True)
    def micDeviceLabels(self):
        return [item[1] for item in self.input_devices]

    @Property(int, constant=True)
    def defaultMicIndex(self):
        return self.selected_mic_idx

    @Property('QVariantList', notify=inputWaveUpdated)
    def inputWavePoints(self):
        return self._input_pts

    @Property('QVariantList', notify=windowFrameUpdated)
    def windowCurvePoints(self):
        return self._window_pts

    @Property('QVariantList', notify=windowFrameUpdated)
    def windowedFramePoints(self):
        return self._windowed_frame_pts

    @Property('QVariantList', notify=eqWaveUpdated)
    def equalizedWavePoints(self):
        return self._eq_pts

    @Property('QVariantList', constant=True)
    def bandLabels(self):
        return config.BAND_LABELS

    @Property('QVariantList', notify=eqWaveUpdated)
    def bandGains(self):
        return self.gains_pct

    def set_status(self, msg):
        self._status = msg
        self.statusChanged.emit()

    # ================= ZOOM & VIEWPORT SLICING =================
    def _compute_view_bounds(self, center_norm, zoom):
        span = 1.0 / max(1.0, zoom)
        half = span / 2.0
        start = center_norm - half
        end = center_norm + half
        if start < 0.0:
            end -= start
            start = 0.0
        if end > 1.0:
            start -= (end - 1.0)
            end = 1.0
        return max(0.0, start), min(1.0, end)

    def _rebuild_input_wave_points(self):
        total = len(self.orig_signal)
        if total == 0:
            return
        self._input_view_start, self._input_view_end = self._compute_view_bounds(self._input_cursor, self._input_zoom)
        s_idx = int(self._input_view_start * (total - 1))
        e_idx = max(s_idx + 2, int(self._input_view_end * total))
        num_pts = min(600, e_idx - s_idx)
        idx = np.linspace(s_idx, e_idx - 1, num_pts, dtype=int)
        self._input_pts = self.orig_signal[idx].tolist()
        self.inputWaveUpdated.emit()
        self.inputCursorChanged.emit()
        self._update_live_window_frame(force=True)

    def _rebuild_eq_wave_points(self):
        total = len(self.eq_signal)
        if total == 0:
            return
        self._eq_view_start, self._eq_view_end = self._compute_view_bounds(self._eq_cursor, self._eq_zoom)
        s_idx = int(self._eq_view_start * (total - 1))
        e_idx = max(s_idx + 2, int(self._eq_view_end * total))
        num_pts = min(600, e_idx - s_idx)
        idx = np.linspace(s_idx, e_idx - 1, num_pts, dtype=int)
        self._eq_pts = self.eq_signal[idx].tolist()
        self.eqWaveUpdated.emit()
        self.eqCursorChanged.emit()

    @Slot(float)
    def zoomInput(self, factor):
        self._input_zoom = max(1.0, min(64.0, round(self._input_zoom * factor, 2)))
        self._rebuild_input_wave_points()

    @Slot()
    def resetInputZoom(self):
        self._input_zoom = 1.0
        self._rebuild_input_wave_points()

    @Slot(float)
    def zoomEq(self, factor):
        self._eq_zoom = max(1.0, min(64.0, round(self._eq_zoom * factor, 2)))
        self._rebuild_eq_wave_points()

    @Slot()
    def resetEqZoom(self):
        self._eq_zoom = 1.0
        self._rebuild_eq_wave_points()

    # ================= INDEPENDENT GRAPH SCRUBBING =================
    @Slot(float)
    def seekInputInView(self, view_norm):
        view_norm = max(0.0, min(1.0, float(view_norm)))
        self._input_cursor = self._input_view_start + view_norm * (self._input_view_end - self._input_view_start)
        self.inputCursorChanged.emit()
        self._update_live_window_frame(force=False)

        if self._active_player == "input":
            self._start_playback("input", from_norm=self._input_cursor)

    @Slot(float)
    def seekEqInView(self, view_norm):
        view_norm = max(0.0, min(1.0, float(view_norm)))
        self._eq_cursor = self._eq_view_start + view_norm * (self._eq_view_end - self._eq_view_start)
        self.eqCursorChanged.emit()

        if self._active_player == "equalized":
            self._start_playback("equalized", from_norm=self._eq_cursor)

    def _update_live_window_frame(self, force=False):
        """
        100% TRUE 1:1 STFT Frame Quantization:
        - Current sample = int(self._input_cursor * total_samples)
        - Frame index k  = current_sample // hop_size   (where hop_size = fft_size // 2)
        - Frame start    = k * hop_size
        - Frame end      = k * hop_size + fft_size
        """
        total = len(self.orig_signal)
        if total == 0:
            return

        hop_samples = max(1, self.fft_size // 2)
        cur_sample = int(self._input_cursor * total)

        # True STFT frame index k (0, 1, 2, 3...)
        max_start = max(0, total - self.fft_size)
        true_frame_idx = cur_sample // hop_samples
        quantized_sample = min(max_start, true_frame_idx * hop_samples)
        true_frame_idx = quantized_sample // hop_samples

        # Convert true quantized sample start into viewport normalized coordinates [0.0 .. 1.0]
        global_norm_start = quantized_sample / float(max(1, total))
        span = max(1e-6, self._input_view_end - self._input_view_start)
        quantized_view_start = max(0.0, min(1.0, (global_norm_start - self._input_view_start) / span))

        if not force and true_frame_idx == self._current_frame_idx and abs(quantized_view_start - self._box_start_in_view) < 1e-6:
            return

        self._box_start_in_view = quantized_view_start
        self._current_frame_idx = true_frame_idx
        self._frame_start_sample = quantized_sample

        frame_slice = self.orig_signal[quantized_sample : quantized_sample + self.fft_size]
        if len(frame_slice) < self.fft_size:
            frame_slice = np.pad(frame_slice, (0, self.fft_size - len(frame_slice)))

        win = get_window(self.window_type, self.fft_size)
        windowed_frame = frame_slice * win

        # Power-of-2 stride (512 points) so the right half [N/2..N] of Frame #k
        # and the left half [0..N/2] of Frame #(k+1) hit the exact same samples!
        num_pts = 512
        step = max(1, self.fft_size // num_pts)
        win_idx = np.arange(0, self.fft_size, step, dtype=int)
        self._window_pts = win[win_idx].tolist()
        self._windowed_frame_pts = windowed_frame[win_idx].tolist()
        self.windowFrameUpdated.emit()

    # ================= DSP & PRESET PROCESSING =================
    @Slot(int)
    def setMicDevice(self, combo_idx):
        if 0 <= combo_idx < len(self.input_devices):
            self.selected_mic_idx = combo_idx
            self._save_mic_preference()
            self.set_status(f"Saved Mic Preference: {self.input_devices[combo_idx][1]}")

    @Slot(int, float)
    def setBandGain(self, index, value_pct):
        if 0 <= index < len(self.gains_pct):
            clamped = max(0.0, min(200.0, float(value_pct)))
            self.gains_pct[index] = round(clamped, 0)
            self._active_preset = "Custom"
            self.process_and_update()

    @Slot(str)
    def applyPreset(self, preset_name):
        if preset_name in config.EQ_PRESETS:
            self._active_preset = preset_name
            self.gains_pct = list(config.EQ_PRESETS[preset_name])
            self.set_status(f"Preset Applied: {preset_name}  •  Gains = {[int(x) for x in self.gains_pct]}%")
            self.process_and_update()

    @Slot(int, str)
    def setDspParams(self, fft_size, window_type):
        self.fft_size = int(fft_size)
        self.window_type = window_type.lower()
        self.set_status(f"Updated DSP Parameters: Window = {window_type}, FFT Frame Size = {fft_size} samples")
        self.process_and_update()

    @Slot()
    def resetGains(self):
        self.applyPreset("Flat 100%")

    def process_and_update(self):
        hop_size = self.fft_size // 2
        self.eq_signal = apply_fft_equalizer(
            signal=self.orig_signal,
            fs=self.fs,
            fft_size=self.fft_size,
            hop_size=hop_size,
            window_type=self.window_type,
            band_centers=config.BAND_CENTERS,
            gains_pct=self.gains_pct
        )
        self._rebuild_input_wave_points()
        self._rebuild_eq_wave_points()
        self._update_live_window_frame(force=True)

    # ================= SMOOTH 60+ FPS PLAYBACK ENGINE =================
    @Slot(str)
    def togglePlay(self, which):
        if self._active_player == which:
            self.stopPlayback()
            return

        cur = self._input_cursor if which == "input" else self._eq_cursor
        if cur >= 0.98:
            cur = 0.0
        self._start_playback(which, from_norm=cur)

    def _start_playback(self, which, from_norm=0.0):
        self.stopPlayback(silent=True)
        sig = self.orig_signal if which == "input" else self.eq_signal
        total = len(sig)
        if total == 0:
            return

        start_sample = int(from_norm * total)
        sliced = sig[start_sample:]
        if len(sliced) < 128:
            sliced = sig
            from_norm = 0.0

        self._active_player = which
        self._play_offset_norm = from_norm
        self._play_wall_start = time.perf_counter()
        self.playbackStateChanged.emit()

        start_native_playback(self.fs, sliced)
        self._play_timer.start()

        label = "Input Signal x[n]" if which == "input" else "Equalized Output y[n]"
        self.set_status(f"Playing {label}...")

    def _on_playback_frame(self):
        dur = len(self.orig_signal) / max(1, self.fs)
        if dur <= 0:
            return
        elapsed = time.perf_counter() - self._play_wall_start
        norm = self._play_offset_norm + (elapsed / dur)

        if norm >= 1.0:
            norm = 1.0
            if self._active_player == "input":
                self._input_cursor = 1.0
                self.inputCursorChanged.emit()
                self._update_live_window_frame(force=True)
            elif self._active_player == "equalized":
                self._eq_cursor = 1.0
                self.eqCursorChanged.emit()
            self.stopPlayback(silent=True)
            self.set_status("Playback finished")
            return

        if self._active_player == "input":
            self._input_cursor = norm
            if self._input_zoom > 1.0 and (norm < self._input_view_start or norm > self._input_view_end):
                self._rebuild_input_wave_points()
            else:
                self.inputCursorChanged.emit()
            self._update_live_window_frame(force=False)
        elif self._active_player == "equalized":
            self._eq_cursor = norm
            if self._eq_zoom > 1.0 and (norm < self._eq_view_start or norm > self._eq_view_end):
                self._rebuild_eq_wave_points()
            else:
                self.eqCursorChanged.emit()

    @Slot()
    def stopPlayback(self, silent=False):
        self._play_timer.stop()
        stop_native_playback()
        if self._active_player != "none":
            self._active_player = "none"
            self.playbackStateChanged.emit()
        if not silent:
            self.set_status("Playback paused")

    # ================= REAL-TIME RECORDING =================
    @Slot()
    def toggleRecording(self):
        if not self._is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.stopPlayback(silent=True)
        dev_id, dev_label, dev_fs = self.input_devices[self.selected_mic_idx]

        try:
            if dev_id == -1 or any(k in dev_label.lower() for k in ["pipewire", "pulse", "default"]):
                start_pipewire_raw_recording()
                self._using_pipewire_rec = True
                self._rec_fs = 48000
            else:
                self._using_pipewire_rec = False
                self._rec_chunks = []
                self._rec_fs = dev_fs

                def audio_callback(indata, frames, time_info, status):
                    self._rec_chunks.append(indata[:, 0].copy())

                self._rec_stream = sd.InputStream(
                    samplerate=self._rec_fs,
                    device=dev_id,
                    channels=1,
                    dtype='float32',
                    callback=audio_callback
                )
                self._rec_stream.start()

            self._is_recording = True
            self._input_zoom = 1.0
            self.recordingChanged.emit()
            self._live_rec_timer.start()
            self.set_status(f"Recording Live [{dev_label}] — Speak now!")
        except Exception as e:
            self._is_recording = False
            self.recordingChanged.emit()
            self.set_status(f"Mic Error: {e}")

    def _on_live_recording_tick(self):
        if not self._is_recording:
            return

        if self._using_pipewire_rec:
            live_sig = read_live_pipewire_samples()
        else:
            if not self._rec_chunks:
                return
            live_sig = np.concatenate(self._rec_chunks, axis=0)

        if len(live_sig) < 128:
            return

        peak = float(np.max(np.abs(live_sig)))
        display_sig = (live_sig / max(peak, 0.05)) * 0.85

        self.fs = self._rec_fs
        self.orig_signal = display_sig
        self._input_cursor = max(0.0, 1.0 - (self.fft_size / max(1, len(display_sig))))

        self._rebuild_input_wave_points()
        self._update_live_window_frame(force=True)

    def _stop_recording(self):
        self._live_rec_timer.stop()
        self._is_recording = False
        self.recordingChanged.emit()

        try:
            if self._using_pipewire_rec:
                fs, sig = stop_pipewire_raw_recording()
            else:
                if self._rec_stream is not None:
                    self._rec_stream.stop()
                    self._rec_stream.close()
                    self._rec_stream = None
                if not self._rec_chunks:
                    self.set_status("Recording stopped (no audio data captured).")
                    return
                rec_signal = np.concatenate(self._rec_chunks, axis=0)
                peak = float(np.max(np.abs(rec_signal)))
                if peak > 1e-4:
                    rec_signal = (rec_signal / peak) * 0.90
                fs, sig = self._rec_fs, rec_signal.astype(np.float32)

            self.fs = fs
            self.orig_signal = sig
            out_path = save_wav("recorded_input.wav", self.fs, self.orig_signal)
            dur = len(self.orig_signal) / self.fs
            self._input_cursor = 0.0
            self._eq_cursor = 0.0
            self.set_status(f"Recorded {dur:.1f}s — Saved to {out_path}")
            self.process_and_update()
        except Exception as e:
            self.set_status(f"Recording Error: {e}")

    @Slot(str)
    def importWavFile(self, file_url):
        self.stopPlayback(silent=True)
        path = unquote(file_url.replace("file://", ""))
        try:
            self.fs, self.orig_signal = load_wav(path)
            self._input_zoom = 1.0
            self._eq_zoom = 1.0
            self._input_cursor = 0.0
            self._eq_cursor = 0.0
            self.set_status(f"Imported {path.split('/')[-1]} ({self.fs} Hz)")
            self.process_and_update()
        except Exception as e:
            self.set_status(f"Import Error: {e}")

    @Slot()
    def loadSyntheticSignal(self):
        self.stopPlayback(silent=True)
        self.fs, self.orig_signal = generate_test_signal(duration=3.0, fs=config.DEFAULT_SAMPLE_RATE)
        self._input_zoom = 1.0
        self._eq_zoom = 1.0
        self._input_cursor = 0.0
        self._eq_cursor = 0.0
        self.set_status("Loaded Synthetic 6-Band Multi-Tone Test Signal")
        self.process_and_update()

    @Slot()
    def exportEqualizedWav(self):
        out_path = save_wav("output_equalized.wav", self.fs, self.eq_signal)
        self.set_status(f"Exported Equalized WAV to: {out_path}")
