import math
from PyQt6.QtCore import Qt, QRectF, QLineF
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from src.effect.logic.particle import ParticleSystem, register_particle, DEFAULT_CONFIG


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


@register_particle("먼지", type_id=0, config=DEFAULT_CONFIG)
def draw_default(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        painter.setBrush(sys._color(r, g, b, a))
        hs = p.size * 0.5
        painter.drawEllipse(QRectF(p.x - hs, p.y - hs, p.size, p.size))


@register_particle("벚꽃", type_id=1, config=(3.5, 6.0, 1.2, 2.4, 0.6, 0.9))
def draw_sakura(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    sin = math.sin
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(sin(p.phase) * 0.35 + 0.65, 1.0)
        painter.setBrush(sys._color(r, g, b, a))
        s = p.size
        painter.drawEllipse(QRectF(-s * 0.45, -s * 1.1, s * 0.9, s * 2.2))
        painter.restore()


@register_particle("별", type_id=2, config=(2.0, 4.0, 0.4, 1.2, 0.5, 1.0))
def draw_stardust(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    sin = math.sin
    pen = sys._temp_pen
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setWidthF(1.0)
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        s = p.size * (sin(p.phase * 2.0) * 0.35 + 0.75)
        hs = s * 0.5
        painter.setBrush(sys._color(r, g, b, a))
        painter.drawEllipse(QRectF(p.x - hs, p.y - hs, s, s))
        if i % 3 == 0:
            pen.setColor(sys._color(r, g, b, max(5, a // 2)))
            painter.setPen(pen)
            arm = s * 1.6
            px, py = p.x, p.y
            painter.drawLine(int(px - arm), int(py), int(px + arm), int(py))
            painter.drawLine(int(px), int(py - arm), int(px), int(py + arm))
            painter.setPen(Qt.PenStyle.NoPen)


@register_particle("빛망울", type_id=3, config=(6.0, 14.0, 0.5, 1.3, 0.3, 0.6))
def draw_bokeh(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        s = p.size
        painter.setBrush(sys._color(r, g, b, max(5, a // 4)))
        painter.drawEllipse(QRectF(p.x - s * 1.5, p.y - s * 1.5, s * 3.0, s * 3.0))
        painter.setBrush(sys._color(r, g, b, a))
        painter.drawEllipse(QRectF(p.x - s * 0.5, p.y - s * 0.5, s, s))


@register_particle("비", type_id=4, config=(10.0, 18.0, 6.0, 10.0, 0.4, 0.8))
def draw_rain(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    pen = sys._temp_pen
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setWidthF(1.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    hypot = math.hypot
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        pen.setColor(sys._color(r, g, b, a))
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


@register_particle("하트", type_id=5, config=(5.0, 10.0, 0.7, 1.6, 0.6, 0.95))
def draw_heart(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    sin = math.sin
    path = PATH_HEART
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot * 0.3 + sin(p.phase) * 15.0)
        painter.scale(p.size, p.size)
        painter.setBrush(sys._color(r, g, b, a))
        painter.drawPath(path)
        painter.restore()


@register_particle("깃털", type_id=6, config=(8.0, 15.0, 0.5, 1.2, 0.45, 0.85))
def draw_feather(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    sin = math.sin
    path = PATH_FEATHER
    spine = LINE_FEATHER_SPINE
    pen = sys._temp_pen
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setWidthF(1.0)
    pen.setCosmetic(True)
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot * 0.4 + sin(p.phase) * 25.0)
        painter.scale(p.size, p.size)
        painter.setBrush(sys._color(r, g, b, a))
        painter.drawPath(path)
        pen.setColor(QColor(255, 255, 255, min(255, a + 35)))
        painter.setPen(pen)
        painter.drawLine(spine)
        painter.restore()
    painter.setPen(Qt.PenStyle.NoPen)


@register_particle("음표", type_id=7, config=(6.0, 11.0, 0.8, 1.8, 0.55, 0.95))
def draw_note(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    head = RECT_NOTE_HEAD
    stem = LINE_NOTE_STEM
    flag = PATH_NOTE_FLAG
    pen = sys._temp_pen
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        col = sys._color(r, g, b, a)
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


@register_particle("반짝이", type_id=8, config=(4.5, 9.0, 0.4, 1.2, 0.65, 1.0))
def draw_cross_star(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    sin = math.sin
    path = PATH_CROSS_STAR
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        painter.save()
        painter.translate(p.x, p.y)
        s = p.size * (sin(p.phase * 3.0) * 0.32 + 0.68)
        painter.rotate(p.rot)
        painter.scale(s, s)
        painter.setBrush(sys._color(r, g, b, a))
        painter.drawPath(path)
        painter.restore()


@register_particle("큐브", type_id=9, config=(6.0, 12.0, 0.6, 1.5, 0.5, 0.85))
def draw_cube(sys: ParticleSystem, painter: QPainter, cols: list, c_count: int, alpha_scale: float):
    pen = sys._temp_pen
    pen.setStyle(Qt.PenStyle.SolidLine)
    pen.setWidthF(1.2)
    for i in range(sys.active_count):
        p = sys.particle_array[i]
        r, g, b = cols[i % c_count]
        a = max(10, min(255, int(alpha_scale * p.alpha_factor)))
        pen.setColor(sys._color(r, g, b, a))
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.setPen(pen)
        painter.setBrush(sys._color(r, g, b, max(5, a // 5)))
        hs = p.size * 0.5
        painter.drawRect(QRectF(-hs, -hs, p.size, p.size))
        painter.restore()
    painter.setPen(Qt.PenStyle.NoPen)