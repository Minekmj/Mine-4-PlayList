import time
import ctypes
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPixmap, QImage

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
        if not self.enabled or self.opacity <= 0.01 or vf_rect.width() <= 0 or vf_rect.height() <= 0:
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

        img = QImage(pix_w, pix_h, QImage.Format.Format_ARGB32_Premultiplied)
        img_ptr = ctypes.cast(int(img.bits()), ctypes.POINTER(ctypes.c_uint32))
        c_engine.c_render_rounded_box_shadow(img_ptr, pix_w, pix_h, R, R, W, H, r, R, 0, 0, 0, float(self.opacity))
        self.cache_pixmap = QPixmap.fromImage(img)
        self.cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
        self.is_dirty = False
        return

        pix = QPixmap(pix_w, pix_h)
        pix.fill(Qt.GlobalColor.transparent)
        sp = QPainter(pix)
        sp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        sp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        sh_alpha = int(255 * min(1.0, self.opacity))
        c_sh = QColor(0, 0, 0, sh_alpha)

        def make_gaussian_stops(grad, start_pos: float = 0.0):
            span = 1.0 - start_pos
            stops = [(start_pos, 1.0), (start_pos + span * 0.18, 0.8), (start_pos + span * 0.38, 0.52),
                     (start_pos + span * 0.6, 0.26), (start_pos + span * 0.82, 0.09), (start_pos + span * 0.96, 0.015), (1.0, 0.0)]
            for pos, mult in stops:
                grad.setColorAt(max(0.0, min(1.0, pos)), QColor(0, 0, 0, int(sh_alpha * mult)))

        if r > 0.5:
            sp.fillRect(QRectF(R + r, R, W - 2 * r, H), c_sh)
            sp.fillRect(QRectF(R, R + r, r, H - 2 * r), c_sh)
            sp.fillRect(QRectF(R + W - r, R + r, r, H - 2 * r), c_sh)
        else:
            sp.fillRect(QRectF(R, R, W, H), c_sh)

        for grad, rect in (
            (QLinearGradient(0, R, 0, 0), QRectF(R + r, 0, W - 2 * r, R)),
            (QLinearGradient(0, R + H, 0, R + H + R), QRectF(R + r, R + H, W - 2 * r, R)),
            (QLinearGradient(R, 0, 0, 0), QRectF(0, R + r, R, H - 2 * r)),
            (QLinearGradient(R + W, 0, R + W + R, 0), QRectF(R + W, R + r, R, H - 2 * r))
        ):
            make_gaussian_stops(grad)
            sp.fillRect(rect, grad)

        total_r = r + R
        start_ratio = r / total_r if total_r > 0 else 0.0
        for center_pt, corner_rect in (
            (QPointF(R + r, R + r), QRectF(0, 0, total_r, total_r)),
            (QPointF(R + W - r, R + r), QRectF(R + W - r, 0, total_r, total_r)),
            (QPointF(R + r, R + H - r), QRectF(0, R + H - r, total_r, total_r)),
            (QPointF(R + W - r, R + H - r), QRectF(R + W - r, R + H - r, total_r, total_r))
        ):
            grad = QRadialGradient(center_pt, total_r)
            make_gaussian_stops(grad, start_ratio)
            sp.fillRect(corner_rect, grad)

        sp.end()
        self.cache_pixmap = pix
        self.cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
        self.is_dirty = False