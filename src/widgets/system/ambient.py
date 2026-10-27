import time
import ctypes
import threading
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QImage
from src.tools.profile import PerfProfiler

class AmbientPipeline(QObject):
    rendered = pyqtSignal()

    def __init__(self, c_engine, profiler: PerfProfiler, quality_percent: int = 50, parent=None):
        super().__init__(parent)
        self.c_engine = c_engine
        self.profiler = profiler

        self.enabled = True
        self.brightness = 1.65
        self.black_lift = 0.25
        self.gamma = 1.35
        self.decay_scale = 1.0
        self.blur_radius = 12

        self.vignette_enabled = True
        self.vignette_max_dist = 85.0
        self.vignette_intensity = 1.65
        self.vignette_shape_depth = 0.85
        self.vignette_darkness = 0.80

        self.quality_percent = quality_percent
        self.c_w = 180
        self.c_h = 100
        self._scale = 0.5
        self._update_resolution(self.quality_percent)

        self._front_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._front_img.fill(0)
        self._mid_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._mid_img.fill(0)
        self._back_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._back_img.fill(0)
        self._temp_buf = (ctypes.c_uint32 * (self.c_w * self.c_h))()

        self._lock = threading.Lock()
        self._job_lock = threading.Lock()
        self._has_new = False
        self._pending_job = None
        self._last_render_time = 0.0

        self._worker_event = threading.Event()
        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _update_resolution(self, percent: int):
        self.quality_percent = max(10, min(100, int(percent)))
        base_w, base_h = 360, 200
        self._scale = max(0.1, min(1.0, self.quality_percent / 100.0))
        self.c_w = max(32, int(round(base_w * self._scale)))
        self.c_h = max(18, int(round(base_h * self._scale)))

    def update_quality(self, percent: int):
        if self.quality_percent == percent:
            return
        self._update_resolution(percent)
        with self._lock:
            self._front_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._front_img.fill(0)
            self._mid_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._mid_img.fill(0)
            self._back_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._back_img.fill(0)
            self._temp_buf = (ctypes.c_uint32 * (self.c_w * self.c_h))()
            self._has_new = False

    def trigger_prerender(self, raw_image: QImage, container_w: int, container_h: int, vf_key: tuple):
        if not self.enabled or not self.c_engine or raw_image is None or raw_image.isNull():
            return
        if container_w <= 0 or container_h <= 0:
            return
        with self._job_lock:
            self._pending_job = (raw_image, container_w, container_h, vf_key)
        self._worker_event.set()

    def acquire_front_image(self) -> QImage:
        with self._lock:
            if self._has_new:
                self._front_img, self._mid_img = self._mid_img, self._front_img
                self._has_new = False
            return self._front_img

    def stop(self):
        self._worker_running = False
        self._worker_event.set()
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.2)

    def _worker_loop(self):
        while self._worker_running:
            self._worker_event.wait()
            self._worker_event.clear()

            with self._job_lock:
                job = self._pending_job
                self._pending_job = None
            if not job:
                continue

            raw_image, W, H, vf_key = job
            try:
                if raw_image.format() not in (
                    QImage.Format.Format_RGB32,
                    QImage.Format.Format_ARGB32,
                    QImage.Format.Format_ARGB32_Premultiplied
                ):
                    raw_image = raw_image.convertToFormat(QImage.Format.Format_RGB32)

                max_src_w = int(480 * self._scale)
                if raw_image.width() > max_src_w:
                    max_src_h = max(1, int(max_src_w * (raw_image.height() / raw_image.width())))
                    image = raw_image.scaled(
                        max_src_w, max_src_h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.FastTransformation
                    )
                else:
                    image = raw_image

                if self._render_to_back_buffer(image, W, H, vf_key):
                    with self._lock:
                        self._back_img, self._mid_img = self._mid_img, self._back_img
                        self._has_new = True
                    self.rendered.emit()
            except Exception as e:
                print(f"[Ambient Worker Error] {e}")

    def _render_to_back_buffer(self, image: QImage, W: int, H: int, vf_key: tuple) -> bool:
        if not self.c_engine or image is None or image.isNull():
            return False

        sx, sy = (self.c_w / float(max(1, W)), self.c_h / float(max(1, H)))
        c_vx1, c_vy1 = (vf_key[0] * sx, vf_key[1] * sy)
        c_vx2, c_vy2 = ((vf_key[0] + vf_key[2]) * sx, (vf_key[1] + vf_key[3]) * sy)

        out_ptr = ctypes.cast(int(self._back_img.bits()), ctypes.POINTER(ctypes.c_uint32))
        src_ptr = ctypes.cast(int(image.bits()), ctypes.POINTER(ctypes.c_uint32))
        scaled_blur = max(1, int(round(self.blur_radius * self._scale)))

        with self.profiler.measure("[Worker] Vanishing Engine (C)"):
            self.c_engine.c_render_vanishing_perspective(
                out_ptr, self.c_w, self.c_h, src_ptr, image.width(), image.height(),
                c_vx1, c_vy1, c_vx2, c_vy2, self.brightness, self.black_lift, self.gamma, self.decay_scale,
                scaled_blur,
                1 if self.vignette_enabled else 0,
                float(self.vignette_max_dist),
                float(self.vignette_intensity),
                float(self.vignette_shape_depth),
                float(self.vignette_darkness)
            )

        if scaled_blur > 0:
            with self.profiler.measure("[Worker] Gaussian Blur (C)"):
                self.c_engine.c_apply_optical_gaussian_blur(
                    out_ptr, self._temp_buf, self.c_w, self.c_h, scaled_blur
                )

        self._last_render_time = time.monotonic()
        return True