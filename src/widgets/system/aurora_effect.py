import math
import ctypes
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QPolygonF

AURORA_PALETTES = {
    '청록': ((40, 235, 190), (90, 145, 255), (190, 105, 255)),
    '분홍': ((255, 135, 190), (255, 190, 215), (205, 125, 255)),
    '파랑': ((35, 180, 255), (50, 115, 245), (90, 235, 230)),
    '보라': ((170, 100, 255), (100, 100, 255), (255, 100, 210)),
    '주황': ((255, 120, 85), (255, 175, 100), (255, 100, 165)),
}

class AuroraRenderer:
    def __init__(self, steps: int = 16):
        self.enabled = True
        self.style = '오로라'
        self.palette = '청록'
        self.intensity = 0.55
        self.speed = 1.0
        self.size = 1.0
        self.phase = 0.0
        self.steps = steps
        self._gradient_cache = {}
        self._y_buf = (ctypes.c_float * (self.steps + 1))()

    def set_params(self, enabled: bool, style: str, palette: str, intensity: float, speed: float = 1.0, size: float = 1.0):
        old_key = (self.style, self.palette, self.intensity, self.size)
        self.enabled = enabled
        self.style = style
        self.palette = palette
        self.intensity = intensity
        self.speed = max(0.1, min(5.0, float(speed)))
        self.size = max(0.2, min(3.0, float(size)))
        if old_key != (self.style, self.palette, self.intensity, self.size):
            self._gradient_cache.clear()

    def paint(self, p: QPainter, w: int, h: int, c_engine=None):
        if not self.enabled or self.style == '없음' or self.intensity <= 0.001 or w <= 0 or h <= 0:
            return

        palette_rgb = AURORA_PALETTES.get(self.palette, AURORA_PALETTES['청록'])
        is_aurora = (self.style == '오로라')
        band_h = max(50, int(h * (0.42 if is_aurora else 0.3) * self.size))
        amp = (0.075 if is_aurora else 0.035) * self.intensity * self.size

        grad_key = (h, band_h, is_aurora, palette_rgb, round(self.intensity, 3), round(self.size, 2))

        gradients = self._gradient_cache.get(grad_key)
        if gradients is None:
            gradients = []
            for i, rgb in enumerate(palette_rgb):
                color = QColor(*rgb)
                grad = QLinearGradient(0, h * max(0.0, (0.12 + i * 0.07) * self.size - amp), 0, band_h)
                top = QColor(color)
                top.setAlpha(int((75 if is_aurora else 42) * self.intensity))
                mid = QColor(color)
                mid.setAlpha(int((25 if is_aurora else 18) * self.intensity))
                end = QColor(color)
                end.setAlpha(0)
                grad.setColorAt(0.0, top)
                grad.setColorAt(0.55, mid)
                grad.setColorAt(1.0, end)
                gradients.append(grad)
            self._gradient_cache[grad_key] = gradients
            if len(self._gradient_cache) > 8:
                self._gradient_cache.pop(next(iter(self._gradient_cache)))

        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(Qt.PenStyle.NoPen)
        step_w = w / self.steps
        use_c = (c_engine is not None)

        for i, grad in enumerate(gradients):
            base = (0.12 + i * 0.07) * self.size
            poly = QPolygonF()

            if use_c:
                c_engine.c_compute_aurora_wave(self._y_buf, self.steps, float(h), float(base), float(amp), float(self.phase), i)
                for n in range(self.steps + 1):
                    poly.append(QPointF(n * step_w, self._y_buf[n]))
            else:
                for n in range(self.steps + 1):
                    x = n * step_w
                    ratio = n / self.steps
                    w1 = math.sin(ratio * math.pi * 2.0 * (1.15 + i * 0.4) + self.phase * 4.0 + i * 1.6)
                    w2 = math.sin(ratio * math.pi * 1.1 - self.phase * 1.8 + i)
                    y = h * base + h * amp * w1 + h * 0.016 * w2
                    poly.append(QPointF(x, y))

            poly.append(QPointF(w, band_h))
            poly.append(QPointF(0, band_h))

            p.setBrush(grad)
            p.drawPolygon(poly)

        p.restore()

    def tick(self, dt: float = 0.016) -> bool:
        if self.enabled and self.style != '없음' and self.intensity > 0.001:
            self.phase = (self.phase + 0.9 * dt * self.speed) % (math.pi * 2.0)
            return True
        return False