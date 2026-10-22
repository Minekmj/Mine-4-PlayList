import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient, QRadialGradient,
    QConicalGradient, QPainterPath, QPolygonF, QBrush, QImage
)


class ScreenBorderSystem:
    def __init__(self):
        self.enabled = True
        self.style = "엣지 글로우"
        self.color_mode = "단색"
        self.color1 = QColor("#38BDF8")
        self.color2 = QColor("#818CF8")
        self.anim_mode = "브리딩 펄스"
        self.anim_speed = 1.0
        self.pulse_depth = 0.35
        self.width = 3
        self.margin = 0
        self.radius = 0
        self.glow_spread = 14
        self.opacity = 0.75

        self.phase = 0.0
        self.sweep_angle = 0.0
        self.flicker_val = 1.0

        self._scanline_brush = self._create_scanline_brush()

    def _create_scanline_brush(self) -> QBrush:
        pattern = QImage(1, 4, QImage.Format.Format_ARGB32_Premultiplied)
        pattern.fill(0)
        pattern.setPixelColor(0, 0, QColor(0, 0, 0, 0))
        pattern.setPixelColor(0, 1, QColor(0, 0, 0, 0))
        pattern.setPixelColor(0, 2, QColor(255, 255, 255, 30))
        pattern.setPixelColor(0, 3, QColor(255, 255, 255, 30))
        return QBrush(pattern)

    def set_params(
        self,
        enabled: bool,
        style: str,
        color_mode: str,
        color1: str,
        color2: str,
        anim_mode: str,
        anim_speed: float,
        pulse_depth: float,
        width: int,
        margin: int,
        radius: int,
        glow_spread: int,
        opacity: float,
    ):
        self.enabled = enabled
        self.style = style
        self.color_mode = color_mode
        self.color1 = QColor(color1) if color1 else QColor("#38BDF8")
        self.color2 = QColor(color2) if color2 else QColor("#818CF8")
        self.anim_mode = anim_mode
        self.anim_speed = max(0.1, min(3.0, anim_speed))
        self.pulse_depth = max(0.0, min(0.8, pulse_depth))
        self.width = max(1, min(24, width))
        self.margin = max(0, min(60, margin))
        self.radius = max(0, min(80, radius))
        self.glow_spread = max(0, min(40, glow_spread))
        self.opacity = max(0.0, min(1.0, opacity))

    def update(self):
        if not self.enabled:
            return

        dt = 0.04 * self.anim_speed
        self.phase = (self.phase + dt) % (math.pi * 2)
        self.sweep_angle = (self.sweep_angle + 2.4 * self.anim_speed) % 360.0

        if self.anim_mode == "네온 플리커":
            flicker_noise = math.sin(self.phase * 11.2) * math.cos(self.phase * 19.4)
            self.flicker_val = 0.65 + 0.35 * max(0.0, flicker_noise)
        else:
            self.flicker_val = 1.0

    def _get_active_alpha(self, base_alpha: int) -> int:
        mult = 1.0
        if self.anim_mode == "브리딩 펄스":
            mult = 1.0 - (self.pulse_depth * 0.5) + (math.sin(self.phase * 2.0) * 0.5 * self.pulse_depth)
        elif self.anim_mode == "네온 플리커":
            mult = self.flicker_val

        final_a = int(base_alpha * self.opacity * max(0.05, min(1.0, mult)))
        return max(0, min(255, final_a))

    def _create_brush_gradient(self, w: int, h: int, alpha: int) -> QLinearGradient | QConicalGradient:
        cx, cy = w * 0.5, h * 0.5

        if self.color_mode == "스펙트럼":
            cg = QConicalGradient(cx, cy, self.sweep_angle)
            hues = [
                (0.0, 0), (0.16, 60), (0.33, 120), (0.50, 180),
                (0.66, 240), (0.83, 300), (1.0, 360)
            ]
            for pos, h_val in hues:
                sc = QColor.fromHsv(h_val, 215, 255, alpha)
                cg.setColorAt(pos, sc)
            return cg

        if self.color_mode == "듀얼 그라디언트":
            c1 = QColor(self.color1.red(), self.color1.green(), self.color1.blue(), alpha)
            c2 = QColor(self.color2.red(), self.color2.green(), self.color2.blue(), alpha)
        else:
            c1 = QColor(self.color1.red(), self.color1.green(), self.color1.blue(), alpha)
            c2 = c1

        if self.anim_mode == "로테이팅 체이스":
            rad = math.radians(self.sweep_angle)
            diag = math.hypot(w, h) * 0.65
            dx = math.cos(rad) * diag
            dy = math.sin(rad) * diag
            lg = QLinearGradient(cx - dx, cy - dy, cx + dx, cy + dy)
            if self.color_mode == "단색":
                c_light = QColor(min(255, c1.red() + 60), min(255, c1.green() + 60), min(255, c1.blue() + 60), alpha)
                c_dark = QColor(c1.red(), c1.green(), c1.blue(), max(10, int(alpha * 0.28)))
                lg.setColorAt(0.0, c_dark)
                lg.setColorAt(0.5, c_light)
                lg.setColorAt(1.0, c_dark)
            else:
                lg.setColorAt(0.0, c1)
                lg.setColorAt(0.5, c2)
                lg.setColorAt(1.0, c1)
            return lg

        lg = QLinearGradient(0, 0, w, h)
        lg.setColorAt(0.0, c1)
        lg.setColorAt(1.0, c2)
        return lg

    def _create_styled_pen(self, w: int, h: int, pen_width: float, alpha: int) -> QPen:
        grad = self._create_brush_gradient(w, h, alpha)
        pen = QPen(grad, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        return pen

    def draw(self, p: QPainter, w: int, h: int):
        if not self.enabled or w <= 0 or h <= 0 or self.opacity <= 0.001 or self.style == "없음":
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        active_alpha = self._get_active_alpha(255)

        if self.style == "엣지 글로우":
            self._draw_edge_glow(p, w, h, active_alpha)
        elif self.style == "미니멀 보더":
            self._draw_minimal_border(p, w, h, active_alpha)
        elif self.style == "더블 라인":
            self._draw_double_line(p, w, h, active_alpha)
        elif self.style == "테크니컬 브래킷":
            self._draw_technical_bracket(p, w, h, active_alpha)
        elif self.style == "인셋 프레임":
            self._draw_inset_frame(p, w, h, active_alpha)
        elif self.style == "스튜디오 챔퍼":
            self._draw_studio_chamfer(p, w, h, active_alpha)
        elif self.style == "도트 매트릭스":
            self._draw_dot_matrix(p, w, h, active_alpha)
        elif self.style == "사이버 그루브":
            self._draw_cyber_groove(p, w, h, active_alpha)
        elif self.style == "옵티컬 비네트":
            self._draw_optical_vignette(p, w, h, active_alpha)
        elif self.style == "시네마틱 레터 림":
            self._draw_cinematic_rim(p, w, h, active_alpha)
        elif self.style == "코너 크로스":
            self._draw_corner_cross(p, w, h, active_alpha)
        elif self.style == "게이머 네온":
            self._draw_gamer_neon(p, w, h, active_alpha)

        p.restore()

    def _draw_edge_glow(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        pulse_spread = 0.0
        if self.anim_mode == "브리딩 펄스":
            pulse_spread = math.sin(self.phase * 2.0) * (self.glow_spread * 0.25 * self.pulse_depth)
        spread = float(max(4, self.glow_spread + pulse_spread))
        r = float(self.radius)

        rect = QRectF(m, m, w - m * 2, h - m * 2)
        path = QPainterPath()
        path.addRoundedRect(rect, r, r)

        p.setBrush(Qt.BrushStyle.NoBrush)
        steps = 2
        for i in range(steps, 0, -1):
            cur_w = float(self.width) + (spread * (i / steps))
            glow_a = max(0, min(255, int(alpha * (1.0 - (i / (steps + 1))) * 0.42)))
            pen = self._create_styled_pen(w, h, cur_w, glow_a)
            p.setPen(pen)
            p.drawPath(path)

        core_pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(core_pen)
        p.drawPath(path)

    def _draw_minimal_border(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        half_w = float(self.width) * 0.5
        rect = QRectF(m + half_w, m + half_w, w - (m + half_w) * 2, h - (m + half_w) * 2)
        r = float(self.radius)

        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawRoundedRect(rect, r, r)

    def _draw_double_line(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        half_w = float(self.width) * 0.5
        rect1 = QRectF(m + half_w, m + half_w, w - (m + half_w) * 2, h - (m + half_w) * 2)
        r1 = float(self.radius)

        p.setBrush(Qt.BrushStyle.NoBrush)
        pen1 = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen1)
        p.drawRoundedRect(rect1, r1, r1)

        offset = max(4.0, float(self.width) + 2.0)
        rect2 = rect1.adjusted(offset, offset, -offset, -offset)
        r2 = max(0.0, r1 - offset)
        if rect2.width() > 10 and rect2.height() > 10:
            pen2 = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.5))))
            p.setPen(pen2)
            p.drawRoundedRect(rect2, r2, r2)

    def _draw_technical_bracket(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + 2.0
        arm = min(72.0, max(24.0, min(w, h) * 0.08))
        thick = float(self.width)
        p.setBrush(Qt.BrushStyle.NoBrush)

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.22))))
        sub_pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(sub_pen)
        p.drawRect(QRectF(m + 4, m + 4, w - (m + 4) * 2, h - (m + 4) * 2))

        pen = self._create_styled_pen(w, h, thick, alpha)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        p.setPen(pen)

        p.drawLine(QPointF(m, m + arm), QPointF(m, m))
        p.drawLine(QPointF(m, m), QPointF(m + arm, m))
        p.drawLine(QPointF(w - m - arm, m), QPointF(w - m, m))
        p.drawLine(QPointF(w - m, m), QPointF(w - m, m + arm))
        p.drawLine(QPointF(m, h - m - arm), QPointF(m, h - m))
        p.drawLine(QPointF(m, h - m), QPointF(m + arm, h - m))
        p.drawLine(QPointF(w - m - arm, h - m), QPointF(w - m, h - m))
        p.drawLine(QPointF(w - m, h - m), QPointF(w - m, h - m - arm))

        accent_sz = max(4.0, thick + 2.0)
        p.setPen(Qt.PenStyle.NoPen)
        grad = self._create_brush_gradient(w, h, alpha)
        p.setBrush(grad)
        p.drawRect(QRectF(m - thick * 0.5, m - thick * 0.5, accent_sz, accent_sz))
        p.drawRect(QRectF(w - m - accent_sz + thick * 0.5, m - thick * 0.5, accent_sz, accent_sz))
        p.drawRect(QRectF(m - thick * 0.5, h - m - accent_sz + thick * 0.5, accent_sz, accent_sz))
        p.drawRect(QRectF(w - m - accent_sz + thick * 0.5, h - m - accent_sz + thick * 0.5, accent_sz, accent_sz))

        cx = w * 0.5
        p.setPen(self._create_styled_pen(w, h, 1.0, alpha))
        p.drawLine(QPointF(cx - 24, m), QPointF(cx + 24, m))
        p.drawLine(QPointF(cx, m - 3), QPointF(cx, m + 3))
        p.drawLine(QPointF(cx - 24, h - m), QPointF(cx + 24, h - m))
        p.drawLine(QPointF(cx, h - m - 3), QPointF(cx, h - m + 3))

    def _draw_inset_frame(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(max(6, self.margin))
        r = float(max(4, self.radius))
        rect = QRectF(m, m, w - m * 2, h - m * 2)

        shadow_c = QColor(0, 0, 0, max(0, min(255, int(alpha * 0.55))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(shadow_c, float(self.width + 3), Qt.PenStyle.SolidLine))
        p.drawRoundedRect(rect.translated(0, 2.5), r, r)

        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawRoundedRect(rect, r, r)

        hi_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.45))))
        p.setPen(hi_pen)
        p.drawRoundedRect(rect.adjusted(2.0, 2.0, -2.0, -2.0), max(0.0, r - 2.0), max(0.0, r - 2.0))

    def _draw_studio_chamfer(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + float(self.width) * 0.5
        c = max(8.0, float(self.radius) if self.radius > 0 else 16.0)

        poly = QPolygonF([
            QPointF(m + c, m),
            QPointF(w - m - c, m),
            QPointF(w - m, m + c),
            QPointF(w - m, h - m - c),
            QPointF(w - m - c, h - m),
            QPointF(m + c, h - m),
            QPointF(m, h - m - c),
            QPointF(m, m + c),
        ])

        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawPolygon(poly)

        inner_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.35))))
        p.setPen(inner_pen)
        m2 = m + 4.0
        c2 = max(4.0, c - 3.0)
        poly_inner = QPolygonF([
            QPointF(m2 + c2, m2),
            QPointF(w - m2 - c2, m2),
            QPointF(w - m2, m2 + c2),
            QPointF(w - m2, h - m2 - c2),
            QPointF(w - m2 - c2, h - m2),
            QPointF(m2 + c2, h - m2),
            QPointF(m2, h - m2 - c2),
            QPointF(m2, m2 + c2),
        ])
        p.drawPolygon(poly_inner)

    def _draw_dot_matrix(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + 4.0
        dot_sz = max(2.0, float(self.width) * 0.8)
        step = 16.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._create_brush_gradient(w, h, alpha))

        x = m
        while x <= w - m:
            p.drawRect(QRectF(x - dot_sz * 0.5, m - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(x - dot_sz * 0.5, h - m - dot_sz * 0.5, dot_sz, dot_sz))
            x += step

        y = m + step
        while y < h - m:
            p.drawRect(QRectF(m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(w - m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
            y += step

    def _draw_cyber_groove(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + 2.0
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        gap = 40.0
        cx, cy = w * 0.5, h * 0.5

        p.drawLine(QPointF(m, m), QPointF(cx - gap, m))
        p.drawLine(QPointF(cx + gap, m), QPointF(w - m, m))
        p.drawLine(QPointF(m, h - m), QPointF(cx - gap, h - m))
        p.drawLine(QPointF(cx + gap, h - m), QPointF(w - m, h - m))
        p.drawLine(QPointF(m, m), QPointF(m, cy - gap))
        p.drawLine(QPointF(m, cy + gap), QPointF(m, h - m))
        p.drawLine(QPointF(w - m, m), QPointF(w - m, cy - gap))
        p.drawLine(QPointF(w - m, cy + gap), QPointF(w - m, h - m))

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.4))))
        p.setPen(sub_pen)
        p.drawLine(QPointF(cx - gap * 0.6, m), QPointF(cx + gap * 0.6, m))
        p.drawLine(QPointF(cx - gap * 0.6, h - m), QPointF(cx + gap * 0.6, h - m))
        p.drawLine(QPointF(m, cy - gap * 0.6), QPointF(m, cy + gap * 0.6))
        p.drawLine(QPointF(w - m, cy - gap * 0.6), QPointF(w - m, cy + gap * 0.6))

    def _draw_optical_vignette(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        rect = QRectF(m, m, w - m * 2, h - m * 2)
        r = float(self.radius)

        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawRoundedRect(rect, r, r)

        inner_rect = QRectF(m + 4.0, m + 4.0, w - (m + 4.0) * 2, h - (m + 4.0) * 2)
        p.fillRect(inner_rect, self._scanline_brush)

        grad = QRadialGradient(QPointF(w * 0.5, h * 0.5), max(w, h) * 0.65)
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.70, QColor(0, 0, 0, int(alpha * 0.10)))
        grad.setColorAt(1.0, QColor(0, 0, 0, int(alpha * 0.48)))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, w, h)

    def _draw_cinematic_rim(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        bar_h = max(3.0, float(self.width) * 1.5)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._create_brush_gradient(w, h, alpha))
        p.drawRect(QRectF(m, m, w - m * 2, bar_h))
        p.drawRect(QRectF(m, h - m - bar_h, w - m * 2, bar_h))

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.25))))
        p.setPen(sub_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(m, m + bar_h), QPointF(m, h - m - bar_h))
        p.drawLine(QPointF(w - m, m + bar_h), QPointF(w - m, h - m - bar_h))

    def _draw_corner_cross(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + 8.0
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        cs = 16.0
        corners = [
            (m, m),
            (w - m, m),
            (m, h - m),
            (w - m, h - m)
        ]
        for cx, cy in corners:
            p.drawLine(QPointF(cx - cs, cy), QPointF(cx + cs, cy))
            p.drawLine(QPointF(cx, cy - cs), QPointF(cx, cy + cs))

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.35))))
        p.setPen(sub_pen)
        p.drawRect(QRectF(m, m, w - m * 2, h - m * 2))

    def _draw_gamer_neon(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        r = float(self.radius)
        rect = QRectF(m, m, w - m * 2, h - m * 2)

        p.setBrush(Qt.BrushStyle.NoBrush)

        outer_pen = self._create_styled_pen(w, h, float(self.width * 2.5), max(0, min(255, int(alpha * 0.25))))
        p.setPen(outer_pen)
        p.drawRoundedRect(rect, r, r)

        core_pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(core_pen)
        p.drawRoundedRect(rect, r, r)

        corner_len = min(40.0, max(14.0, min(w, h) * 0.05))
        accent_pen = QPen(QColor(255, 255, 255, alpha), float(self.width + 1.0))
        p.setPen(accent_pen)
        p.drawLine(QPointF(m, m), QPointF(m + corner_len, m))
        p.drawLine(QPointF(m, m), QPointF(m, m + corner_len))
        p.drawLine(QPointF(w - m, m), QPointF(w - m - corner_len, m))
        p.drawLine(QPointF(w - m, m), QPointF(w - m, m + corner_len))
        p.drawLine(QPointF(m, h - m), QPointF(m + corner_len, h - m))
        p.drawLine(QPointF(m, h - m), QPointF(m, h - m - corner_len))
        p.drawLine(QPointF(w - m, h - m), QPointF(w - m - corner_len, h - m))
        p.drawLine(QPointF(w - m, h - m), QPointF(w - m, h - m - corner_len))