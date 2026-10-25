import math
from collections import OrderedDict
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient,
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
        self._gradient_cache = OrderedDict()
        self._path_cache = OrderedDict()

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
        angle = int(round(self.sweep_angle / 5.0) * 5) % 360 if self.color_mode == "스펙트럼" or self.anim_mode == "로테이팅 체이스" else 0
        key = (w, h, alpha, self.color_mode, self.color1.rgba(), self.color2.rgba(), self.anim_mode, angle)
        cached = self._gradient_cache.get(key)
        if cached is not None:
            self._gradient_cache.move_to_end(key)
            return cached
        grad = self._build_brush_gradient(w, h, alpha, angle)
        self._gradient_cache[key] = grad
        if len(self._gradient_cache) > 96:
            self._gradient_cache.popitem(last=False)
        return grad

    def _build_brush_gradient(self, w: int, h: int, alpha: int, cached_angle: int) -> QLinearGradient | QConicalGradient:
        cx, cy = w * 0.5, h * 0.5

        if self.color_mode == "스펙트럼":
            cg = QConicalGradient(cx, cy, cached_angle)
            hues = [
                (0.0, 0),
                (0.16, 42),
                (0.33, 85),
                (0.50, 128),
                (0.66, 170),
                (0.83, 212),
                (1.0, 255)
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
            rad = math.radians(cached_angle)
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

    def _get_base_rounded_path(self, w: int, h: int) -> QPainterPath:
        half_w = float(self.width) * 0.5
        m = float(self.margin) + half_w
        r_outer = float(self.radius)
        r = max(0.0, r_outer - half_w) if r_outer > 0.5 else 0.0
        r = min(r, (float(w) - m * 2.0) / 2.0, (float(h) - m * 2.0) / 2.0)

        path_key = (w, h, int(self.margin * 10), int(self.width * 10), int(r * 10))
        path = self._path_cache.get(path_key)
        if path is None:
            path = QPainterPath()
            if r > 0.5:
                path.addRoundedRect(QRectF(m, m, float(w) - m * 2.0, float(h) - m * 2.0), r, r)
            else:
                path.addRect(QRectF(m, m, float(w) - m * 2.0, float(h) - m * 2.0))
            self._path_cache[path_key] = path
            if len(self._path_cache) > 16:
                self._path_cache.popitem(last=False)
        else:
            self._path_cache.move_to_end(path_key)
        return path

    def _create_curved_corner_brackets(self, w: float, h: float, m: float, r: float, arm: float) -> list[QPainterPath]:
        brackets = []
        half_w = float(self.width) * 0.5
        x_l = float(m) + half_w
        y_t = float(m) + half_w
        x_r = float(w) - x_l
        y_b = float(h) - y_t
        max_r = min((x_r - x_l) / 2.0, (y_b - y_t) / 2.0)
        r_c = max(0.0, min(float(r) - half_w, max_r)) if r > 0.5 else 0.0

        p_tl = QPainterPath()
        if r_c > 0.5:
            p_tl.moveTo(x_l + r_c + arm, y_t)
            p_tl.lineTo(x_l + r_c, y_t)
            p_tl.arcTo(QRectF(x_l, y_t, 2.0 * r_c, 2.0 * r_c), 90.0, 90.0)
            p_tl.lineTo(x_l, y_t + r_c + arm)
        else:
            p_tl.moveTo(x_l + arm, y_t)
            p_tl.lineTo(x_l, y_t)
            p_tl.lineTo(x_l, y_t + arm)
        brackets.append(p_tl)

        p_tr = QPainterPath()
        if r_c > 0.5:
            p_tr.moveTo(x_r - r_c - arm, y_t)
            p_tr.lineTo(x_r - r_c, y_t)
            p_tr.arcTo(QRectF(x_r - 2.0 * r_c, y_t, 2.0 * r_c, 2.0 * r_c), 90.0, -90.0)
            p_tr.lineTo(x_r, y_t + r_c + arm)
        else:
            p_tr.moveTo(x_r - arm, y_t)
            p_tr.lineTo(x_r, y_t)
            p_tr.lineTo(x_r, y_t + arm)
        brackets.append(p_tr)

        p_br = QPainterPath()
        if r_c > 0.5:
            p_br.moveTo(x_r, y_b - r_c - arm)
            p_br.lineTo(x_r, y_b - r_c)
            p_br.arcTo(QRectF(x_r - 2.0 * r_c, y_b - 2.0 * r_c, 2.0 * r_c, 2.0 * r_c), 0.0, -90.0)
            p_br.lineTo(x_r - r_c - arm, y_b)
        else:
            p_br.moveTo(x_r, y_b - arm)
            p_br.lineTo(x_r, y_b)
            p_br.lineTo(x_r - arm, y_b)
        brackets.append(p_br)

        p_bl = QPainterPath()
        if r_c > 0.5:
            p_bl.moveTo(x_l, y_b - r_c - arm)
            p_bl.lineTo(x_l, y_b - r_c)
            p_bl.arcTo(QRectF(x_l, y_b - 2.0 * r_c, 2.0 * r_c, 2.0 * r_c), 180.0, 90.0)
            p_bl.lineTo(x_l + r_c + arm, y_b)
        else:
            p_bl.moveTo(x_l, y_b - arm)
            p_bl.lineTo(x_l, y_b)
            p_bl.lineTo(x_l + arm, y_b)
        brackets.append(p_bl)

        return brackets

    def draw(self, p: QPainter, w: int, h: int):
        if not self.enabled or w <= 0 or h <= 0 or self.opacity <= 0.001 or self.style == "없음":
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
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
        pulse_spread = 0.0
        if self.anim_mode == "브리딩 펄스":
            pulse_spread = math.sin(self.phase * 2.0) * (self.glow_spread * 0.25 * self.pulse_depth)
        spread = float(max(4.0, self.glow_spread + pulse_spread))
        path = self._get_base_rounded_path(w, h)

        p.setBrush(Qt.BrushStyle.NoBrush)
        steps = 8
        base_w = float(self.width)
        for i in range(steps, 0, -1):
            ratio = i / float(steps)
            cur_w = base_w + spread * ratio * 2.2
            glow_a = max(0, min(255, int(alpha * math.exp(-3.0 * (ratio ** 2)) * 0.42)))
            if glow_a > 0:
                pen = self._create_styled_pen(w, h, cur_w, glow_a)
                p.setPen(pen)
                p.drawPath(path)

        core_pen = self._create_styled_pen(w, h, base_w, alpha)
        p.setPen(core_pen)
        p.drawPath(path)

    def _draw_minimal_border(self, p: QPainter, w: int, h: int, alpha: int):
        path = self._get_base_rounded_path(w, h)
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawPath(path)

    def _draw_double_line(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        r = float(self.radius)
        p.setBrush(Qt.BrushStyle.NoBrush)

        path1 = self._get_base_rounded_path(w, h)
        pen1 = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen1)
        p.drawPath(path1)

        offset = max(4.0, float(self.width) + 2.0)
        m2 = m + offset
        r2 = max(0.0, r - offset)
        if w - m2 * 2 > 10 and h - m2 * 2 > 10:
            path2 = QPainterPath()
            if r2 > 0.5:
                path2.addRoundedRect(QRectF(m2, m2, w - m2 * 2, h - m2 * 2), r2, r2)
            else:
                path2.addRect(QRectF(m2, m2, w - m2 * 2, h - m2 * 2))
            pen2 = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.5))))
            p.setPen(pen2)
            p.drawPath(path2)

    def _draw_technical_bracket(self, p: QPainter, w: int, h: int, alpha: int):
        thick = float(self.width)
        half_w = thick * 0.5
        m_inner = float(self.margin) + half_w + 3.0
        r_inner = max(0.0, float(self.radius) - half_w - 3.0)
        arm = min(72.0, max(24.0, min(w, h) * 0.08))
        p.setBrush(Qt.BrushStyle.NoBrush)

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.25))))
        sub_pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(sub_pen)
        p_inner = QPainterPath()
        if r_inner > 0.5:
            p_inner.addRoundedRect(QRectF(m_inner, m_inner, float(w) - m_inner * 2.0, float(h) - m_inner * 2.0), r_inner, r_inner)
        else:
            p_inner.addRect(QRectF(m_inner, m_inner, float(w) - m_inner * 2.0, float(h) - m_inner * 2.0))
        p.drawPath(p_inner)

        pen = self._create_styled_pen(w, h, thick, alpha)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for b_path in self._create_curved_corner_brackets(w, h, self.margin, self.radius, arm):
            p.drawPath(b_path)

        accent_sz = max(4.0, thick + 2.0)
        half_acc = accent_sz * 0.5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._create_brush_gradient(w, h, alpha))

        x_l = float(self.margin) + half_w
        y_t = float(self.margin) + half_w
        x_r = float(w) - x_l
        y_b = float(h) - y_t
        r_c = max(0.0, float(self.radius) - half_w) if self.radius > 0.5 else 0.0
        diag_off = r_c * 0.2929 if r_c > 0.5 else 0.0

        corners = [
            QPointF(x_l + diag_off, y_t + diag_off),
            QPointF(x_r - diag_off, y_t + diag_off),
            QPointF(x_r - diag_off, y_b - diag_off),
            QPointF(x_l + diag_off, y_b - diag_off)
        ]
        for pt in corners:
            p.drawRect(QRectF(pt.x() - half_acc, pt.y() - half_acc, accent_sz, accent_sz))

        cx, cy = float(w) * 0.5, float(h) * 0.5
        top_y = float(self.margin) + half_w
        bot_y = float(h) - top_y
        p.setPen(self._create_styled_pen(w, h, 1.0, alpha))
        p.drawLine(QPointF(cx - 24, top_y), QPointF(cx + 24, top_y))
        p.drawLine(QPointF(cx, top_y - 3), QPointF(cx, top_y + 3))
        p.drawLine(QPointF(cx - 24, bot_y), QPointF(cx + 24, bot_y))
        p.drawLine(QPointF(cx, bot_y - 3), QPointF(cx, bot_y + 3))

    def _draw_inset_frame(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(max(6, self.margin))
        r = float(max(0, self.radius))
        path = self._get_base_rounded_path(w, h)

        shadow_c = QColor(0, 0, 0, max(0, min(255, int(alpha * 0.55))))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(shadow_c, float(self.width + 3), Qt.PenStyle.SolidLine))
        p.save()
        p.translate(0, 2.5)
        p.drawPath(path)
        p.restore()

        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawPath(path)

        hi_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.45))))
        p.setPen(hi_pen)
        inner_r = max(0.0, r - 2.0)
        p_hi = QPainterPath()
        if inner_r > 0.5:
            p_hi.addRoundedRect(QRectF(m + 2.0, m + 2.0, w - (m + 2.0) * 2, h - (m + 2.0) * 2), inner_r, inner_r)
        else:
            p_hi.addRect(QRectF(m + 2.0, m + 2.0, w - (m + 2.0) * 2, h - (m + 2.0) * 2))
        p.drawPath(p_hi)

    def _draw_studio_chamfer(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + float(self.width) * 0.5
        c = max(8.0, float(self.radius) if self.radius > 0 else 16.0)

        poly = QPolygonF([
            QPointF(m + c, m), QPointF(w - m - c, m),
            QPointF(w - m, m + c), QPointF(w - m, h - m - c),
            QPointF(w - m - c, h - m), QPointF(m + c, h - m),
            QPointF(m, h - m - c), QPointF(m, m + c),
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
            QPointF(m2 + c2, m2), QPointF(w - m2 - c2, m2),
            QPointF(w - m2, m2 + c2), QPointF(w - m2, h - m2 - c2),
            QPointF(w - m2 - c2, h - m2), QPointF(m2 + c2, h - m2),
            QPointF(m2, h - m2 - c2), QPointF(m2, m2 + c2),
        ])
        p.drawPolygon(poly_inner)

    def _draw_dot_matrix(self, p: QPainter, w: int, h: int, alpha: int):
        half_w = float(self.width) * 0.5
        m = float(self.margin) + half_w + 2.0
        r_c = max(0.0, float(self.radius) - half_w - 2.0) if self.radius > 0.5 else 0.0
        dot_sz = max(2.0, float(self.width) * 0.8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._create_brush_gradient(w, h, alpha))

        step = 18.0
        if r_c <= 1.0:
            avail_w = max(10.0, float(w) - m * 2.0)
            avail_h = max(10.0, float(h) - m * 2.0)
            count_x = max(2, int(round(avail_w / step)))
            count_y = max(2, int(round(avail_h / step)))
            step_x = avail_w / count_x
            step_y = avail_h / count_y

            for i in range(count_x + 1):
                x = m + i * step_x
                p.drawRect(QRectF(x - dot_sz * 0.5, m - dot_sz * 0.5, dot_sz, dot_sz))
                p.drawRect(QRectF(x - dot_sz * 0.5, float(h) - m - dot_sz * 0.5, dot_sz, dot_sz))

            for j in range(1, count_y):
                y = m + j * step_y
                p.drawRect(QRectF(m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
                p.drawRect(QRectF(float(w) - m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
            return

        straight_w = max(0.0, (float(w) - m * 2.0) - r_c * 2.0)
        straight_h = max(0.0, (float(h) - m * 2.0) - r_c * 2.0)
        count_sx = max(1, int(round(straight_w / step)))
        count_sy = max(1, int(round(straight_h / step)))
        step_sx = straight_w / count_sx if count_sx > 0 else 0
        step_sy = straight_h / count_sy if count_sy > 0 else 0

        for i in range(count_sx + 1):
            x = m + r_c + i * step_sx
            p.drawRect(QRectF(x - dot_sz * 0.5, m - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(x - dot_sz * 0.5, float(h) - m - dot_sz * 0.5, dot_sz, dot_sz))

        for j in range(count_sy + 1):
            y = m + r_c + j * step_sy
            p.drawRect(QRectF(m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(float(w) - m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))

        arc_len = (math.pi * 0.5) * r_c
        arc_dots = max(1, int(round(arc_len / step)))
        for k in range(1, arc_dots):
            theta = (math.pi * 0.5) * (k / float(arc_dots))
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            p.drawRect(QRectF((m + r_c - r_c * sin_t) - dot_sz * 0.5, (m + r_c - r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF((float(w) - m - r_c + r_c * sin_t) - dot_sz * 0.5, (m + r_c - r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF((float(w) - m - r_c + r_c * sin_t) - dot_sz * 0.5, (float(h) - m - r_c + r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF((m + r_c - r_c * sin_t) - dot_sz * 0.5, (float(h) - m - r_c + r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))

    def _draw_cyber_groove(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin) + 2.0
        r = float(self.radius)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        gap = 40.0
        cx, cy = w * 0.5, h * 0.5
        
        p_tl = QPainterPath()
        p_tl.moveTo(cx - gap, m)
        if r > 0.5:
            p_tl.lineTo(m + r, m)
            p_tl.arcTo(m, m, 2 * r, 2 * r, 90, 90)
        else:
            p_tl.lineTo(m, m)
        p_tl.lineTo(m, cy - gap)
        p.drawPath(p_tl)

        p_tr = QPainterPath()
        p_tr.moveTo(cx + gap, m)
        if r > 0.5:
            p_tr.lineTo(w - m - r, m)
            p_tr.arcTo(w - m - 2 * r, m, 2 * r, 2 * r, 90, -90)
        else:
            p_tr.lineTo(w - m, m)
        p_tr.lineTo(w - m, cy - gap)
        p.drawPath(p_tr)

        p_br = QPainterPath()
        p_br.moveTo(w - m, cy + gap)
        if r > 0.5:
            p_br.lineTo(w - m, h - m - r)
            p_br.arcTo(w - m - 2 * r, h - m - 2 * r, 2 * r, 2 * r, 0, -90)
        else:
            p_br.lineTo(w - m, h - m)
        p_br.lineTo(cx + gap, h - m)
        p.drawPath(p_br)

        p_bl = QPainterPath()
        p_bl.moveTo(cx - gap, h - m)
        if r > 0.5:
            p_bl.lineTo(m + r, h - m)
            p_bl.arcTo(m, h - m - 2 * r, 2 * r, 2 * r, 270, -90)
        else:
            p_bl.lineTo(m, h - m)
        p_bl.lineTo(m, cy + gap)
        p.drawPath(p_bl)

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.4))))
        p.setPen(sub_pen)
        p.drawLine(QPointF(cx - gap * 0.6, m), QPointF(cx + gap * 0.6, m))
        p.drawLine(QPointF(cx - gap * 0.6, h - m), QPointF(cx + gap * 0.6, h - m))
        p.drawLine(QPointF(m, cy - gap * 0.6), QPointF(m, cy + gap * 0.6))
        p.drawLine(QPointF(w - m, cy - gap * 0.6), QPointF(w - m, cy + gap * 0.6))

    def _draw_optical_vignette(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        r = float(self.radius)
        path = self._get_base_rounded_path(w, h)

        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = self._create_styled_pen(w, h, float(self.width), alpha)
        p.setPen(pen)
        p.drawPath(path)

        p.save()
        p.setClipPath(path)
        inner_rect = QRectF(m + 4.0, m + 4.0, w - (m + 4.0) * 2, h - (m + 4.0) * 2)
        p.fillRect(inner_rect, self._scanline_brush)
        p.restore()

    def _draw_cinematic_rim(self, p: QPainter, w: int, h: int, alpha: int):
        m = float(self.margin)
        r = float(self.radius)
        bar_h = max(3.0, float(self.width) * 1.5)

        p.save()
        path = self._get_base_rounded_path(w, h)
        p.setClipPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._create_brush_gradient(w, h, alpha))
        p.drawRect(QRectF(m, m, w - m * 2, bar_h))
        p.drawRect(QRectF(m, h - m - bar_h, w - m * 2, bar_h))
        p.restore()

        sub_pen = self._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.25))))
        p.setPen(sub_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(m, m + bar_h), QPointF(m, h - m - bar_h))
        p.drawLine(QPointF(w - m, m + bar_h), QPointF(w - m, h - m - bar_h))

    def _draw_corner_cross(self, p: QPainter, w: int, h: int, alpha: int):
        thick = float(self.width)
        half_w = thick * 0.5
        x_l = float(self.margin) + half_w
        y_t = float(self.margin) + half_w
        x_r = float(w) - x_l
        y_b = float(h) - y_t
        r_c = max(0.0, float(self.radius) - half_w) if self.radius > 0.5 else 0.0

        pen = self._create_styled_pen(w, h, thick, alpha)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        path = self._get_base_rounded_path(w, h)
        p.drawPath(path)

        cs = 14.0
        diag_off = r_c * 0.2929 if r_c > 0.5 else 0.0
        corners = [
            (x_l + diag_off, y_t + diag_off),
            (x_r - diag_off, y_t + diag_off),
            (x_r - diag_off, y_b - diag_off),
            (x_l + diag_off, y_b - diag_off)
        ]
        sub_pen = self._create_styled_pen(w, h, 1.5, alpha)
        p.setPen(sub_pen)
        for cx, cy in corners:
            p.drawLine(QPointF(cx - cs * 0.5, cy), QPointF(cx + cs * 0.5, cy))
            p.drawLine(QPointF(cx, cy - cs * 0.5), QPointF(cx, cy + cs * 0.5))

    def _draw_gamer_neon(self, p: QPainter, w: int, h: int, alpha: int):
        path = self._get_base_rounded_path(w, h)
        p.setBrush(Qt.BrushStyle.NoBrush)

        steps = 5
        base_w = float(self.width)
        for i in range(steps, 0, -1):
            ratio = i / float(steps)
            gw = base_w + (base_w * 2.2) * ratio
            ga = max(0, min(255, int(alpha * 0.28 * math.exp(-2.2 * (ratio ** 2)))))
            if ga > 0:
                outer_pen = self._create_styled_pen(w, h, gw, ga)
                p.setPen(outer_pen)
                p.drawPath(path)

        core_pen = self._create_styled_pen(w, h, base_w, alpha)
        p.setPen(core_pen)
        p.drawPath(path)

        corner_len = min(40.0, max(14.0, min(w, h) * 0.05))
        accent_pen = QPen(QColor(255, 255, 255, alpha), float(self.width + 1.2))
        accent_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        accent_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(accent_pen)

        for b_path in self._create_curved_corner_brackets(w, h, self.margin, self.radius, corner_len):
            p.drawPath(b_path)

        half_w = float(self.width) * 0.5
        x_l = float(self.margin) + half_w
        y_t = float(self.margin) + half_w
        x_r = float(w) - x_l
        y_b = float(h) - y_t
        max_r = min((x_r - x_l) / 2.0, (y_b - y_t) / 2.0)
        r_c = max(0.0, min(float(self.radius) - half_w, max_r)) if self.radius > 0.5 else 0.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, min(255, int(alpha * 1.1))))
        pip_sz = float(self.width + 2.0)
        half_pip = pip_sz * 0.5

        pips = [
            QPointF(x_l + r_c + corner_len, y_t), QPointF(x_l, y_t + r_c + corner_len),
            QPointF(x_r - r_c - corner_len, y_t), QPointF(x_r, y_t + r_c + corner_len),
            QPointF(x_r - r_c - corner_len, y_b), QPointF(x_r, y_b - r_c - corner_len),
            QPointF(x_l + r_c + corner_len, y_b), QPointF(x_l, y_b - r_c - corner_len)
        ]
        for pt in pips:
            p.drawEllipse(QRectF(pt.x() - half_pip, pt.y() - half_pip, pip_sz, pip_sz))