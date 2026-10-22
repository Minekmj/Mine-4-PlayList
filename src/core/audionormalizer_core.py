import os
import math
import threading
from concurrent.futures import ThreadPoolExecutor
import av
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

class AudioNormalizer(QObject):
    gain_ready = pyqtSignal(str, float)

    def __init__(self, target_base_db: float = -24.0):
        super().__init__()
        self.target_db = target_base_db
        self.gain_cache = {}
        self._analyzing = set()
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=2)

    def _measure_base_volume_db(self, filepath: str) -> float:
        with av.open(filepath) as container:
            audio_streams = [s for s in container.streams if s.type == 'audio']
            if not audio_streams:
                return -24.0

            stream = audio_streams[0]
            rate = stream.rate or 44100
            dur = float(container.duration / 1000000.0) if container.duration else 0.0

            if dur > 20.0:
                seek_pos = max(3.0, dur * 0.10)
                try:
                    container.seek(int(seek_pos * 1000000))
                except Exception:
                    pass

            chunk_dbs = []
            collected_sec = 0.0

            for frame in container.decode(stream):
                arr = frame.to_ndarray()
                if np.issubdtype(arr.dtype, np.integer):
                    data = arr.astype(np.float32) / np.iinfo(arr.dtype).max
                else:
                    data = arr.astype(np.float32)

                rms = float(np.sqrt(np.mean(data ** 2) + 1e-9))
                db = 20.0 * math.log10(rms + 1e-9)
                chunk_dbs.append(db)

                collected_sec += frame.samples / rate
                if collected_sec >= 12.0:
                    break

            if not chunk_dbs:
                return -24.0

            dbs = np.array(chunk_dbs, dtype=np.float32)
            active_db = dbs[dbs > -50.0]
            if len(active_db) < 10:
                active_db = dbs[dbs > -65.0]
            if len(active_db) == 0:
                return -24.0

            p15, p85 = np.percentile(active_db, [15, 85])
            core_db = active_db[(active_db >= p15) & (active_db <= p85)]

            if len(core_db) == 0:
                return float(np.mean(active_db))

            return float(np.mean(core_db))

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
                base_db = self._measure_base_volume_db(filepath)
                diff_db = self.target_db - base_db
                gain = math.pow(10.0, diff_db / 20.0)
                gain = max(0.35, min(3.0, gain))
            except Exception:
                gain = 1.0

            with self._lock:
                self.gain_cache[filepath] = gain
                self._analyzing.discard(filepath)

            self.gain_ready.emit(filepath, gain)

        self._pool.submit(run)