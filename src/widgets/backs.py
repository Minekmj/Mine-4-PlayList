import math
import time
import ctypes
import threading
from PyQt6.QtWidgets import QFrame, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QImage, QPen, QPainterPath, QPixmap
from src.C.native_bridge import get_native_engine
from src.effect.particles import ParticleSystem
from src.effect.borders import ScreenBorderSystem

from src.tools.profile import PerfProfiler

EFFECT_TARGET_FPS = 24
AMBIENT_MAX_FPS   = 30
SHADOW_MAX_FPS    = 24

AMBIENT_QUALITY_PERCENT = 50

profiler = PerfProfiler(interval_sec=1.0, ENABLE_PROFILER=False)

_AURORA_PALETTES = {
    '청록': ((40, 235, 190), (90, 145, 255), (190, 105, 255)),
    '분홍': ((255, 135, 190), (255, 190, 215), (205, 125, 255)),
    '파랑': ((35, 180, 255), (50, 115, 245), (90, 235, 230)),
    '보라': ((170, 100, 255), (100, 100, 255), (255, 100, 210)),
    '주황': ((255, 120, 85), (255, 175, 100), (255, 100, 165)),
}

class AmbientVideoContainer(QFrame):
    _ambient_rendered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.c_engine = get_native_engine()
        self.video_widget = None
        self.dock_widget = None
        self.playlist_widget = None
        self.playlist_visible = True
        self.aurora_enabled = True
        self.aurora_style = '오로라'
        self.aurora_palette = '청록'
        self.aurora_intensity = 0.55
        self.aurora_phase = 0.0
        self._aurora_gradient_cache = {}
        self._aurora_steps = 16
        self._aurora_y_buf = (ctypes.c_float * (self._aurora_steps + 1))()
        self.particle_system = ParticleSystem()
        self.border_system = ScreenBorderSystem()
        self.video_aspect = 16.0 / 9.0

        self.fps_effect = EFFECT_TARGET_FPS
        self.fps_ambient = AMBIENT_MAX_FPS
        self.fps_shadow = SHADOW_MAX_FPS
        self.ambient_quality_percent = AMBIENT_QUALITY_PERCENT

        base_w, base_h = 360, 200
        quality_scale = max(0.1, min(1.0, self.ambient_quality_percent / 100.0))
        self.c_w = max(32, int(round(base_w * quality_scale)))
        self.c_h = max(18, int(round(base_h * quality_scale)))
        self._ambient_scale = quality_scale

        self._ambient_front_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._ambient_front_img.fill(0)
        self._ambient_mid_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._ambient_mid_img.fill(0)
        self._ambient_back_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self._ambient_back_img.fill(0)
        self._ambient_temp_buf = (ctypes.c_uint32 * (self.c_w * self.c_h))()
        
        self._ambient_lock = threading.Lock()
        self._job_lock = threading.Lock()
        self._has_new_ambient = False
        self._pending_job = None
        self._last_ambient_render_time = 0.0
        self.raw_frame_image = None
        
        self.ambient_enabled = True
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

        self.motion_intensity = 0.35
        self.motion_speed = 1.0
        self.tint_enabled = False
        self.tint_color = QColor('#38BDF8')
        self.tint_ratio = 0.2
        self.floating_rim_enabled = True
        self.shadow_enabled = True
        self.shadow_opacity = 0.25
        self.shadow_radius = 28
        self.shadow_offset = 8
        self._shadow_cache_pixmap = None
        self._shadow_cache_pos = QPointF(0, 0)
        self._shadow_dirty = True
        self._last_shadow_rebuild_time = 0.0
        self._window_clip_path = None
        self._window_clip_key = None
        self._base_window_color = QColor(8, 10, 16, 255)
        self._base_fullscreen_color = QColor(0, 0, 0, 255)
        self._rim_pen = QPen(QColor(255, 255, 255, 45), 1.0)
        self._tint_overlay_color = QColor(self.tint_color)
        self._tint_overlay_color.setAlpha(int(255 * self.tint_ratio * 0.35))
        self.phase = 0.0
        self.window_radius = 12.0
        self.video_radius = 8.0
        self._ambient_params_key = self._ambient_render_settings_key()
        self._ambient_rendered.connect(self.update)
        
        self._effect_cache_pixmap = None
        self._effect_last_render_time = 0.0
        self._effect_dirty = True

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(max(10, int(1000 / max(1, self.fps_effect))))
        self.anim_timer.timeout.connect(self.on_anim_tick)
        self.anim_timer.start()
        
        self.is_mini_mode = False
        
        self._worker_event = threading.Event()
        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._ambient_worker_loop, daemon=True)
        self._worker_thread.start()

    def _update_ambient_quality(self, percent: int):
        percent = max(10, min(100, int(percent)))
        if self.ambient_quality_percent == percent:
            return
        self.ambient_quality_percent = percent
        base_w, base_h = 360, 200
        quality_scale = max(0.1, min(1.0, percent / 100.0))
        self.c_w = max(32, int(round(base_w * quality_scale)))
        self.c_h = max(18, int(round(base_h * quality_scale)))
        self._ambient_scale = quality_scale

        with self._ambient_lock:
            self._ambient_front_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._ambient_front_img.fill(0)
            self._ambient_mid_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._ambient_mid_img.fill(0)
            self._ambient_back_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
            self._ambient_back_img.fill(0)
            self._ambient_temp_buf = (ctypes.c_uint32 * (self.c_w * self.c_h))()
            self._has_new_ambient = False

        self._trigger_ambient_prerender(force=True)

    def _ambient_render_settings_key(self):
        return (
            self.ambient_enabled, self.brightness, self.black_lift, self.gamma,
            self.decay_scale, self.blur_radius, self.ambient_quality_percent,
            self.vignette_enabled, self.vignette_max_dist, self.vignette_intensity,
            self.vignette_shape_depth, self.vignette_darkness
        )

    @staticmethod
    def _set_widget_geometry(widget: QWidget, x: int, y: int, width: int, height: int):
        geometry = (int(x), int(y), max(0, int(width)), max(0, int(height)))
        if tuple(widget.geometry().getRect()) != geometry:
            widget.setGeometry(*geometry)

    def set_window_radius(self, radius: float):
        r = max(0.0, float(radius))
        if abs(self.window_radius - r) > 0.01:
            self.window_radius = r
            self._window_clip_key = None
            self.update()

    def set_video_radius(self, radius: float):
        r = max(0.0, float(radius))
        if abs(self.video_radius - r) > 0.01:
            self.video_radius = r
            self._shadow_dirty = True
            self.update()

    def set_children_widgets(self, video_w: QWidget, dock_w: QWidget, list_w: QWidget):
        self.video_widget = video_w
        self.dock_widget = dock_w
        self.playlist_widget = list_w
        self.video_widget.setParent(self)
        self.dock_widget.setParent(self)
        self.playlist_widget.setParent(self)
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)

    def set_playlist_visibility(self, visible: bool):
        visible = bool(visible)
        if self.playlist_visible == visible:
            return
        self.playlist_visible = visible
        if self.playlist_widget:
            self.playlist_widget.setVisible(visible)
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)
        self.update()

    def set_ambient_params(self, cfg: dict):
        old_ambient_key = self._ambient_render_settings_key()
        old_aurora_key = (self.aurora_style, self.aurora_palette, self.aurora_intensity)
        old_shadow_key = (self.shadow_enabled, self.shadow_opacity, self.shadow_radius, self.shadow_offset, self.video_radius)

        if "fps_effect" in cfg:
            self.fps_effect = max(10, min(60, int(cfg.get("fps_effect", 24))))
            self.anim_timer.setInterval(max(10, int(1000 / max(1, self.fps_effect))))
        if "fps_ambient" in cfg:
            self.fps_ambient = max(10, min(120, int(cfg.get("fps_ambient", 60))))
        if "fps_shadow" in cfg:
            self.fps_shadow = max(5, min(60, int(cfg.get("fps_shadow", 24))))

        quality_pct = int(cfg.get("ambient_quality_percent", self.ambient_quality_percent))
        if quality_pct != self.ambient_quality_percent:
            self._update_ambient_quality(quality_pct)

        self.ambient_enabled = bool(cfg.get('ambient_glow', True))
        self.brightness = float(cfg.get('ambient_brightness', 1.65))
        self.black_lift = float(cfg.get('ambient_black_lift', 0.25))
        self.gamma = float(cfg.get('ambient_gamma', 1.35))
        self.decay_scale = float(cfg.get('ambient_decay_scale', 1.0))

        self.vignette_enabled = bool(cfg.get('ambient_vignette_enabled', True))
        self.vignette_max_dist = float(cfg.get('ambient_vignette_max_dist', 85.0))
        self.vignette_intensity = float(cfg.get('ambient_vignette_intensity', 1.65))
        self.vignette_shape_depth = float(cfg.get('ambient_vignette_shape_depth', 0.85))
        self.vignette_darkness = float(cfg.get('ambient_vignette_darkness', 0.80))

        try:
            self.blur_radius = max(0, min(64, int(round(float(cfg.get('ambient_blur_radius', 12))))))
        except (TypeError, ValueError, OverflowError):
            self.blur_radius = 12
        self.motion_intensity = max(0.0, min(1.0, float(cfg.get('ambient_motion_intensity', 0.35))))
        self.motion_speed = max(0.0, min(5.0, float(cfg.get('ambient_motion_speed', 1.0))))
        self.tint_enabled = bool(cfg.get('ambient_tint_enabled', False))
        self.tint_color = QColor(cfg.get('ambient_tint_color', '#38BDF8'))
        self.tint_ratio = max(0.0, min(1.0, float(cfg.get('ambient_tint_ratio', 0.2))))
        self._tint_overlay_color = QColor(self.tint_color)
        self._tint_overlay_color.setAlpha(int(255 * self.tint_ratio * 0.35))
        self.aurora_enabled = bool(cfg.get('aurora_enabled', True))
        self.aurora_style = str(cfg.get('aurora_style', '오로라'))
        self.aurora_palette = str(cfg.get('aurora_palette', '청록'))
        self.particle_system.set_params(
            enabled=bool(cfg.get('particle_enabled', True)),
            p_type=str(cfg.get('particle_type', '먼지')),
            direction=str(cfg.get('particle_direction', '아래로')),
            palette=str(cfg.get('particle_palette', '청록')),
            density=float(cfg.get('particle_density', 0.45)),
            speed=float(cfg.get('particle_speed', 1.0))
        )
        
        col1 = cfg.get('border_color1', cfg.get('border_color', '#38BDF8'))
        col2 = cfg.get('border_color2', '#818CF8')
        border_r = int(cfg.get('border_radius', 0))
        border_en = bool(cfg.get('border_enabled', True))
        self.border_system.set_params(
            enabled=bool(cfg.get('border_enabled', True)),
            style=str(cfg.get('border_style', '네온')),
            color_mode=str(cfg.get('border_color_mode', '단색')),
            color1=str(col1),
            color2=str(col2),
            anim_mode=str(cfg.get('border_anim_mode', '숨쉬기')),
            anim_speed=float(cfg.get('border_anim_speed', 1.0)),
            pulse_depth=float(cfg.get('border_pulse_depth', 0.35)),
            width=int(cfg.get('border_width', 3)),
            margin=int(cfg.get('border_margin', 0)),
            radius=border_r,
            glow_spread=int(cfg.get('border_glow_spread', 14)),
            opacity=float(cfg.get('border_opacity', 0.75))
        )
        self.floating_rim_enabled = bool(cfg.get('video_floating_rim', True))
        self.shadow_enabled = bool(cfg.get('video_shadow_enabled', True))
        self.shadow_opacity = max(0.0, min(1.0, float(cfg.get('video_shadow_opacity', 0.25))))
        self.shadow_radius = max(0, min(100, int(cfg.get('video_shadow_radius', 28))))
        self.shadow_offset = max(-100, min(100, int(cfg.get('video_shadow_offset', 8))))
        raw_win_r = float(cfg.get('window_radius', 12))
        if border_en and raw_win_r < float(border_r):
            raw_win_r = float(border_r)
        self.window_radius = raw_win_r
        self.video_radius = float(cfg.get('video_radius', 8))
        if old_shadow_key != (self.shadow_enabled, self.shadow_opacity, self.shadow_radius, self.shadow_offset, self.video_radius):
            self._shadow_dirty = True
        if old_aurora_key != (self.aurora_style, self.aurora_palette, self.aurora_intensity):
            self._aurora_gradient_cache.clear()
        new_ambient_key = self._ambient_render_settings_key()
        ambient_changed = new_ambient_key != old_ambient_key
        self._ambient_params_key = new_ambient_key
        self._effect_dirty = True
        self.update_sub_geometries()
        if ambient_changed:
            self._trigger_ambient_prerender(force=True)
        self.update()
        self.restore_child_stacking()

    def _rebuild_shadow_cache(self, vf_rect: QRectF, force: bool = False):
        if not self.shadow_enabled or self.shadow_opacity <= 0.01 or vf_rect.width() <= 0 or (vf_rect.height() <= 0):
            self._shadow_cache_pixmap = None
            self._shadow_dirty = False
            return

        now = time.monotonic()
        min_shadow_interval = 1.0 / max(1, self.fps_shadow)
        if not force and self._shadow_cache_pixmap is not None and (now - self._last_shadow_rebuild_time < min_shadow_interval):
            return
        self._last_shadow_rebuild_time = now

        R = float(max(2, self.shadow_radius))
        W = vf_rect.width()
        H = vf_rect.height()
        r = float(max(0.0, min(self.video_radius, W / 2.0, H / 2.0)))
        dx = self.shadow_offset * 0.75
        dy = float(self.shadow_offset)
        pix_w = max(1, int(W + 2 * R))
        pix_h = max(1, int(H + 2 * R))

        if self.c_engine and hasattr(self.c_engine, 'c_render_rounded_box_shadow'):
            img = QImage(pix_w, pix_h, QImage.Format.Format_ARGB32_Premultiplied)
            img_ptr = ctypes.cast(int(img.bits()), ctypes.POINTER(ctypes.c_uint32))
            self.c_engine.c_render_rounded_box_shadow(img_ptr, pix_w, pix_h, R, R, W, H, r, R, 0, 0, 0, float(self.shadow_opacity))
            self._shadow_cache_pixmap = QPixmap.fromImage(img)
            self._shadow_cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
            self._shadow_dirty = False
            return

        pix = QPixmap(pix_w, pix_h)
        pix.fill(Qt.GlobalColor.transparent)
        sp = QPainter(pix)
        sp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        sp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        sh_alpha = int(255 * min(1.0, self.shadow_opacity))
        c_sh = QColor(0, 0, 0, sh_alpha)

        def make_gaussian_stops(grad, start_pos: float=0.0):
            span = 1.0 - start_pos
            stops = [(start_pos, 1.0), (start_pos + span * 0.18, 0.8), (start_pos + span * 0.38, 0.52), (start_pos + span * 0.6, 0.26), (start_pos + span * 0.82, 0.09), (start_pos + span * 0.96, 0.015), (1.0, 0.0)]
            for pos, mult in stops:
                grad.setColorAt(max(0.0, min(1.0, pos)), QColor(0, 0, 0, int(sh_alpha * mult)))

        if r > 0.5:
            sp.fillRect(QRectF(R + r, R, W - 2 * r, H), c_sh)
            sp.fillRect(QRectF(R, R + r, r, H - 2 * r), c_sh)
            sp.fillRect(QRectF(R + W - r, R + r, r, H - 2 * r), c_sh)
        else:
            sp.fillRect(QRectF(R, R, W, H), c_sh)

        g_top = QLinearGradient(0, R, 0, 0)
        make_gaussian_stops(g_top)
        sp.fillRect(QRectF(R + r, 0, W - 2 * r, R), g_top)

        g_bot = QLinearGradient(0, R + H, 0, R + H + R)
        make_gaussian_stops(g_bot)
        sp.fillRect(QRectF(R + r, R + H, W - 2 * r, R), g_bot)

        g_left = QLinearGradient(R, 0, 0, 0)
        make_gaussian_stops(g_left)
        sp.fillRect(QRectF(0, R + r, R, H - 2 * r), g_left)

        g_right = QLinearGradient(R + W, 0, R + W + R, 0)
        make_gaussian_stops(g_right)
        sp.fillRect(QRectF(R + W, R + r, R, H - 2 * r), g_right)

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
        self._shadow_cache_pixmap = pix
        self._shadow_cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
        self._shadow_dirty = False

    def _render_effect_layer(self, W: int, H: int):
        if self._effect_cache_pixmap is None or self._effect_cache_pixmap.size() != self.size():
            self._effect_cache_pixmap = QPixmap(W, H)
        
        self._effect_cache_pixmap.fill(Qt.GlobalColor.transparent)
        ep = QPainter(self._effect_cache_pixmap)
        ep.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        ep.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        with profiler.measure("[Paint] Aurora"):
            self._paint_aurora(ep, W, H)

        vf_rect = QRectF(self.video_widget.geometry()) if self.video_widget and self.video_widget.isVisible() else None
        with profiler.measure("[Paint] Particles"):
            self.particle_system.draw(ep, W, H, exclude_rect=vf_rect)

        with profiler.measure("[Paint] Border"):
            self.border_system.draw(ep, W, H)

        ep.end()
        self._effect_last_render_time = time.monotonic()
        self._effect_dirty = False

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        W, H = (self.width(), self.height())
        if W <= 0 or H <= 0:
            p.end()
            return

        vf_rect = QRectF(self.video_widget.geometry()) if self.video_widget else QRectF(W * 0.15, H * 0.15, W * 0.7, H * 0.7)
        is_fs = self.window().isFullScreen() if self.window() else False
        eff_wr = 0.0 if is_fs else self.window_radius
        if not is_fs and self.border_system.enabled and (self.border_system.style != '없음'):
            eff_wr = max(eff_wr, float(self.border_system.radius))
        if eff_wr > 0.5:
            clip_key = (W, H, round(eff_wr, 3))
            if self._window_clip_key != clip_key or self._window_clip_path is None:
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, W, H), eff_wr, eff_wr)
                self._window_clip_path = path
                self._window_clip_key = clip_key
            p.setClipPath(self._window_clip_path)
        p.fillRect(0, 0, W, H, self._base_fullscreen_color if is_fs else self._base_window_color)
        
        if self.ambient_enabled and self.video_widget:
            with self._ambient_lock:
                if self._has_new_ambient:
                    self._ambient_front_img, self._ambient_mid_img = self._ambient_mid_img, self._ambient_front_img
                    self._has_new_ambient = False

            has_ambient = not self._ambient_front_img.isNull()
            if has_ambient:
                with profiler.measure("[Paint] Ambient Draw"):
                    p.drawImage(QRectF(0, 0, W, H), self._ambient_front_img)
            
                if self.shadow_enabled and self.shadow_opacity > 0.01:
                    with profiler.measure("[Paint] Shadow"):
                        if self._shadow_dirty or self._shadow_cache_pixmap is None:
                            self._rebuild_shadow_cache(vf_rect)
                        if self._shadow_cache_pixmap:
                            p.drawPixmap(self._shadow_cache_pos, self._shadow_cache_pixmap)
                
                if self.floating_rim_enabled:
                    p.save()
                    p.setPen(self._rim_pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    vr = float(self.video_radius)
                    rim_rect = vf_rect.adjusted(-0.5, -0.5, 0.5, 0.5)
                    if vr > 0.5:
                        p.drawRoundedRect(rim_rect, vr, vr)
                    else:
                        p.drawRect(rim_rect)
                    p.restore()
                
                if self.tint_enabled and self.tint_ratio > 0.01:
                    p.fillRect(0, 0, W, H, self._tint_overlay_color)

        if self._effect_dirty or self._effect_cache_pixmap is None:
            self._render_effect_layer(W, H)

        if self._effect_cache_pixmap:
            with profiler.measure("[Paint] Effect Cache Blit"):
                p.drawPixmap(0, 0, self._effect_cache_pixmap)
        
        p.end()

    def on_anim_tick(self):
        active = False
        if self.ambient_enabled and self.raw_frame_image is not None and (self.motion_intensity > 0.01):
            self.phase = (self.phase + 0.05 * self.motion_speed) % (math.pi * 2.0)
        if self.aurora_enabled and self.aurora_style != '없음' and (self.aurora_intensity > 0.001):
            self.aurora_phase = (self.aurora_phase + 0.015) % (math.pi * 2.0)
            active = True
        
        with profiler.measure("[Tick] Particle/Border Update"):
            if self.particle_system.enabled and self.particle_system.density > 0.001:
                self.particle_system.update(self.width(), self.height())
                active = True
            if self.border_system.enabled and self.border_system.style != '없음':
                self.border_system.update()
                if self.border_system.anim_mode not in ('정지', '없음') or self.border_system.color_mode == '무지개':
                    active = True

        if active:
            self._effect_dirty = True
            self.update()

    def set_aspect_ratio(self, aspect: float):
        if aspect > 0.1 and abs(self.video_aspect - aspect) > 0.01:
            self.video_aspect = aspect
            self._shadow_dirty = True
            self._effect_dirty = True
            self.update_sub_geometries()
            self._trigger_ambient_prerender(force=True)
            self.update()

    def restore_child_stacking(self):
        if not self.video_widget or not self.dock_widget or (not self.playlist_widget):
            return
        self.video_widget.raise_()
        if self.dock_widget.isVisible():
            self.dock_widget.raise_()
        if self.playlist_visible and self.playlist_widget.isVisible():
            self.playlist_widget.raise_()

    def update_sub_geometries(self):
        if not self.video_widget or not self.dock_widget or (not self.playlist_widget):
            return
        W, H = (self.width(), self.height())
        old_video_rect = tuple(self.video_widget.geometry().getRect())
        if self.is_mini_mode:
            pad = 12
            avail_w = max(40, W - pad * 2)
            avail_h = max(40, H - pad * 2)
            if avail_w / max(1.0, avail_h) > self.video_aspect:
                target_h = int(avail_h)
                target_w = int(round(target_h * self.video_aspect))
            else:
                target_w = int(avail_w)
                target_h = int(round(target_w / self.video_aspect))
            vx = (W - target_w) // 2
            vy = (H - target_h) // 2
            self._set_widget_geometry(self.video_widget, vx, vy, target_w, target_h)
            self.video_widget.show()
            self.dock_widget.hide()
            self.playlist_widget.hide()
        else:
            pad = 16
            plist_w = 330 if self.playlist_visible else 0
            if self.playlist_visible:
                self._set_widget_geometry(self.playlist_widget, W - plist_w - pad, pad, plist_w, max(0, H - 2 * pad))
            avail_w = max(100, W - (plist_w + pad * 2 if self.playlist_visible else pad * 2) - 100)
            avail_h = max(100, H - 220)
            if avail_w / max(1.0, avail_h) > self.video_aspect:
                target_h = int(avail_h)
                target_w = int(round(target_h * self.video_aspect))
            else:
                target_w = int(avail_w)
                target_h = int(round(target_w / self.video_aspect))
            view_center_x = (W - (plist_w + pad if self.playlist_visible else 0)) // 2
            view_center_y = (H - 50) // 2
            vx = view_center_x - target_w // 2
            vy = view_center_y - target_h // 2
            self._set_widget_geometry(self.video_widget, vx, vy, target_w, target_h)
            self.video_widget.show()
            dock_w = min(880, max(520, target_w + 40))
            dock_h = 76
            self._set_widget_geometry(self.dock_widget, view_center_x - dock_w // 2, H - dock_h - pad, dock_w, dock_h)
        if tuple(self.video_widget.geometry().getRect()) != old_video_rect:
            self._shadow_dirty = True
            self._effect_dirty = True
        self.restore_child_stacking()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._effect_dirty = True
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)

    def update_video_frame(self, qimage: QImage):
        if qimage.isNull() or not self.ambient_enabled or not self.video_widget:
            return

        self.raw_frame_image = qimage
        self._trigger_ambient_prerender(image=qimage, force=False)

    def _paint_aurora(self, p: QPainter, w: int, h: int):
        if not self.aurora_enabled or self.aurora_style == '없음' or self.aurora_intensity <= 0.001 or (w <= 0) or (h <= 0):
            return
        palette_key = _AURORA_PALETTES.get(self.aurora_palette, _AURORA_PALETTES['청록'])
        phase = self.aurora_phase
        is_aurora = self.aurora_style == '오로라'
        band_h = max(90, int(h * (0.42 if is_aurora else 0.3)))
        amp = (0.075 if is_aurora else 0.035) * self.aurora_intensity
        gradient_key = (w, h, band_h, is_aurora, palette_key, round(self.aurora_intensity, 4))
        gradients = self._aurora_gradient_cache.get(gradient_key)
        if gradients is None:
            gradients = []
            for i, rgb in enumerate(palette_key):
                color = QColor(*rgb)
                grad = QLinearGradient(0, h * max(0.0, 0.12 + i * 0.07 - amp), 0, band_h)
                top = QColor(color)
                top.setAlpha(int((75 if is_aurora else 42) * self.aurora_intensity))
                mid = QColor(color)
                mid.setAlpha(int((25 if is_aurora else 18) * self.aurora_intensity))
                end = QColor(color)
                end.setAlpha(0)
                grad.setColorAt(0.0, top)
                grad.setColorAt(0.55, mid)
                grad.setColorAt(1.0, end)
                gradients.append(grad)
            self._aurora_gradient_cache[gradient_key] = gradients
            if len(self._aurora_gradient_cache) > 12:
                self._aurora_gradient_cache.pop(next(iter(self._aurora_gradient_cache)))
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(Qt.PenStyle.NoPen)
        steps = self._aurora_steps
        step_w = w / steps
        use_c = self.c_engine is not None and hasattr(self.c_engine, 'c_compute_aurora_wave')
        for i, grad in enumerate(gradients):
            base = 0.12 + i * 0.07
            path = QPainterPath()
            path.moveTo(0, h * base)
            if use_c:
                self.c_engine.c_compute_aurora_wave(self._aurora_y_buf, steps, float(h), float(base), float(amp), float(phase), i)
                for n in range(steps + 1):
                    path.lineTo(n * step_w, self._aurora_y_buf[n])
            else:
                for n in range(steps + 1):
                    x = n * step_w
                    ratio = n / steps
                    w1 = math.sin(ratio * math.pi * 2.0 * (1.15 + i * 0.4) + phase * 4.0 + i * 1.6)
                    w2 = math.sin(ratio * math.pi * 1.1 - phase * 1.8 + i)
                    y = h * base + h * amp * w1 + h * 0.016 * w2
                    path.lineTo(x, y)
            path.lineTo(w, band_h)
            path.lineTo(0, band_h)
            path.closeSubpath()
            p.setBrush(grad)
            p.drawPath(path)
        p.restore()

    def _trigger_ambient_prerender(self, image: QImage = None, force: bool = False):
        if not self.ambient_enabled or not self.c_engine:
            return
        
        target_img = image if image is not None else self.raw_frame_image
        if target_img is None or target_img.isNull() or not self.video_widget:
            return

        W, H = (self.width(), self.height())
        if W <= 0 or H <= 0:
            return
        vf_key = tuple(self.video_widget.geometry().getRect())
        
        with self._job_lock:
            self._pending_job = (target_img, W, H, vf_key)
        self._worker_event.set()

    def _ambient_worker_loop(self):
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

                max_src_w = int(480 * self._ambient_scale)
                if raw_image.width() > max_src_w:
                    max_src_h = max(1, int(max_src_w * (raw_image.height() / raw_image.width())))
                    image = raw_image.scaled(
                        max_src_w, max_src_h,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.FastTransformation
                    )
                else:
                    image = raw_image

                rendered = self._render_ambient_to_back_buffer(image, W, H, vf_key)
                if rendered:
                    with self._ambient_lock:
                        self._ambient_back_img, self._ambient_mid_img = self._ambient_mid_img, self._ambient_back_img
                        self._has_new_ambient = True
                    
                    self._ambient_rendered.emit()
            except Exception as e:
                print(f"[Ambient Worker Error] {e}")

    def _render_ambient_to_back_buffer(self, image: QImage, W: int, H: int, vf_key: tuple):
        if not self.c_engine or image is None or image.isNull():
            return False
            
        sx, sy = (self.c_w / float(max(1, W)), self.c_h / float(max(1, H)))
        c_vx1, c_vy1 = (vf_key[0] * sx, vf_key[1] * sy)
        c_vx2, c_vy2 = ((vf_key[0] + vf_key[2]) * sx, (vf_key[1] + vf_key[3]) * sy)
        output_image = self._ambient_back_img
        out_ptr = ctypes.cast(int(output_image.bits()), ctypes.POINTER(ctypes.c_uint32))
        src_ptr = ctypes.cast(int(image.bits()), ctypes.POINTER(ctypes.c_uint32))

        scaled_blur = max(1, int(round(self.blur_radius * self._ambient_scale)))

        with profiler.measure("[Worker] Vanishing Engine (C)"):
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
            with profiler.measure("[Worker] Gaussian Blur (C)"):
                self.c_engine.c_apply_optical_gaussian_blur(
                    out_ptr, self._ambient_temp_buf, self.c_w, self.c_h, scaled_blur
                )

        self._last_ambient_render_time = time.monotonic()
        return True