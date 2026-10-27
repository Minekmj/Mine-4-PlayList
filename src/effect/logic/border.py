import math
from collections import OrderedDict
from typing import Callable, Dict
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QLinearGradient,
    QConicalGradient, QPainterPath, QBrush, QImage
)

from src.effect.logic.border_anime import get_animation

BORDER_REGISTRY: Dict[str, Callable] = {}

def register_border(style_name: str):
    def decorator(fn: Callable):
        BORDER_REGISTRY[style_name] = fn
        return fn
    return decorator

class ScreenBorderSystem:
    def __init__(self, **kwargs):
        self.enabled = True
        self.style = "네온"
        self.color_mode = "단색"
        self.anim_mode = "숨쉬기"

        self.color1 = QColor("#38BDF8")
        self.color2 = QColor("#818CF8")
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

        if kwargs:
            self.configure(**kwargs)

    def _create_scanline_brush(self) -> QBrush:
        pattern = QImage(1, 4, QImage.Format.Format_ARGB32_Premultiplied)
        pattern.fill(0)
        pattern.setPixelColor(0, 0, QColor(0, 0, 0, 0))
        pattern.setPixelColor(0, 1, QColor(0, 0, 0, 0))
        pattern.setPixelColor(0, 2, QColor(255, 255, 255, 30))
        pattern.setPixelColor(0, 3, QColor(255, 255, 255, 30))
        return QBrush(pattern)

    def configure(self, **kwargs):
        for key, val in kwargs.items():
            if not hasattr(self, key):
                continue
            if key in ("color1", "color2") and isinstance(val, str):
                val = QColor(val) if val else (self.color1 if key == "color1" else self.color2)
            elif key == "anim_speed":
                val = max(0.1, min(3.0, float(val)))
            elif key == "pulse_depth":
                val = max(0.0, min(0.8, float(val)))
            elif key == "width":
                val = max(1, min(24, int(val)))
            elif key == "margin":
                val = max(0, min(60, int(val)))
            elif key == "radius":
                val = max(0, min(80, int(val)))
            elif key == "glow_spread":
                val = max(0, min(40, int(val)))
            elif key == "opacity":
                val = max(0.0, min(1.0, float(val)))
            setattr(self, key, val)

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

        anim = get_animation(self.anim_mode)
        anim.update(self, dt)

    def _get_active_alpha(self, base_alpha: int) -> int:
        anim = get_animation(self.anim_mode)
        mult = anim.get_alpha_mult(self)

        final_a = int(base_alpha * self.opacity * max(0.05, min(1.0, mult)))
        return max(0, min(255, final_a))

    def _create_brush_gradient(self, w: int, h: int, alpha: int) -> QLinearGradient | QConicalGradient:
        anim = get_animation(self.anim_mode)
        is_rotating = anim.is_rotating or self.color_mode == "무지개" or self.anim_mode == "회전"
        angle = int(round(self.sweep_angle / 5.0) * 5) % 360 if is_rotating else 0

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

        if self.color_mode == "무지개":
            cg = QConicalGradient(cx, cy, cached_angle)
            hues = [(0.0, 0), (0.16, 42), (0.33, 85), (0.50, 128), (0.66, 170), (0.83, 212), (1.0, 255)]
            for pos, h_val in hues:
                cg.setColorAt(pos, QColor.fromHsv(h_val, 215, 255, alpha))
            return cg

        if self.color_mode == "그라디언트":
            c1 = QColor(self.color1.red(), self.color1.green(), self.color1.blue(), alpha)
            c2 = QColor(self.color2.red(), self.color2.green(), self.color2.blue(), alpha)
        else:
            c1 = QColor(self.color1.red(), self.color1.green(), self.color1.blue(), alpha)
            c2 = c1

        anim = get_animation(self.anim_mode)
        if anim.is_rotating or self.anim_mode == "회전":
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
        return QPen(grad, pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)

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
            p_br.arcTo(QRectF(x_r - 2.0 * r_c, y_b - 2.0 * r_c, 2.0 * r_c), 0.0, -90.0)
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
            p_bl.arcTo(QRectF(x_l, y_b - 2.0 * r_c, 2.0 * r_c), 180.0, 90.0)
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

        draw_fn = BORDER_REGISTRY.get(self.style)
        if not draw_fn:
            return

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        active_alpha = self._get_active_alpha(255)

        draw_fn(self, p, w, h, active_alpha)

        p.restore()