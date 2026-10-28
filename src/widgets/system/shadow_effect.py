import time
import ctypes
from PyQt6.QtCore import QRectF, QPointF
from PyQt6.QtGui import QPixmap, QImage

class VideoShadowRenderer:
    def __init__(self, fps_shadow: int = 24):
        self.enabled = True
        self.opacity = 0.25
        self.radius = 28
        self.offset = 8
        self.video_radius = 8.0
        self.fps_shadow = fps_shadow

        self.cache_pixmap = None
        self.cache_pos = QPointF(0, 0)
        self.is_dirty = True
        self._last_rebuild_time = 0.0

        self._cached_img = None
        self._cached_w = 0
        self._cached_h = 0

    def mark_dirty(self):
        self.is_dirty = True

    def set_params(self, enabled: bool, opacity: float, radius: int, offset: int, video_radius: float, fps: int = None):
        if fps:
            self.fps_shadow = fps
        old_key = (self.enabled, self.opacity, self.radius, self.offset, self.video_radius)
        self.enabled = enabled
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.radius = max(0, min(100, int(radius)))
        self.offset = max(-100, min(100, int(offset)))
        self.video_radius = float(video_radius)

        if old_key != (self.enabled, self.opacity, self.radius, self.offset, self.video_radius):
            self.is_dirty = True

    def render_cache(self, vf_rect: QRectF, c_engine=None, force: bool = False):
        if not self.enabled or self.opacity <= 0.01 or vf_rect.width() <= 0 or vf_rect.height() <= 0 or not c_engine:
            self.cache_pixmap = None
            self.is_dirty = False
            return

        now = time.monotonic()
        min_interval = 1.0 / max(1, self.fps_shadow)
        if not force and self.cache_pixmap is not None and (now - self._last_rebuild_time < min_interval):
            return
        self._last_rebuild_time = now

        R = float(max(2, self.radius))
        W = vf_rect.width()
        H = vf_rect.height()
        r = float(max(0.0, min(self.video_radius, W / 2.0, H / 2.0)))
        dx = self.offset * 0.75
        dy = float(self.offset)
        pix_w = max(1, int(W + 2 * R))
        pix_h = max(1, int(H + 2 * R))

        if self._cached_img is None or self._cached_w != pix_w or self._cached_h != pix_h:
            self._cached_img = QImage(pix_w, pix_h, QImage.Format.Format_ARGB32_Premultiplied)
            self._cached_w = pix_w
            self._cached_h = pix_h

        img_ptr = ctypes.cast(int(self._cached_img.bits()), ctypes.POINTER(ctypes.c_uint32))
        c_engine.c_render_rounded_box_shadow(img_ptr, pix_w, pix_h, R, R, W, H, r, R, 0, 0, 0, float(self.opacity))
        
        self.cache_pixmap = QPixmap.fromImage(self._cached_img)
        self.cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
        self.is_dirty = False