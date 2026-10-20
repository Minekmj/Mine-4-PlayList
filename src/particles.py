import math
import random
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen


class Particle:
    def __init__(self, w: int, h: int, p_type: str, p_dir: str):
        self.reset(w, h, p_type, p_dir, randomize_pos=True)

    def reset(self, w: int, h: int, p_type: str, p_dir: str, randomize_pos: bool = False):
        self.type = p_type
        self.direction = p_dir
        self.rot = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.5, 2.5)
        self.phase = random.uniform(0, math.pi * 2)

        if self.type == "벚꽃":
            self.size = random.uniform(3.5, 6.0)
            self.base_speed = random.uniform(1.2, 2.4)
            self.alpha_factor = random.uniform(0.6, 0.9)
        elif self.type == "별빛":
            self.size = random.uniform(2.0, 4.0)
            self.base_speed = random.uniform(0.4, 1.2)
            self.alpha_factor = random.uniform(0.5, 1.0)
        elif self.type == "빛망울":
            self.size = random.uniform(6.0, 14.0)
            self.base_speed = random.uniform(0.5, 1.3)
            self.alpha_factor = random.uniform(0.3, 0.6)
        elif self.type == "비":
            self.size = random.uniform(10.0, 18.0)
            self.base_speed = random.uniform(6.0, 10.0)
            self.alpha_factor = random.uniform(0.4, 0.8)
        else:
            self.size = random.uniform(1.8, 3.5)
            self.base_speed = random.uniform(0.8, 1.8)
            self.alpha_factor = random.uniform(0.4, 0.8)

        if randomize_pos or w <= 0 or h <= 0:
            self.x = random.uniform(0, max(1, w))
            self.y = random.uniform(0, max(1, h))
        else:
            if self.direction == "위로":
                self.x = random.uniform(0, w)
                self.y = h + self.size + 10
            elif self.direction == "왼쪽 대각선":
                self.x = random.choice([random.uniform(0, w), w + 10])
                self.y = -10 if self.x < w else random.uniform(0, h)
            elif self.direction == "오른쪽 대각선":
                self.x = random.choice([random.uniform(0, w), -10])
                self.y = -10 if self.x > 0 else random.uniform(0, h)
            elif self.direction == "부유 / 흩날림":
                self.x = random.uniform(0, w)
                self.y = random.uniform(0, h)
            else:
                self.x = random.uniform(0, w)
                self.y = -self.size - 10


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self.enabled = True
        self.p_type = "눈 / 먼지"
        self.direction = "아래로"
        self.palette_name = "청록"
        self.density = 0.45
        self.speed = 1.0

        self.palettes = {
            "청록": [QColor(40, 235, 190), QColor(90, 145, 255), QColor(190, 105, 255)],
            "벚꽃": [QColor(255, 155, 195), QColor(255, 205, 225), QColor(240, 135, 200)],
            "바다": [QColor(35, 180, 255), QColor(60, 130, 250), QColor(95, 240, 230)],
            "보라": [QColor(170, 105, 255), QColor(110, 110, 255), QColor(255, 110, 215)],
            "노을": [QColor(255, 125, 90), QColor(255, 185, 110), QColor(255, 110, 175)],
            "화이트": [QColor(240, 245, 255), QColor(215, 230, 255), QColor(255, 255, 255)],
        }

    def set_params(self, enabled: bool, p_type: str, direction: str, palette: str, density: float, speed: float):
        reset_needed = (self.p_type != p_type or self.direction != direction)
        self.enabled = enabled
        self.p_type = p_type
        self.direction = direction
        self.palette_name = palette
        self.density = max(0.0, min(1.0, density))
        self.speed = max(0.1, min(3.0, speed))

        if reset_needed:
            self.particles.clear()

    def _sync_count(self, w: int, h: int):
        target_count = int(140 * self.density) if self.enabled else 0
        while len(self.particles) < target_count:
            self.particles.append(Particle(w, h, self.p_type, self.direction))
        if len(self.particles) > target_count:
            self.particles = self.particles[:target_count]

    def update(self, w: int, h: int):
        if not self.enabled or w <= 0 or h <= 0 or self.density <= 0.001:
            return

        self._sync_count(w, h)
        dt = self.speed

        for p in self.particles:
            p.phase += 0.03 * dt
            p.rot = (p.rot + p.rot_speed * dt) % 360

            vx, vy = 0.0, 0.0
            if p.direction == "위로":
                vy = -p.base_speed * dt
                vx = math.sin(p.phase) * 0.45 * dt
            elif p.direction == "왼쪽 대각선":
                vx = -p.base_speed * 0.9 * dt
                vy = p.base_speed * 0.9 * dt
            elif p.direction == "오른쪽 대각선":
                vx = p.base_speed * 0.9 * dt
                vy = p.base_speed * 0.9 * dt
            elif p.direction == "부유 / 흩날림":
                vx = math.cos(p.phase * 0.8) * p.base_speed * 0.7 * dt
                vy = math.sin(p.phase) * p.base_speed * 0.7 * dt
            else:
                vy = p.base_speed * dt
                vx = math.sin(p.phase) * 0.45 * dt

            p.x += vx
            p.y += vy

            pad = p.size + 15
            if p.x < -pad or p.x > w + pad or p.y < -pad or p.y > h + pad:
                p.reset(w, h, self.p_type, self.direction, randomize_pos=False)

    def draw(self, painter: QPainter, w: int, h: int):
        if not self.enabled or not self.particles or w <= 0 or h <= 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        cols = self.palettes.get(self.palette_name, self.palettes["화이트"])
        c_count = len(cols)

        for i, p in enumerate(self.particles):
            base_col = cols[i % c_count]
            alpha = int(255 * p.alpha_factor * min(1.0, self.density * 1.5))
            col = QColor(base_col.red(), base_col.green(), base_col.blue(), max(10, min(255, alpha)))

            if p.type == "벚꽃":
                painter.save()
                painter.translate(p.x, p.y)
                painter.rotate(p.rot)
                scale_x = math.sin(p.phase) * 0.35 + 0.65
                painter.scale(scale_x, 1.0)
                painter.setBrush(col)
                painter.drawEllipse(QRectF(-p.size * 0.45, -p.size * 1.1, p.size * 0.9, p.size * 2.2))
                painter.restore()

            elif p.type == "별빛":
                pulse = math.sin(p.phase * 2.0) * 0.35 + 0.75
                s = p.size * pulse
                painter.setBrush(col)
                painter.drawEllipse(QRectF(p.x - s * 0.5, p.y - s * 0.5, s, s))
                if i % 3 == 0:
                    pen_col = QColor(col.red(), col.green(), col.blue(), max(5, alpha // 2))
                    painter.setPen(QPen(pen_col, 1.0))
                    painter.drawLine(int(p.x - s * 1.6), int(p.y), int(p.x + s * 1.6), int(p.y))
                    painter.drawLine(int(p.x), int(p.y - s * 1.6), int(p.x), int(p.y + s * 1.6))
                    painter.setPen(Qt.PenStyle.NoPen)

            elif p.type == "빛망울":
                halo_col = QColor(col.red(), col.green(), col.blue(), max(5, alpha // 4))
                painter.setBrush(halo_col)
                painter.drawEllipse(QRectF(p.x - p.size * 1.5, p.y - p.size * 1.5, p.size * 3.0, p.size * 3.0))
                painter.setBrush(col)
                painter.drawEllipse(QRectF(p.x - p.size * 0.5, p.y - p.size * 0.5, p.size, p.size))

            elif p.type == "비":
                pen = QPen(col, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                dx, dy = 0.0, p.size
                if p.direction == "왼쪽 대각선":
                    dx = -p.size * 0.6
                elif p.direction == "오른쪽 대각선":
                    dx = p.size * 0.6
                painter.drawLine(int(p.x), int(p.y), int(p.x + dx), int(p.y + dy))
                painter.setPen(Qt.PenStyle.NoPen)

            else:
                painter.setBrush(col)
                painter.drawEllipse(QRectF(p.x - p.size * 0.5, p.y - p.size * 0.5, p.size, p.size))

        painter.restore()