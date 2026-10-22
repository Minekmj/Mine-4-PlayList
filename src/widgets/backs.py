import math
import ctypes
from PyQt6.QtWidgets import QFrame, QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QImage, QPen, QPainterPath, QPixmap
)
from src.c_ambient import get_compiled_c_engine
from src.effect.particles import ParticleSystem
from src.effect.borders import ScreenBorderSystem


class AmbientVideoContainer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._ambient_dirty = True
        self._ambient_params_key = None

        self.video_widget = None
        self.dock_widget = None
        self.playlist_widget = None
        self.playlist_visible = True

        self.aurora_enabled = True
        self.aurora_style = "오로라"
        self.aurora_palette = "청록"
        self.aurora_intensity = 0.55
        self.aurora_phase = 0.0

        self.particle_system = ParticleSystem()
        self.border_system = ScreenBorderSystem()
        self.video_aspect = 16.0 / 9.0

        self.c_w = 360
        self.c_h = 200
        self.c_out_img = QImage(self.c_w, self.c_h, QImage.Format.Format_RGB32)
        self.c_temp_buf = (ctypes.c_uint32 * (self.c_w * self.c_h))()
        self.raw_frame_image = None

        self.ambient_enabled = True
        self.brightness = 1.65
        self.black_lift = 0.25
        self.gamma = 1.35
        self.blur_radius = 12
        self.motion_intensity = 0.35
        self.motion_speed = 1.0
        self.tint_enabled = False
        self.tint_color = QColor("#38BDF8")
        self.tint_ratio = 0.20

        self.floating_rim_enabled = True
        self.shadow_enabled = True
        self.shadow_opacity = 0.55
        self.shadow_radius = 20
        self.shadow_offset = 10

        self._shadow_cache_pixmap = None
        self._shadow_cache_pos = QPointF(0, 0)
        self._shadow_dirty = True

        self.c_engine = get_compiled_c_engine()

        self.phase = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self.on_anim_tick)
        self.anim_timer.start()

    def set_children_widgets(self, video_w: QWidget, dock_w: QWidget, list_w: QWidget):
        self.video_widget = video_w
        self.dock_widget = dock_w
        self.playlist_widget = list_w

        self.video_widget.setParent(self)
        self.dock_widget.setParent(self)
        self.playlist_widget.setParent(self)
        self.update_sub_geometries()

    def set_playlist_visibility(self, visible: bool):
        self.playlist_visible = visible
        if self.playlist_widget:
            self.playlist_widget.setVisible(visible)
        self.update_sub_geometries()
        self.update()

    def set_ambient_params(self, cfg: dict):
        self.ambient_enabled = cfg.get("ambient_glow", True)
        self.brightness = cfg.get("ambient_brightness", 1.65)
        self.black_lift = cfg.get("ambient_black_lift", 0.25)
        self.gamma = cfg.get("ambient_gamma", 1.35)
        try:
            self.blur_radius = max(0, min(64, int(round(float(cfg.get("ambient_blur_radius", 12))))))
        except (TypeError, ValueError, OverflowError):
            self.blur_radius = 12
        self.motion_intensity = cfg.get("ambient_motion_intensity", 0.35)
        self.motion_speed = cfg.get("ambient_motion_speed", 1.0)
        self.tint_enabled = cfg.get("ambient_tint_enabled", False)
        self.tint_color = QColor(cfg.get("ambient_tint_color", "#38BDF8"))
        self.tint_ratio = cfg.get("ambient_tint_ratio", 0.20)

        self.aurora_enabled = bool(cfg.get("aurora_enabled", True))
        self.aurora_style = str(cfg.get("aurora_style", "오로라"))
        self.aurora_palette = str(cfg.get("aurora_palette", "청록"))
        self.aurora_intensity = max(0.0, min(1.0, float(cfg.get("aurora_intensity", 0.55))))

        self.particle_system.set_params(
            enabled=bool(cfg.get("particle_enabled", True)),
            p_type=str(cfg.get("particle_type", "소프트 더스트")),
            direction=str(cfg.get("particle_direction", "아래로")),
            palette=str(cfg.get("particle_palette", "에메랄드 틸")),
            density=float(cfg.get("particle_density", 0.45)),
            speed=float(cfg.get("particle_speed", 1.0))
        )

        col1 = cfg.get("border_color1", cfg.get("border_color", "#38BDF8"))
        col2 = cfg.get("border_color2", "#818CF8")

        self.border_system.set_params(
            enabled=bool(cfg.get("border_enabled", True)),
            style=str(cfg.get("border_style", "엣지 글로우")),
            color_mode=str(cfg.get("border_color_mode", "단색")),
            color1=str(col1),
            color2=str(col2),
            anim_mode=str(cfg.get("border_anim_mode", "브리딩 펄스")),
            anim_speed=float(cfg.get("border_anim_speed", 1.0)),
            pulse_depth=float(cfg.get("border_pulse_depth", 0.35)),
            width=int(cfg.get("border_width", 3)),
            margin=int(cfg.get("border_margin", 0)),
            radius=int(cfg.get("border_radius", 0)),
            glow_spread=int(cfg.get("border_glow_spread", 14)),
            opacity=float(cfg.get("border_opacity", 0.75))
        )

        self.floating_rim_enabled = cfg.get("video_floating_rim", True)
        self.shadow_enabled = cfg.get("video_shadow_enabled", True)
        self.shadow_opacity = cfg.get("video_shadow_opacity", 0.55)
        self.shadow_radius = cfg.get("video_shadow_radius", 20)
        self.shadow_offset = cfg.get("video_shadow_offset", 10)

        self._ambient_dirty = True
        self._shadow_dirty = True
        self.update_sub_geometries()
        self.update()
        self.restore_child_stacking()

    def on_anim_tick(self):
        if self.ambient_enabled and self.raw_frame_image and self.motion_intensity > 0.01:
            self.phase += 0.05 * self.motion_speed
        if self.aurora_enabled and self.aurora_style != "없음":
            self.aurora_phase += 0.015

        if self.particle_system.enabled:
            self.particle_system.update(self.width(), self.height())
        if self.border_system.enabled:
            self.border_system.update()

        self.update()

    def set_aspect_ratio(self, aspect: float):
        if aspect > 0.1 and abs(self.video_aspect - aspect) > 0.01:
            self.video_aspect = aspect
            self._shadow_dirty = True
            self.update_sub_geometries()
            self.update()

    def restore_child_stacking(self):
        if not self.video_widget or not self.dock_widget or not self.playlist_widget:
            return
        self.video_widget.raise_()
        if self.dock_widget.isVisible():
            self.dock_widget.raise_()
        if self.playlist_visible and self.playlist_widget.isVisible():
            self.playlist_widget.raise_()

    def update_sub_geometries(self):
        if not self.video_widget or not self.dock_widget or not self.playlist_widget:
            return

        W, H = self.width(), self.height()
        pad = 16

        plist_w = 330 if self.playlist_visible else 0
        if self.playlist_visible:
            self.playlist_widget.setGeometry(W - plist_w - pad, pad, plist_w, H - 2 * pad)

        avail_w = max(100, W - (plist_w + pad * 2 if self.playlist_visible else pad * 2) - 100)
        avail_h = max(100, H - 120 - 100)

        if (avail_w / max(1.0, avail_h)) > self.video_aspect:
            target_h = int(avail_h)
            target_w = int(target_h * self.video_aspect)
        else:
            target_w = int(avail_w)
            target_h = int(target_w / self.video_aspect)

        view_center_x = (W - (plist_w + pad if self.playlist_visible else 0)) // 2
        view_center_y = (H - 50) // 2

        vx = view_center_x - target_w // 2
        vy = view_center_y - target_h // 2
        
        self.video_widget.setGeometry(vx, vy, target_w, target_h)
        self.video_widget.show()

        dock_w = min(880, max(520, target_w + 40))
        dock_h = 76
        dock_x = view_center_x - dock_w // 2
        dock_y = H - dock_h - pad
        self.dock_widget.setGeometry(dock_x, dock_y, dock_w, dock_h)

        self._ambient_dirty = True
        self._shadow_dirty = True
        self.restore_child_stacking()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._shadow_dirty = True
        self._ambient_dirty = True
        self.update_sub_geometries()

    def update_video_frame(self, qimage: QImage):
        if qimage.isNull():
            return
        image = qimage
        if image.format() != QImage.Format.Format_RGB32:
            image = image.convertToFormat(QImage.Format.Format_RGB32)
        self.raw_frame_image = image
        self._ambient_dirty = True
        self.update()

    def _render_ambient_base(self, W: int, H: int, vf_key: tuple):
        if not (self.ambient_enabled and self.raw_frame_image and not self.raw_frame_image.isNull() and self.c_engine):
            return

        sx, sy = self.c_w / float(W), self.c_h / float(H)
        c_vx1, c_vy1 = vf_key[0] * sx, vf_key[1] * sy
        c_vx2, c_vy2 = (vf_key[0] + vf_key[2]) * sx, (vf_key[1] + vf_key[3]) * sy

        out_ptr = ctypes.cast(int(self.c_out_img.bits()), ctypes.POINTER(ctypes.c_uint32))
        src_ptr = ctypes.cast(int(self.raw_frame_image.bits()), ctypes.POINTER(ctypes.c_uint32))

        self.c_engine.c_render_vanishing_perspective(
            out_ptr, self.c_w, self.c_h, src_ptr,
            self.raw_frame_image.width(), self.raw_frame_image.height(),
            c_vx1, c_vy1, c_vx2, c_vy2,
            self.brightness, self.black_lift, self.gamma, 1.0
        )
        self.c_engine.c_apply_optical_gaussian_blur(
            out_ptr, self.c_temp_buf, self.c_w, self.c_h,
            max(0, min(64, int(self.blur_radius)))
        )
        self._ambient_dirty = False

    def _rebuild_shadow_cache(self, vf_rect: QRectF):
        if not self.shadow_enabled or self.shadow_opacity <= 0.01 or vf_rect.width() <= 0 or vf_rect.height() <= 0:
            self._shadow_cache_pixmap = None
            return

        R = float(max(2, self.shadow_radius))
        O = float(self.shadow_offset)
        dx = O * 0.75
        dy = O * 1.0

        pix_w = int(vf_rect.width() + 2 * R)
        pix_h = int(vf_rect.height() + 2 * R)
        if pix_w <= 0 or pix_h <= 0:
            return

        pix = QPixmap(pix_w, pix_h)
        pix.fill(Qt.GlobalColor.transparent)

        sp = QPainter(pix)
        sp.setRenderHint(QPainter.RenderHint.Antialiasing)

        sh_alpha = int(255 * min(1.0, self.shadow_opacity))
        c_sh = QColor(0, 0, 0, sh_alpha)

        def apply_stops(grad):
            grad.setColorAt(0.0, c_sh)
            grad.setColorAt(0.25, QColor(0, 0, 0, int(sh_alpha * 0.72)))
            grad.setColorAt(0.55, QColor(0, 0, 0, int(sh_alpha * 0.32)))
            grad.setColorAt(0.85, QColor(0, 0, 0, int(sh_alpha * 0.08)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        local_s = QRectF(R, R, vf_rect.width(), vf_rect.height())
        sp.fillRect(local_s, c_sh)

        g_top = QLinearGradient(0, local_s.top(), 0, local_s.top() - R)
        apply_stops(g_top)
        sp.fillRect(QRectF(local_s.left(), local_s.top() - R, local_s.width(), R), g_top)

        g_bot = QLinearGradient(0, local_s.bottom(), 0, local_s.bottom() + R)
        apply_stops(g_bot)
        sp.fillRect(QRectF(local_s.left(), local_s.bottom(), local_s.width(), R), g_bot)

        g_left = QLinearGradient(local_s.left(), 0, local_s.left() - R, 0)
        apply_stops(g_left)
        sp.fillRect(QRectF(local_s.left() - R, local_s.top(), R, local_s.height()), g_left)

        g_right = QLinearGradient(local_s.right(), 0, local_s.right() + R, 0)
        apply_stops(g_right)
        sp.fillRect(QRectF(local_s.right(), local_s.top(), R, local_s.height()), g_right)

        gtl = QRadialGradient(local_s.topLeft(), R)
        apply_stops(gtl)
        sp.fillRect(QRectF(local_s.left() - R, local_s.top() - R, R, R), gtl)

        gtr = QRadialGradient(local_s.topRight(), R)
        apply_stops(gtr)
        sp.fillRect(QRectF(local_s.right(), local_s.top() - R, R, R), gtr)

        gbl = QRadialGradient(local_s.bottomLeft(), R)
        apply_stops(gbl)
        sp.fillRect(QRectF(local_s.left() - R, local_s.bottom(), R, R), gbl)

        gbr = QRadialGradient(local_s.bottomRight(), R)
        apply_stops(gbr)
        sp.fillRect(QRectF(local_s.right(), local_s.bottom(), R, R), gbr)

        sp.end()

        self._shadow_cache_pixmap = pix
        self._shadow_cache_pos = QPointF(vf_rect.left() + dx - R, vf_rect.top() + dy - R)
        self._shadow_dirty = False

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        W, H = self.width(), self.height()
        vf_rect = QRectF(self.video_widget.geometry()) if self.video_widget else QRectF(W * 0.15, H * 0.15, W * 0.7, H * 0.7)

        if (self.ambient_enabled and self.video_widget and 
            self.raw_frame_image and not self.raw_frame_image.isNull() and self.c_engine):
            
            vf_key = tuple(self.video_widget.geometry().getRect())
            params_key = (vf_key, self.raw_frame_image.cacheKey(), self.blur_radius, W, H)
            
            if self._ambient_dirty or params_key != self._ambient_params_key:
                self._render_ambient_base(W, H, vf_key)
                self._ambient_params_key = params_key
            
            p.save()
            if self.motion_intensity > 0.01:
                pulse = math.sin(self.phase) * (0.07 * self.motion_intensity)
                p.setOpacity(max(0.1, min(1.0, 1.0 + pulse)))

            p.drawImage(QRectF(0, 0, W, H), self.c_out_img)
            p.restore()

            if self.shadow_enabled and self.shadow_opacity > 0.01:
                if self._shadow_dirty or not self._shadow_cache_pixmap:
                    self._rebuild_shadow_cache(vf_rect)
                if self._shadow_cache_pixmap:
                    p.drawPixmap(self._shadow_cache_pos, self._shadow_cache_pixmap)

            if self.floating_rim_enabled:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(vf_rect.adjusted(-1.0, -1.0, 1.0, 1.0))

            if self.tint_enabled and self.tint_ratio > 0.01:
                p.save()
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
                p.setOpacity(self.tint_ratio * 0.45)
                p.fillRect(0, 0, W, H, self.tint_color)
                p.restore()
        else:
            p.fillRect(0, 0, W, H, QColor(8, 10, 16))

        self._paint_aurora(p, W, H)
        self.particle_system.draw(p, W, H)
        self.border_system.draw(p, W, H)
        p.end()

    def _paint_aurora(self, p: QPainter, w: int, h: int):
        if not self.aurora_enabled or self.aurora_style == "없음" or self.aurora_intensity <= 0.001 or w <= 0 or h <= 0:
            return

        palettes = {
            "청록": [QColor(40, 235, 190), QColor(90, 145, 255), QColor(190, 105, 255)],
            "벚꽃": [QColor(255, 135, 190), QColor(255, 190, 215), QColor(205, 125, 255)],
            "바다": [QColor(35, 180, 255), QColor(50, 115, 245), QColor(90, 235, 230)],
            "보라": [QColor(170, 100, 255), QColor(100, 100, 255), QColor(255, 100, 210)],
            "노을": [QColor(255, 120, 85), QColor(255, 175, 100), QColor(255, 100, 165)],
        }
        colors = palettes.get(self.aurora_palette, palettes["청록"])
        phase = self.aurora_phase
        is_aurora = (self.aurora_style == "오로라")

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)

        band_h = max(90, int(h * (0.42 if is_aurora else 0.30)))
        steps = 28
        step_w = w / steps

        for i, color in enumerate(colors):
            path = QPainterPath()
            base = 0.12 + i * 0.07
            amp = (0.075 if is_aurora else 0.035) * self.aurora_intensity

            path.moveTo(0, h * base)
            for n in range(steps + 1):
                x = n * step_w
                ratio = n / steps
                w1 = math.sin((ratio * math.pi * 2 * (1.15 + i * 0.4)) + phase * 4.0 + i * 1.6)
                w2 = math.sin((ratio * math.pi * 2 * 0.55) - phase * 1.8 + i)
                y = h * base + h * amp * w1 + h * 0.016 * w2
                path.lineTo(x, y)

            path.lineTo(w, band_h)
            path.lineTo(0, band_h)
            path.closeSubpath()

            grad = QLinearGradient(0, h * max(0.0, base - amp), 0, band_h)
            top = QColor(color)
            top.setAlpha(int((75 if is_aurora else 42) * self.aurora_intensity))
            mid = QColor(color)
            mid.setAlpha(int((25 if is_aurora else 18) * self.aurora_intensity))
            end = QColor(color)
            end.setAlpha(0)
            grad.setColorAt(0.0, top)
            grad.setColorAt(0.55, mid)
            grad.setColorAt(1.0, end)

            p.setBrush(grad)
            p.drawPath(path)

        p.restore()