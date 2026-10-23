import math
import random
from PyQt6.QtCore import Qt, QRectF, QLineF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from src.native_bridge import get_native_engine, NativeParticle

ALIAS_MAP = {
    "눈 / 먼지": "소프트 더스트",
    "벚꽃": "사쿠라",
    "별빛": "스타더스트",
    "빛망울": "보케 글로우",
    "비": "라이트 레인",
    "깃털": "페더",
    "반짝이": "크로스 스타",
    "네온 큐브": "기하학 큐브",
}

TYPE_ENUM = {
    "소프트 더스트": 0, "사쿠라": 1, "스타더스트": 2, "보케 글로우": 3,
    "라이트 레인": 4, "하트": 5, "페더": 6, "음표": 7,
    "크로스 스타": 8, "기하학 큐브": 9
}

DIR_ENUM = {
    "위로": 0,
    "왼쪽 대각선": 1,
    "오른쪽 대각선": 2,
    "부유 / 흩날림": 3,
    "아래로": 4
}

TYPE_CONFIG = {
    "사쿠라": (3.5, 6.0, 1.2, 2.4, 0.6, 0.9),
    "스타더스트": (2.0, 4.0, 0.4, 1.2, 0.5, 1.0),
    "보케 글로우": (6.0, 14.0, 0.5, 1.3, 0.3, 0.6),
    "라이트 레인": (10.0, 18.0, 6.0, 10.0, 0.4, 0.8),
    "하트": (5.0, 10.0, 0.7, 1.6, 0.6, 0.95),
    "페더": (8.0, 15.0, 0.5, 1.2, 0.45, 0.85),
    "음표": (6.0, 11.0, 0.8, 1.8, 0.55, 0.95),
    "크로스 스타": (4.5, 9.0, 0.4, 1.2, 0.65, 1.0),
    "기하학 큐브": (6.0, 12.0, 0.6, 1.5, 0.5, 0.85),
}
DEFAULT_CONFIG = (1.8, 3.5, 0.8, 1.8, 0.4, 0.8)

PATH_HEART = QPainterPath()
PATH_HEART.moveTo(0.0, 0.35)
PATH_HEART.cubicTo(-0.7, -0.45, -0.7, -1.05, 0.0, -0.55)
PATH_HEART.cubicTo(0.7, -1.05, 0.7, -0.45, 0.0, 0.35)

PATH_FEATHER = QPainterPath()
PATH_FEATHER.moveTo(0.0, -1.0)
PATH_FEATHER.quadTo(0.38, -0.15, 0.0, 1.0)
PATH_FEATHER.quadTo(-0.38, -0.15, 0.0, -1.0)
LINE_FEATHER_SPINE = QLineF(0.0, -0.9, 0.0, 0.9)

PATH_CROSS_STAR = QPainterPath()
PATH_CROSS_STAR.moveTo(0.0, -1.0)
PATH_CROSS_STAR.quadTo(0.0, 0.0, 1.0, 0.0)
PATH_CROSS_STAR.quadTo(0.0, 0.0, 0.0, 1.0)
PATH_CROSS_STAR.quadTo(0.0, 0.0, -1.0, 0.0)
PATH_CROSS_STAR.quadTo(0.0, 0.0, 0.0, -1.0)

PATH_NOTE_FLAG = QPainterPath()
PATH_NOTE_FLAG.moveTo(0.38, -0.85)
PATH_NOTE_FLAG.quadTo(0.85, -0.55, 0.75, -0.1)
RECT_NOTE_HEAD = QRectF(-0.45, 0.0, 0.9, 0.65)
LINE_NOTE_STEM = QLineF(0.38, 0.3, 0.38, -0.85)


class ParticleSystem:
    def __init__(self):
        self.c_engine = get_native_engine()
        self.enabled = True
        self.p_type = "소프트 더스트"
        self.direction = "아래로"
        self.palette_name = "에메랄드 틸"
        self.density = 0.45
        self.speed = 1.0
        self.prev_w = 0
        self.prev_h = 0
        self._temp_pen = QPen()
        self._max_particles = 260
        self.active_count = 0
        self.particle_array = (NativeParticle * self._max_particles)()
        self._color_cache = {}

        raw_palettes = {
            "에메랄드 틸": [(40, 235, 190), (90, 145, 255), (190, 105, 255)],
            "사쿠라 로즈": [(255, 155, 195), (255, 205, 225), (240, 135, 200)],
            "딥 오션": [(35, 180, 255), (60, 130, 250), (95, 240, 230)],
            "네뷸라 바이올렛": [(170, 105, 255), (110, 110, 255), (255, 110, 215)],
            "선셋 앰버": [(255, 125, 90), (255, 185, 110), (255, 110, 175)],
            "퓨어 화이트": [(240, 245, 255), (215, 230, 255), (255, 255, 255)],
            "샴페인 골드": [(255, 215, 0), (255, 190, 60), (255, 242, 150)],
            "사이버 네온": [(0, 255, 210), (255, 0, 135), (0, 195, 255)],
            "소프트 핑크": [(255, 110, 180), (195, 120, 255), (255, 200, 235)],
            "청록": [(40, 235, 190), (90, 145, 255), (190, 105, 255)],
            "벚꽃": [(255, 155, 195), (255, 205, 225), (240, 135, 200)],
            "바다": [(35, 180, 255), (60, 130, 250), (95, 240, 230)],
            "보라": [(170, 105, 255), (110, 110, 255), (255, 110, 215)],
            "노을": [(255, 125, 90), (255, 185, 110), (255, 110, 175)],
            "화이트": [(240, 245, 255), (215, 230, 255), (255, 255, 255)],
        }
        self.palettes = {k: [QColor(*rgb) for rgb in v] for k, v in raw_palettes.items()}
        self._palette_rgbs = raw_palettes

        self._draw_handlers = {
            "사쿠라": self._draw_sakura,
            "스타더스트": self._draw_stardust,
            "보케 글로우": self._draw_bokeh,
            "라이트 레인": self._draw_rain,
            "하트": self._draw_heart,
            "페더": self._draw_feather,
            "음표": self._draw_note,
            "크로스 스타": self._draw_cross_star,
            "기하학 큐브": self._draw_cube,
        }

    def _reset_particle(self, idx: int, w: int, h: int, randomize_pos: bool = False):
        p = self.particle_array[idx]
        p_type = self.p_type
        p_dir = self.direction
        p.type = TYPE_ENUM.get(p_type, 0)
        p.direction = DIR_ENUM.get(p_dir, 4)
        p.rot = random.uniform(0.0, 360.0)
        p.rot_speed = random.uniform(-2.5, 2.5)
        p.phase = random.uniform(0.0, 6.2831853)

        cfg = TYPE_CONFIG.get(p_type, DEFAULT_CONFIG)
        p.size = random.uniform(cfg[0], cfg[1])
        p.base_speed = random.uniform(cfg[2], cfg[3])
        p.alpha_factor = random.uniform(cfg[4], cfg[5])
        p.pad = p.size + 15.0
        p.out_of_bounds = 0

        pad = p.pad
        if randomize_pos or w <= 0 or h <= 0:
            p.x = random.uniform(0.0, max(1.0, float(w)))
            p.y = random.uniform(0.0, max(1.0, float(h)))
        elif p_dir == "위로":
            p.x = random.uniform(0.0, w)
            p.y = h + pad
        elif p_dir == "왼쪽 대각선":
            if random.uniform(0.0, w + h) < w:
                p.x = random.uniform(0.0, w)
                p.y = -pad
            else:
                p.x = w + pad
                p.y = random.uniform(0.0, h)
        elif p_dir == "오른쪽 대각선":
            if random.uniform(0.0, w + h) < w:
                p.x = random.uniform(0.0, w)
                p.y = -pad
            else:
                p.x = -pad
                p.y = random.uniform(0.0, h)
        elif p_dir == "부유 / 흩날림":
            p.x = random.uniform(0.0, w)
            p.y = random.uniform(0.0, h)
        else:
            p.x = random.uniform(0.0, w)
            p.y = -pad

    def set_params(self, enabled: bool, p_type: str, direction: str, palette: str, density: float, speed: float):
        norm_type = ALIAS_MAP.get(p_type, p_type)
        reset_needed = (self.p_type != norm_type or self.direction != direction)
        cache_changed = self.palette_name != palette or self.density != max(0.0, min(1.0, density))
        self.enabled = enabled
        self.p_type = norm_type
        self.direction = direction
        self.palette_name = palette
        self.density = max(0.0, min(1.0, density))
        self.speed = max(0.1, min(3.0, speed))
        if cache_changed:
            self._color_cache.clear()

        if reset_needed:
            self.active_count = 0
            self.prev_w = 0
            self.prev_h = 0

    def _sync_count(self, w: int, h: int):
        scale = max(1.0, (w * h) / 921600.0)
        target = min(self._max_particles, int(140 * self.density * min(scale, 3.0))) if self.enabled else 0
        if self.active_count < target:
            for i in range(self.active_count, target):
                self._reset_particle(i, w, h, randomize_pos=True)
            self.active_count = target
        elif self.active_count > target:
            self.active_count = target

    def update(self, w: int, h: int):
        if not self.enabled or w <= 0 or h <= 0 or self.density <= 0.001:
            return

        if self.prev_w > 0 and self.prev_h > 0 and (self.prev_w != w or self.prev_h != h):
            sx = w / float(self.prev_w)
            sy = h / float(self.prev_h)
            for i in range(self.active_count):
                p = self.particle_array[i]
                p.x *= sx
                p.y *= sy

        self.prev_w = w
        self.prev_h = h
        self._sync_count(w, h)
        if self.active_count == 0:
            return

        dt = self.speed
        phase_dt = 0.03 * dt
        sway_speed = 0.45 * dt

        if self.c_engine:
            self.c_engine.c_update_particles(
                self.particle_array, self.active_count,
                float(w), float(h), float(dt), float(phase_dt), float(sway_speed)
            )
            for i in range(self.active_count):
                if self.particle_array[i].out_of_bounds:
                    self._reset_particle(i, w, h, False)
        else:
            for i in range(self.active_count):
                p = self.particle_array[i]
                p.phase += phase_dt
                p.rot = (p.rot + p.rot_speed * dt) % 360.0
                p.vx = math.sin(p.phase) * sway_speed
                p.vy = p.base_speed * dt
                p.x += p.vx
                p.y += p.vy
                pad = p.pad
                if p.x < -pad or p.x > w + pad or p.y < -pad or p.y > h + pad:
                    self._reset_particle(i, w, h, False)

    def draw(self, painter: QPainter, w: int, h: int):
        if not self.enabled or self.active_count == 0 or w <= 0 or h <= 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        cols = self._palette_rgbs.get(self.palette_name, self._palette_rgbs["퓨어 화이트"])
        c_count = len(cols)
        alpha_scale = 255.0 * min(1.0, self.density * 1.5)

        draw_handler = self._draw_handlers.get(self.p_type, self._draw_default)
        draw_handler(painter, cols, c_count, alpha_scale)

        painter.restore()

    def _color(self, r: int, g: int, b: int, a: int) -> QColor:
        key = (r, g, b, a)
        color = self._color_cache.get(key)
        if color is None:
            if len(self._color_cache) > 600:
                self._color_cache.clear()
            color = QColor(r, g, b, a)
            self._color_cache[key] = color
        return color

    def _draw_sakura(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        sin = math.sin
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot)
            painter.scale(sin(p.phase) * 0.35 + 0.65, 1.0)
            painter.setBrush(self._color(r, g, b, a))
            s = p.size
            painter.drawEllipse(QRectF(-s * 0.45, -s * 1.1, s * 0.9, s * 2.2))
            painter.restore()

    def _draw_stardust(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        sin = math.sin
        pen = self._temp_pen
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidthF(1.0)
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            s = p.size * (sin(p.phase * 2.0) * 0.35 + 0.75)
            hs = s * 0.5
            painter.setBrush(self._color(r, g, b, a))
            painter.drawEllipse(QRectF(p.x - hs, p.y - hs, s, s))
            if i % 3 == 0:
                pen.setColor(self._color(r, g, b, max(5, a // 2)))
                painter.setPen(pen)
                arm = s * 1.6
                px, py = p.x, p.y
                painter.drawLine(int(px - arm), int(py), int(px + arm), int(py))
                painter.drawLine(int(px), int(py - arm), int(px), int(py + arm))
                painter.setPen(Qt.PenStyle.NoPen)

    def _draw_bokeh(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            s = p.size
            painter.setBrush(self._color(r, g, b, max(5, a // 4)))
            painter.drawEllipse(QRectF(p.x - s * 1.5, p.y - s * 1.5, s * 3.0, s * 3.0))
            painter.setBrush(self._color(r, g, b, a))
            painter.drawEllipse(QRectF(p.x - s * 0.5, p.y - s * 0.5, s, s))

    def _draw_rain(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        pen = self._temp_pen
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidthF(1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        hypot = math.hypot
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            pen.setColor(self._color(r, g, b, a))
            painter.setPen(pen)
            speed = hypot(p.vx, p.vy)
            if speed > 0.0001:
                factor = p.size / speed
                dx = p.vx * factor
                dy = p.vy * factor
            else:
                dx, dy = 0.0, p.size
            painter.drawLine(int(p.x), int(p.y), int(p.x + dx), int(p.y + dy))
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_heart(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        sin = math.sin
        path = PATH_HEART
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot * 0.3 + sin(p.phase) * 15.0)
            painter.scale(p.size, p.size)
            painter.setBrush(self._color(r, g, b, a))
            painter.drawPath(path)
            painter.restore()

    def _draw_feather(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        sin = math.sin
        path = PATH_FEATHER
        spine = LINE_FEATHER_SPINE
        pen = self._temp_pen
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidthF(1.0)
        pen.setCosmetic(True)
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot * 0.4 + sin(p.phase) * 25.0)
            painter.scale(p.size, p.size)
            painter.setBrush(self._color(r, g, b, a))
            painter.drawPath(path)
            pen.setColor(QColor(255, 255, 255, min(255, a + 35)))
            painter.setPen(pen)
            painter.drawLine(spine)
            painter.restore()
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_note(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        head = RECT_NOTE_HEAD
        stem = LINE_NOTE_STEM
        flag = PATH_NOTE_FLAG
        pen = self._temp_pen
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            col = self._color(r, g, b, a)
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot * 0.25)
            s = p.size
            painter.scale(s, s)
            painter.setBrush(col)
            painter.drawEllipse(head)
            pen.setColor(col)
            pen.setWidthF(max(1.2 / s, 0.18))
            painter.setPen(pen)
            painter.drawLine(stem)
            painter.strokePath(flag, pen)
            painter.restore()
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_cross_star(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        sin = math.sin
        path = PATH_CROSS_STAR
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            painter.save()
            painter.translate(p.x, p.y)
            s = p.size * (sin(p.phase * 3.0) * 0.32 + 0.68)
            painter.rotate(p.rot)
            painter.scale(s, s)
            painter.setBrush(self._color(r, g, b, a))
            painter.drawPath(path)
            painter.restore()

    def _draw_cube(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        pen = self._temp_pen
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidthF(1.2)
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            pen.setColor(self._color(r, g, b, a))
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rot)
            painter.setPen(pen)
            painter.setBrush(self._color(r, g, b, max(5, a // 5)))
            hs = p.size * 0.5
            painter.drawRect(QRectF(-hs, -hs, p.size, p.size))
            painter.restore()
        painter.setPen(Qt.PenStyle.NoPen)

    def _draw_default(self, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
        for i in range(self.active_count):
            p = self.particle_array[i]
            r, g, b = cols[i % c_count]
            a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
            painter.setBrush(self._color(r, g, b, a))
            hs = p.size * 0.5
            painter.drawEllipse(QRectF(p.x - hs, p.y - hs, p.size, p.size))