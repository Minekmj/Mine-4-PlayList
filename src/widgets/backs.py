import math
from PyQt6.QtWidgets import QFrame, QWidget
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QImage, QPen, QPainterPath, QPixmap

from src.C.native_bridge import get_native_engine
from src.effect.particles import ParticleSystem
from src.effect.borders import ScreenBorderSystem
from src.tools.profile import PerfProfiler

from src.widgets.system.layout_manager import ContainerLayoutManager
from src.widgets.system.aurora_effect import AuroraRenderer
from src.widgets.system.shadow_effect import VideoShadowRenderer
from src.widgets.system.ambient import AmbientPipeline

EFFECT_TARGET_FPS = 24
AMBIENT_MAX_FPS   = 30
SHADOW_MAX_FPS    = 24
AMBIENT_QUALITY_PERCENT = 50

profiler = PerfProfiler(interval_sec=1.0, ENABLE_PROFILER=False)

class AmbientVideoContainer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.c_engine = get_native_engine()

        self.video_widget = None
        self.dock_widget = None
        self.playlist_widget = None

        self.layout_mgr = ContainerLayoutManager()
        self.aurora_mgr = AuroraRenderer()
        self.shadow_mgr = VideoShadowRenderer(fps_shadow=SHADOW_MAX_FPS)
        self.ambient_pipe = AmbientPipeline(self.c_engine, profiler, quality_percent=AMBIENT_QUALITY_PERCENT)
        self.ambient_pipe.rendered.connect(self.update)

        self.particle_system = ParticleSystem()
        self.border_system = ScreenBorderSystem()

        self.fps_effect = EFFECT_TARGET_FPS
        self.fps_ambient = AMBIENT_MAX_FPS
        self.raw_frame_image = None
        self.phase = 0.0
        self.motion_intensity = 0.35
        self.motion_speed = 1.0

        self.floating_rim_enabled = True
        self.tint_enabled = False
        self.tint_color = QColor('#38BDF8')
        self.tint_ratio = 0.2
        self._tint_overlay_color = QColor(self.tint_color)
        self._tint_overlay_color.setAlpha(int(255 * self.tint_ratio * 0.35))
        self._rim_pen = QPen(QColor(255, 255, 255, 45), 1.0)
        self._base_window_color = QColor(8, 10, 16, 255)
        self._base_fullscreen_color = QColor(0, 0, 0, 255)

        self.window_radius = 12.0
        self._window_clip_path = None
        self._window_clip_key = None

        self._effect_cache_pixmap = None
        self._effect_dirty = True

        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(max(10, int(1000 / max(1, self.fps_effect))))
        self.anim_timer.timeout.connect(self.on_anim_tick)
        self.anim_timer.start()

    @property
    def is_mini_mode(self): return self.layout_mgr.is_mini_mode
    @is_mini_mode.setter
    def is_mini_mode(self, val): self.layout_mgr.is_mini_mode = val

    @property
    def playlist_visible(self): return self.layout_mgr.playlist_visible

    def set_children_widgets(self, video_w: QWidget, dock_w: QWidget, list_w: QWidget):
        self.video_widget = video_w
        self.dock_widget = dock_w
        self.playlist_widget = list_w
        for w in (video_w, dock_w, list_w):
            w.setParent(self)
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)

    def set_playlist_visibility(self, visible: bool):
        if self.layout_mgr.playlist_visible == visible:
            return
        self.layout_mgr.playlist_visible = bool(visible)
        if self.playlist_widget:
            self.playlist_widget.setVisible(visible)
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)
        self.update()

    def set_aspect_ratio(self, aspect: float):
        if aspect > 0.1 and abs(self.layout_mgr.video_aspect - aspect) > 0.01:
            self.layout_mgr.video_aspect = aspect
            self.shadow_mgr.mark_dirty()
            self._effect_dirty = True
            self.update_sub_geometries()
            self._trigger_ambient_prerender(force=True)
            self.update()

    def set_window_radius(self, radius: float):
        r = max(0.0, float(radius))
        if abs(self.window_radius - r) > 0.01:
            self.window_radius = r
            self._window_clip_key = None
            self.update()

    def set_video_radius(self, radius: float):
        self.shadow_mgr.set_params(self.shadow_mgr.enabled, self.shadow_mgr.opacity,
                                   self.shadow_mgr.radius, self.shadow_mgr.offset, radius)
        self.update()

    def update_sub_geometries(self):
        changed = self.layout_mgr.update_geometries(
            self.width(), self.height(), self.video_widget, self.dock_widget, self.playlist_widget
        )
        if changed:
            self.shadow_mgr.mark_dirty()
            self._effect_dirty = True
        self.restore_child_stacking()

    def restore_child_stacking(self):
        self.layout_mgr.restore_child_stacking(
            self.video_widget, self.dock_widget, self.playlist_widget, self.layout_mgr.playlist_visible
        )

    def set_ambient_params(self, cfg: dict):
        if "fps_effect" in cfg:
            self.fps_effect = max(10, min(60, int(cfg.get("fps_effect", 24))))
            self.anim_timer.setInterval(max(10, int(1000 / max(1, self.fps_effect))))
        if "fps_ambient" in cfg:
            self.fps_ambient = max(10, min(120, int(cfg.get("fps_ambient", 60))))

        # 앰비언트
        if "ambient_quality_percent" in cfg:
            self.ambient_pipe.update_quality(int(cfg["ambient_quality_percent"]))
        self.ambient_pipe.enabled = bool(cfg.get('ambient_glow', True))
        self.ambient_pipe.brightness = float(cfg.get('ambient_brightness', 1.65))
        self.ambient_pipe.black_lift = float(cfg.get('ambient_black_lift', 0.25))
        self.ambient_pipe.gamma = float(cfg.get('ambient_gamma', 1.35))
        self.ambient_pipe.decay_scale = float(cfg.get('ambient_decay_scale', 1.0))
        self.ambient_pipe.blur_radius = max(0, min(64, int(round(float(cfg.get('ambient_blur_radius', 12))))))
        self.ambient_pipe.vignette_enabled = bool(cfg.get('ambient_vignette_enabled', True))
        self.ambient_pipe.vignette_max_dist = float(cfg.get('ambient_vignette_max_dist', 85.0))
        self.ambient_pipe.vignette_intensity = float(cfg.get('ambient_vignette_intensity', 1.65))
        self.ambient_pipe.vignette_shape_depth = float(cfg.get('ambient_vignette_shape_depth', 0.85))
        self.ambient_pipe.vignette_darkness = float(cfg.get('ambient_vignette_darkness', 0.80))

        # 오로라
        self.aurora_mgr.set_params(
            enabled=bool(cfg.get('aurora_enabled', True)),
            style=str(cfg.get('aurora_style', '오로라')),
            palette=str(cfg.get('aurora_palette', '청록')),
            intensity=float(cfg.get('aurora_intensity', 0.55))
        )

        # 그림자
        sh_fps = max(5, min(60, int(cfg.get("fps_shadow", 24))))
        vr = float(cfg.get('video_radius', 8))
        self.shadow_mgr.set_params(
            enabled=bool(cfg.get('video_shadow_enabled', True)),
            opacity=float(cfg.get('video_shadow_opacity', 0.25)),
            radius=int(cfg.get('video_shadow_radius', 28)),
            offset=int(cfg.get('video_shadow_offset', 8)),
            video_radius=vr,
            fps=sh_fps
        )

        # 기타
        self.motion_intensity = max(0.0, min(1.0, float(cfg.get('ambient_motion_intensity', 0.35))))
        self.motion_speed = max(0.0, min(5.0, float(cfg.get('ambient_motion_speed', 1.0))))
        self.tint_enabled = bool(cfg.get('ambient_tint_enabled', False))
        self.tint_color = QColor(cfg.get('ambient_tint_color', '#38BDF8'))
        self.tint_ratio = max(0.0, min(1.0, float(cfg.get('ambient_tint_ratio', 0.2))))
        self._tint_overlay_color = QColor(self.tint_color)
        self._tint_overlay_color.setAlpha(int(255 * self.tint_ratio * 0.35))
        self.floating_rim_enabled = bool(cfg.get('video_floating_rim', True))

        # 파티클 & 보더
        self.particle_system.set_params(
            enabled=bool(cfg.get('particle_enabled', True)),
            p_type=str(cfg.get('particle_type', '먼지')),
            direction=str(cfg.get('particle_direction', '아래로')),
            palette=str(cfg.get('particle_palette', '청록')),
            density=float(cfg.get('particle_density', 0.45)),
            speed=float(cfg.get('particle_speed', 1.0))
        )
        border_r = int(cfg.get('border_radius', 0))
        border_en = bool(cfg.get('border_enabled', True))
        self.border_system.set_params(
            enabled=border_en,
            style=str(cfg.get('border_style', '네온')),
            color_mode=str(cfg.get('border_color_mode', '단색')),
            color1=str(cfg.get('border_color1', cfg.get('border_color', '#38BDF8'))),
            color2=str(cfg.get('border_color2', '#818CF8')),
            anim_mode=str(cfg.get('border_anim_mode', '숨쉬기')),
            anim_speed=float(cfg.get('border_anim_speed', 1.0)),
            pulse_depth=float(cfg.get('border_pulse_depth', 0.35)),
            width=int(cfg.get('border_width', 3)),
            margin=int(cfg.get('border_margin', 0)),
            radius=border_r,
            glow_spread=int(cfg.get('border_glow_spread', 14)),
            opacity=float(cfg.get('border_opacity', 0.75))
        )

        raw_win_r = float(cfg.get('window_radius', 12))
        if border_en and raw_win_r < float(border_r):
            raw_win_r = float(border_r)
        self.window_radius = raw_win_r

        self._effect_dirty = True
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)
        self.update()

    def update_video_frame(self, qimage: QImage):
        if qimage.isNull() or not self.ambient_pipe.enabled or not self.video_widget:
            return
        self.raw_frame_image = qimage
        self._trigger_ambient_prerender(image=qimage)

    def _trigger_ambient_prerender(self, image: QImage = None, force: bool = False):
        target_img = image if image is not None else self.raw_frame_image
        if target_img is None or target_img.isNull() or not self.video_widget:
            return
        W, H = self.width(), self.height()
        vf_rect = tuple(self.video_widget.geometry().getRect())
        self.ambient_pipe.trigger_prerender(target_img, W, H, vf_rect)

    def on_anim_tick(self):
        active = False
        if self.ambient_pipe.enabled and self.raw_frame_image is not None and self.motion_intensity > 0.01:
            self.phase = (self.phase + 0.05 * self.motion_speed) % (math.pi * 2.0)

        if self.aurora_mgr.tick():
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

    def _render_effect_layer(self, W: int, H: int):
        if self._effect_cache_pixmap is None or self._effect_cache_pixmap.size() != self.size():
            self._effect_cache_pixmap = QPixmap(W, H)

        self._effect_cache_pixmap.fill(Qt.GlobalColor.transparent)
        ep = QPainter(self._effect_cache_pixmap)
        ep.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        ep.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        with profiler.measure("[Paint] Aurora"):
            self.aurora_mgr.paint(ep, W, H, self.c_engine)

        vf_rect = QRectF(self.video_widget.geometry()) if self.video_widget and self.video_widget.isVisible() else None
        with profiler.measure("[Paint] Particles"):
            self.particle_system.draw(ep, W, H, exclude_rect=vf_rect)

        with profiler.measure("[Paint] Border"):
            self.border_system.draw(ep, W, H)

        ep.end()
        self._effect_dirty = False

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        W, H = self.width(), self.height()
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

        if self.ambient_pipe.enabled and self.video_widget:
            front_img = self.ambient_pipe.acquire_front_image()
            if not front_img.isNull():
                with profiler.measure("[Paint] Ambient Draw"):
                    p.drawImage(QRectF(0, 0, W, H), front_img)

                if self.shadow_mgr.enabled and self.shadow_mgr.opacity > 0.01:
                    with profiler.measure("[Paint] Shadow"):
                        if self.shadow_mgr.is_dirty or self.shadow_mgr.cache_pixmap is None:
                            self.shadow_mgr.render_cache(vf_rect, self.c_engine)
                        if self.shadow_mgr.cache_pixmap:
                            p.drawPixmap(self.shadow_mgr.cache_pos, self.shadow_mgr.cache_pixmap)

                if self.floating_rim_enabled:
                    p.save()
                    p.setPen(self._rim_pen)
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    vr = self.shadow_mgr.video_radius
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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._effect_dirty = True
        self.update_sub_geometries()
        self._trigger_ambient_prerender(force=True)

    def closeEvent(self, event):
        self.ambient_pipe.stop()
        super().closeEvent(event)