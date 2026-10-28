import os
import math
import ctypes
import threading
from concurrent.futures import ThreadPoolExecutor
import av
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from src.C.native_bridge import get_native_engine

class AudioNormalizer(QObject):
    gain_ready = pyqtSignal(str, float)

    def __init__(self, target_base_db: float = -18.0):
        super().__init__()
        self.target_db = target_base_db
        self.gain_cache = {}
        self._analyzing = set()
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=2)
        self.c_engine = get_native_engine()

    def _measure_track_stats(self, filepath: str) -> tuple[float, float]:
        with av.open(filepath) as container:
            audio_streams = [s for s in container.streams if s.type == 'audio']
            if not audio_streams:
                return -24.0, 1.0

            stream = audio_streams[0]
            rate = stream.rate or 44100
            dur = float(container.duration / 1000000.0) if container.duration else 0.0

            if dur > 20.0:
                seek_pos = max(5.0, dur * 0.30)
                try:
                    container.seek(int(seek_pos * 1000000))
                except Exception:
                    pass

            window_samples = int(rate * 0.40)
            buffer = []
            buf_len = 0
            block_powers = []
            max_peak = 1e-4
            collected_sec = 0.0

            for frame in container.decode(stream):
                arr = frame.to_ndarray()
                if np.issubdtype(arr.dtype, np.integer):
                    data = arr.astype(np.float32) / np.iinfo(arr.dtype).max
                else:
                    data = arr.astype(np.float32)

                cur_peak = float(np.max(np.abs(data)))
                if cur_peak > max_peak:
                    max_peak = cur_peak

                flat_data = data.ravel()
                buffer.append(flat_data)
                buf_len += flat_data.size
                collected_sec += frame.samples / rate

                channels = data.shape[0] if data.ndim > 1 else 1
                target_block_size = window_samples * channels

                while buf_len >= target_block_size:
                    merged = np.concatenate(buffer)
                    block = merged[:target_block_size]
                    rem = merged[target_block_size:]
                    buffer = [rem] if rem.size > 0 else []
                    buf_len = rem.size

                    block_ptr = block.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                    block_db = self.c_engine.c_calculate_frame_db(block_ptr, block.size)
                    
                    if block_db > -70.0:
                        block_powers.append(10.0 ** (block_db / 10.0))

                if collected_sec >= 12.0:
                    break

            if not block_powers:
                return -24.0, max_peak

            powers = np.array(block_powers, dtype=np.float32)

            avg_p = np.mean(powers)
            relative_gate = avg_p * 0.10
            gated_powers = powers[powers >= relative_gate]

            if len(gated_powers) == 0:
                gated_powers = powers

            final_power = float(np.mean(gated_powers))
            if final_power <= 1e-9:
                return -24.0, max_peak

            loudness_db = float(10.0 * np.log10(final_power))
            return loudness_db, max_peak

    def analyze_track_gain(self, filepath: str):
        if not filepath or not os.path.exists(filepath):
            return

        with self._lock:
            if filepath in self.gain_cache:
                self.gain_ready.emit(filepath, self.gain_cache[filepath])
                return
            if filepath in self._analyzing:
                return
            self._analyzing.add(filepath)

        def run():
            gain = 1.0
            try:
                base_db, peak = self._measure_track_stats(filepath)
                diff_db = self.target_db - base_db
                
                raw_gain = math.pow(10.0, diff_db / 20.0)

                gain = max(0.10, min(6.0, raw_gain))

                if peak > 0.001:
                    max_safe_gain = 0.95 / peak
                    if gain > max_safe_gain:
                        gain = max_safe_gain

                gain = max(0.10, gain)

            except Exception:
                gain = 1.0

            with self._lock:
                self.gain_cache[filepath] = gain
                self._analyzing.discard(filepath)

            self.gain_ready.emit(filepath, gain)

        self._pool.submit(run)