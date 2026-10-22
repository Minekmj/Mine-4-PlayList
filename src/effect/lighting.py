import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPolygonF
)


class StudioLightingSystem:
    def __init__(self):
        self.enabled = False
        self.style = "탑다운 시네마 림"
        self.color = QColor("#E0F2FE")
        self.intensity = 0.45
        self.beam_spread = 45.0
        self.sway_speed = 1.0
        self.video_reactive = True

        self.phase = 0.0
        self.reactive_luma = 0.0

    def set_params(
        self,
        enabled: bool,
        style: str,
        color: str,
        intensity: float,
        beam_spread: float,
        sway_speed: float,
        video_reactive: bool,
    ):
        self.enabled = enabled
        self.style = style
        self.color = QColor(color) if color else QColor("#E0F2FE")
        self.intensity = max(0.0, min(1.0, intensity))
        self.beam_spread = max(15.0, min(80.0, beam_spread))
        self.sway_speed = max(0.1, min(3.0, sway_speed))
        self.video_reactive = video_reactive

    def update(self, video_react: dict | None = None):
        if not self.enabled:
            return

        self.phase = (self.phase + 0.032 * self.sway_speed) % (math.pi * 2)

        if video_react and self.video_reactive:
            target_luma = video_react.get("luma", 0.0) * 0.75 + video_react.get("flash", 0.0) * 1.2
            self.reactive_luma += (target_luma - self.reactive_luma) * 0.22
        else:
            self.reactive_luma += (0.0 - self.reactive_luma) * 0.1

    def draw(self, p: QPainter, w: int, h: int, video_rect: QRectF | None = None):
        if not self.enabled or w <= 0 or h <= 0 or self.intensity <= 0.001 or self.style == "없음":
            return

        vr = video_rect if (video_rect and video_rect.isValid() and video_rect.width() > 10) else QRectF(w * 0.15, h * 0.15, w * 0.7, h * 0.7)

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)

        mult = 1.0 + (self.reactive_luma * 0.85 if self.video_reactive else 0.0)
        alpha = max(0, min(255, int(255 * self.intensity * mult)))
        col = QColor(self.color.red(), self.color.green(), self.color.blue(), alpha)

        if self.style == "탑다운 시네마 림":
            self._draw_top_cinema_rim(p, w, h, vr, col)
        elif self.style == "듀얼 스포트라이트":
            self._draw_dual_spotlights(p, w, h, vr, col)
        elif self.style == "백라이트 글로우":
            self._draw_backlight_aura(p, w, h, vr, col)
        elif self.style == "사이드 플레어":
            self._draw_side_flares(p, w, h, vr, col)

        p.restore()

    def _draw_top_cinema_rim(self, p: QPainter, w: int, h: int, vr: QRectF, col: QColor):
        p.setPen(Qt.PenStyle.NoPen)
        cx = vr.center().x()
        target_top = vr.top()
        radius_x = (vr.width() * 0.55) * (self.beam_spread / 40.0)
        radius_y = max(60.0, target_top + 40.0)

        center_pt = QPointF(cx, target_top * 0.25)
        grad = QRadialGradient(center_pt, radius_x)
        grad.setFocalPoint(center_pt)
        grad.setColorAt(0.0, col)
        grad.setColorAt(0.40, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.45)))
        grad.setColorAt(0.75, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.12)))
        grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))

        p.setBrush(grad)
        p.drawRect(QRectF(cx - radius_x, 0, radius_x * 2, target_top + 80.0))

    def _draw_dual_spotlights(self, p: QPainter, w: int, h: int, vr: QRectF, col: QColor):
        p.setPen(Qt.PenStyle.NoPen)
        sway = math.sin(self.phase) * (vr.width() * 0.035)
        spread = (vr.width() * 0.35) * (self.beam_spread / 45.0)

        origin_lx = vr.left() + vr.width() * 0.1
        target_lx = vr.left() + vr.width() * 0.25 + sway
        poly_left = QPolygonF([
            QPointF(origin_lx, -10),
            QPointF(target_lx - spread * 0.5, vr.bottom() + 10),
            QPointF(target_lx + spread * 0.5, vr.bottom() + 10)
        ])
        g_left = QLinearGradient(origin_lx, -10, target_lx, vr.bottom())
        g_left.setColorAt(0.0, col)
        g_left.setColorAt(0.45, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.35)))
        g_left.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        p.setBrush(g_left)
        p.drawPolygon(poly_left)

        origin_rx = vr.right() - vr.width() * 0.1
        target_rx = vr.right() - vr.width() * 0.25 - sway
        poly_right = QPolygonF([
            QPointF(origin_rx, -10),
            QPointF(target_rx - spread * 0.5, vr.bottom() + 10),
            QPointF(target_rx + spread * 0.5, vr.bottom() + 10)
        ])
        g_right = QLinearGradient(origin_rx, -10, target_rx, vr.bottom())
        g_right.setColorAt(0.0, col)
        g_right.setColorAt(0.45, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.35)))
        g_right.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        p.setBrush(g_right)
        p.drawPolygon(poly_right)

    def _draw_backlight_aura(self, p: QPainter, w: int, h: int, vr: QRectF, col: QColor):
        p.setPen(Qt.PenStyle.NoPen)
        cx = vr.center().x()
        cy = vr.center().y()
        pulse = 1.0 + math.sin(self.phase * 1.5) * 0.06
        radius = (max(vr.width(), vr.height()) * 0.65) * (self.beam_spread / 45.0) * pulse

        grad = QRadialGradient(QPointF(cx, cy), radius)
        grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.65)))
        grad.setColorAt(0.50, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.22)))
        grad.setColorAt(0.85, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.05)))
        grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))

        p.setBrush(grad)
        p.drawRect(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

    def _draw_side_flares(self, p: QPainter, w: int, h: int, vr: QRectF, col: QColor):
        p.setPen(Qt.PenStyle.NoPen)
        cy = vr.center().y()
        flare_w = (vr.width() * 0.4) * (self.beam_spread / 45.0)
        flare_h = vr.height() * 0.85

        left_g = QLinearGradient(0, cy, flare_w, cy)
        left_g.setColorAt(0.0, col)
        left_g.setColorAt(0.40, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.35)))
        left_g.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        p.setBrush(left_g)
        p.drawRect(QRectF(0, cy - flare_h * 0.5, flare_w, flare_h))

        right_g = QLinearGradient(w, cy, w - flare_w, cy)
        right_g.setColorAt(0.0, col)
        right_g.setColorAt(0.40, QColor(col.red(), col.green(), col.blue(), int(col.alpha() * 0.35)))
        right_g.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        p.setBrush(right_g)
        p.drawRect(QRectF(w - flare_w, cy - flare_h * 0.5, flare_w, flare_h))