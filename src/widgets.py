import os
import math
import ctypes
from PyQt6.QtWidgets import (
    QSlider, QLabel, QListWidget, QAbstractItemView, QFrame, 
    QToolTip, QWidget, QSizePolicy, QHBoxLayout
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, QImage, QPen, QDragEnterEvent, QDropEvent, QPainterPath
)
from src.c_ambient import get_compiled_c_engine
from src.particles import ParticleSystem


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

        self.c_engine = get_compiled_c_engine()

        self.phase = 0.0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(30)
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
            p_type=str(cfg.get("particle_type", "눈 / 먼지")),
            direction=str(cfg.get("particle_direction", "아래로")),
            palette=str(cfg.get("particle_palette", "화이트")),
            density=float(cfg.get("particle_density", 0.45)),
            speed=float(cfg.get("particle_speed", 1.0))
        )

        self.floating_rim_enabled = cfg.get("video_floating_rim", True)
        self.shadow_enabled = cfg.get("video_shadow_enabled", True)
        self.shadow_opacity = cfg.get("video_shadow_opacity", 0.55)
        self.shadow_radius = cfg.get("video_shadow_radius", 20)
        self.shadow_offset = cfg.get("video_shadow_offset", 10)

        self.update_sub_geometries()
        self.update()
        QTimer.singleShot(0, self.restore_child_stacking)

    def on_anim_tick(self):
        if self.ambient_enabled and self.raw_frame_image and self.motion_intensity > 0.01:
            self.phase += 0.05 * self.motion_speed
        if self.aurora_enabled and self.aurora_style != "없음":
            self.aurora_phase += 0.015
        if self.particle_system.enabled:
            self.particle_system.update(self.width(), self.height())
        self.update()

    def set_aspect_ratio(self, aspect: float):
        if aspect > 0.1 and abs(self.video_aspect - aspect) > 0.01:
            self.video_aspect = aspect
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

        self.restore_child_stacking()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_sub_geometries()
        QTimer.singleShot(0, self.restore_child_stacking)

    def update_video_frame(self, qimage: QImage):
        if qimage.isNull():
            return
        image = qimage
        if image.format() != QImage.Format.Format_RGB32:
            image = image.convertToFormat(QImage.Format.Format_RGB32)
        self.raw_frame_image = image
        self._ambient_dirty = True
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        W, H = self.width(), self.height()

        if (self.ambient_enabled and self.video_widget and 
            self.raw_frame_image and not self.raw_frame_image.isNull() and self.c_engine):
            
            vf_rect = QRectF(self.video_widget.geometry())
            pulse = math.sin(self.phase) * (0.07 * self.motion_intensity)
            cur_bright = max(self.brightness * self.black_lift, self.brightness * (1.0 + pulse))
            vf_key = tuple(self.video_widget.geometry().getRect())
            params_key = (vf_key, self.raw_frame_image.cacheKey(), cur_bright, self.blur_radius, W, H)
            
            if self._ambient_dirty or params_key != self._ambient_params_key:
                sx, sy = self.c_w / float(W), self.c_h / float(H)
                c_vx1, c_vy1 = vf_key[0] * sx, vf_key[1] * sy
                c_vx2, c_vy2 = (vf_key[0] + vf_key[2]) * sx, (vf_key[1] + vf_key[3]) * sy
                out_ptr = ctypes.cast(int(self.c_out_img.bits()), ctypes.POINTER(ctypes.c_uint32))
                src_ptr = ctypes.cast(int(self.raw_frame_image.bits()), ctypes.POINTER(ctypes.c_uint32))
                self.c_engine.c_render_vanishing_perspective(out_ptr, self.c_w, self.c_h, src_ptr, self.raw_frame_image.width(), self.raw_frame_image.height(), c_vx1, c_vy1, c_vx2, c_vy2, cur_bright, self.black_lift, self.gamma, 1.0)
                self.c_engine.c_apply_optical_gaussian_blur(out_ptr, self.c_temp_buf, self.c_w, self.c_h, max(0, min(64, int(self.blur_radius))))
                self._ambient_params_key = params_key
                self._ambient_dirty = False
            
            p.save()
            p.drawImage(QRectF(0, 0, W, H), self.c_out_img)

            if self.shadow_enabled and self.shadow_opacity > 0.01:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                R = float(max(2, self.shadow_radius))
                O = float(self.shadow_offset)

                dx = O * 0.75
                dy = O * 1.0
                S = vf_rect.translated(dx, dy)

                sh_alpha = int(255 * min(1.0, self.shadow_opacity))
                c_sh = QColor(0, 0, 0, sh_alpha)

                def apply_stops(grad):
                    grad.setColorAt(0.0, c_sh)
                    grad.setColorAt(0.25, QColor(0, 0, 0, int(sh_alpha * 0.72)))
                    grad.setColorAt(0.55, QColor(0, 0, 0, int(sh_alpha * 0.32)))
                    grad.setColorAt(0.85, QColor(0, 0, 0, int(sh_alpha * 0.08)))
                    grad.setColorAt(1.0, QColor(0, 0, 0, 0))

                p.fillRect(S, c_sh)

                g_top = QLinearGradient(0, S.top(), 0, S.top() - R)
                apply_stops(g_top)
                p.fillRect(QRectF(S.left(), S.top() - R, S.width(), R), g_top)

                g_bot = QLinearGradient(0, S.bottom(), 0, S.bottom() + R)
                apply_stops(g_bot)
                p.fillRect(QRectF(S.left(), S.bottom(), S.width(), R), g_bot)

                g_left = QLinearGradient(S.left(), 0, S.left() - R, 0)
                apply_stops(g_left)
                p.fillRect(QRectF(S.left() - R, S.top(), R, S.height()), g_left)

                g_right = QLinearGradient(S.right(), 0, S.right() + R, 0)
                apply_stops(g_right)
                p.fillRect(QRectF(S.right(), S.top(), R, S.height()), g_right)

                gtl = QRadialGradient(S.topLeft(), R)
                apply_stops(gtl)
                p.fillRect(QRectF(S.left() - R, S.top() - R, R, R), gtl)

                gtr = QRadialGradient(S.topRight(), R)
                apply_stops(gtr)
                p.fillRect(QRectF(S.right(), S.top() - R, R, R), gtr)

                gbl = QRadialGradient(S.bottomLeft(), R)
                apply_stops(gbl)
                p.fillRect(QRectF(S.left() - R, S.bottom(), R, R), gbl)

                gbr = QRadialGradient(S.bottomRight(), R)
                apply_stops(gbr)
                p.fillRect(QRectF(S.right(), S.bottom(), R, R), gbr)

            if self.floating_rim_enabled:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRect(vf_rect.adjusted(-1.0, -1.0, 1.0, 1.0))

            if self.tint_enabled and self.tint_ratio > 0.01:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
                p.setOpacity(self.tint_ratio * 0.45)
                p.fillRect(0, 0, W, H, self.tint_color)

            p.restore()
        else:
            p.fillRect(0, 0, W, H, QColor(8, 10, 16))

        self._paint_aurora(p, W, H)
        self.particle_system.draw(p, W, H)
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
        for i, color in enumerate(colors):
            path = QPainterPath()
            steps = max(40, min(120, w // 10))
            base = 0.12 + i * 0.07
            amp = (0.075 if is_aurora else 0.035) * self.aurora_intensity

            for n in range(steps + 1):
                x = w * n / steps
                w1 = math.sin((n / steps * math.pi * 2 * (1.15 + i * 0.4)) + phase * 4.0 + i * 1.6)
                w2 = math.sin((n / steps * math.pi * 2 * 0.55) - phase * 1.8 + i)
                y = h * base + h * amp * w1 + h * 0.016 * w2
                if n == 0:
                    path.moveTo(x, y)
                else:
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


class FloatingGlassPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)


class FluidSeekSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.total_seconds = 0.0
        self._hover_progress = 0.0

        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, val: float):
        self._hover_progress = val
        self.update()

    hoverProgress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_duration(self, seconds: float):
        self.total_seconds = max(0.0, seconds)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.pixel_pos_to_val(event.position().x())
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.total_seconds > 0:
            pct = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
            target_sec = int(pct * self.total_seconds)
            time_str = f"{target_sec // 60:02d}:{target_sec % 60:02d}"
            QToolTip.showText(event.globalPosition().toPoint(), time_str, self)
        super().mouseMoveEvent(event)

    def pixel_pos_to_val(self, x):
        ratio = max(0.0, min(1.0, x / max(1, self.width())))
        return int(self.minimum() + ratio * (self.maximum() - self.minimum()))


class FloatingOSD(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 1500):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = 30
            self.move(x, y)
        self.show()
        self.raise_()
        self.timer.start(duration_ms)


class PlaylistWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if os.path.exists(url.toLocalFile())]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def set_full_text(self, text: str):
        self._full_text = text
        self.update_elide()

    def update_elide(self):
        metrics = self.fontMetrics()
        avail_w = max(10, self.width() - 4)
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, avail_w)
        super().setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elide()


class PlaylistItemCard(QWidget):
    OFFSET_DEFAULT = 32
    OFFSET_EXPANDED = 0

    def __init__(self, item, title: str, on_play_callback, parent=None):
        super().__init__(parent)
        self.item = item
        self.on_play_callback = on_play_callback

        self._offset = self.OFFSET_DEFAULT
        self._is_selected = False
        self._is_hovered = False

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(self._offset, 2, 2, 2)
        self.main_layout.setSpacing(0)

        self.inner_card = QFrame()
        self.inner_card.setObjectName("innerPlaylistCard")
        card_layout = QHBoxLayout(self.inner_card)
        card_layout.setContentsMargins(14, 6, 12, 6)
        card_layout.setSpacing(10)

        self.lbl_title = ElidedLabel(title)
        self.lbl_title.setObjectName("card_title")
        card_layout.addWidget(self.lbl_title)

        self.main_layout.addWidget(self.inner_card)

        self.anim = QPropertyAnimation(self, b"offset", self)
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuart)

        self.update_card_style()

    def get_offset(self):
        return self._offset

    def set_offset(self, val: int):
        self._offset = val
        self.main_layout.setContentsMargins(val, 2, 2, 2)
        self.lbl_title.update_elide()

    offset = pyqtProperty(int, get_offset, set_offset)

    def animate_to(self, target: int):
        if self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()
        self.anim.setStartValue(self._offset)
        self.anim.setEndValue(target)
        self.anim.start()

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update_card_style()
        self.animate_to(self.OFFSET_EXPANDED if (self._is_selected or self._is_hovered) else self.OFFSET_DEFAULT)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self.update_card_style()
        self.animate_to(self.OFFSET_EXPANDED)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self.update_card_style()
        if not self._is_selected:
            self.animate_to(self.OFFSET_DEFAULT)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            lw = self.item.listWidget()
            if lw:
                lw.setCurrentItem(self.item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_play_callback:
            self.on_play_callback(self.item)
        super().mouseDoubleClickEvent(event)

    def update_card_style(self):
        if self._is_selected:
            self.inner_card.setProperty("state", "selected")
        elif self._is_hovered:
            self.inner_card.setProperty("state", "hover")
        else:
            self.inner_card.setProperty("state", "normal")
        self.inner_card.style().unpolish(self.inner_card)
        self.inner_card.style().polish(self.inner_card)