import math
import random
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath


class Particle:
    def __init__(self, w: int, h: int, p_type: str, p_dir: str):
        self.vx = 0.0
        self.vy = 0.0
        self.reset(w, h, p_type, p_dir, randomize_pos=True)

    def reset(self, w: int, h: int, p_type: str, p_dir: str, randomize_pos: bool = False):
        self.type = self._normalize_type(p_type)
        self.direction = p_dir
        self.rot = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2.5, 2.5)
        self.phase = random.uniform(0, math.pi * 2)

        if self.type == "사쿠라":
            self.size = random.uniform(3.5, 6.0)
            self.base_speed = random.uniform(1.2, 2.4)
            self.alpha_factor = random.uniform(0.6, 0.9)
        elif self.type == "스타더스트":
            self.size = random.uniform(2.0, 4.0)
            self.base_speed = random.uniform(0.4, 1.2)
            self.alpha_factor = random.uniform(0.5, 1.0)
        elif self.type == "보케 글로우":
            self.size = random.uniform(6.0, 14.0)
            self.base_speed = random.uniform(0.5, 1.3)
            self.alpha_factor = random.uniform(0.3, 0.6)
        elif self.type == "라이트 레인":
            self.size = random.uniform(10.0, 18.0)
            self.base_speed = random.uniform(6.0, 10.0)
            self.alpha_factor = random.uniform(0.4, 0.8)
        elif self.type == "하트":
            self.size = random.uniform(5.0, 10.0)
            self.base_speed = random.uniform(0.7, 1.6)
            self.alpha_factor = random.uniform(0.6, 0.95)
        elif self.type == "페더":
            self.size = random.uniform(8.0, 15.0)
            self.base_speed = random.uniform(0.5, 1.2)
            self.alpha_factor = random.uniform(0.45, 0.85)
        elif self.type == "음표":
            self.size = random.uniform(6.0, 11.0)
            self.base_speed = random.uniform(0.8, 1.8)
            self.alpha_factor = random.uniform(0.55, 0.95)
        elif self.type == "크로스 스타":
            self.size = random.uniform(4.5, 9.0)
            self.base_speed = random.uniform(0.4, 1.2)
            self.alpha_factor = random.uniform(0.65, 1.0)
        elif self.type == "기하학 큐브":
            self.size = random.uniform(6.0, 12.0)
            self.base_speed = random.uniform(0.6, 1.5)
            self.alpha_factor = random.uniform(0.5, 0.85)
        else:
            self.size = random.uniform(1.8, 3.5)
            self.base_speed = random.uniform(0.8, 1.8)
            self.alpha_factor = random.uniform(0.4, 0.8)

        if self.direction == "위로":
            self.vx = 0.0
            self.vy = -self.base_speed
        elif self.direction == "왼쪽 대각선":
            self.vx = -self.base_speed * 0.9
            self.vy = self.base_speed * 0.9
        elif self.direction == "오른쪽 대각선":
            self.vx = self.base_speed * 0.9
            self.vy = self.base_speed * 0.9
        elif self.direction == "부유 / 흩날림":
            self.vx = math.cos(self.phase * 0.8) * self.base_speed * 0.7
            self.vy = math.sin(self.phase) * self.base_speed * 0.7
        else:
            self.vx = 0.0
            self.vy = self.base_speed

        pad = self.size + 15
        if randomize_pos or w <= 0 or h <= 0:
            self.x = random.uniform(0, max(1, w))
            self.y = random.uniform(0, max(1, h))
        else:
            if self.direction == "위로":
                self.x = random.uniform(0, w)
                self.y = h + pad
            elif self.direction == "왼쪽 대각선":
                if random.uniform(0, w + h) < w:
                    self.x = random.uniform(0, w)
                    self.y = -pad
                else:
                    self.x = w + pad
                    self.y = random.uniform(0, h)
            elif self.direction == "오른쪽 대각선":
                if random.uniform(0, w + h) < w:
                    self.x = random.uniform(0, w)
                    self.y = -pad
                else:
                    self.x = -pad
                    self.y = random.uniform(0, h)
            elif self.direction == "부유 / 흩날림":
                self.x = random.uniform(0, w)
                self.y = random.uniform(0, h)
            else:
                self.x = random.uniform(0, w)
                self.y = -pad

    def _normalize_type(self, raw_type: str) -> str:
        alias_map = {
            "눈 / 먼지": "소프트 더스트",
            "벚꽃": "사쿠라",
            "별빛": "스타더스트",
            "빛망울": "보케 글로우",
            "비": "라이트 레인",
            "깃털": "페더",
            "반짝이": "크로스 스타",
            "네온 큐브": "기하학 큐브",
        }
        return alias_map.get(raw_type, raw_type)


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self.enabled = True
        self.p_type = "소프트 더스트"
        self.direction = "아래로"
        self.palette_name = "에메랄드 틸"
        self.density = 0.45
        self.speed = 1.0
        self.prev_w = 0
        self.prev_h = 0

        self.palettes = {
            "에메랄드 틸": [QColor(40, 235, 190), QColor(90, 145, 255), QColor(190, 105, 255)],
            "사쿠라 로즈": [QColor(255, 155, 195), QColor(255, 205, 225), QColor(240, 135, 200)],
            "딥 오션": [QColor(35, 180, 255), QColor(60, 130, 250), QColor(95, 240, 230)],
            "네뷸라 바이올렛": [QColor(170, 105, 255), QColor(110, 110, 255), QColor(255, 110, 215)],
            "선셋 앰버": [QColor(255, 125, 90), QColor(255, 185, 110), QColor(255, 110, 175)],
            "퓨어 화이트": [QColor(240, 245, 255), QColor(215, 230, 255), QColor(255, 255, 255)],
            "샴페인 골드": [QColor(255, 215, 0), QColor(255, 190, 60), QColor(255, 242, 150)],
            "사이버 네온": [QColor(0, 255, 210), QColor(255, 0, 135), QColor(0, 195, 255)],
            "소프트 핑크": [QColor(255, 110, 180), QColor(195, 120, 255), QColor(255, 200, 235)],
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
        scale = max(1.0, (w * h) / (1280 * 720))
        target_count = int(140 * self.density * scale) if self.enabled else 0
        while len(self.particles) < target_count:
            self.particles.append(Particle(w, h, self.p_type, self.direction))
        if len(self.particles) > target_count:
            self.particles = self.particles[:target_count]

    def update(self, w: int, h: int):
        if not self.enabled or w <= 0 or h <= 0 or self.density <= 0.001:
            return

        if self.prev_w > 0 and self.prev_h > 0 and (self.prev_w != w or self.prev_h != h):
            sx = w / self.prev_w
            sy = h / self.prev_h
            for p in self.particles:
                p.x *= sx
                p.y *= sy
        self.prev_w = w
        self.prev_h = h

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

            p.vx = vx
            p.vy = vy
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

        cols = self.palettes.get(self.palette_name, self.palettes["퓨어 화이트"])
        c_count = len(cols)

        for i, p in enumerate(self.particles):
            base_col = cols[i % c_count]
            alpha = int(255 * p.alpha_factor * min(1.0, self.density * 1.5))
            col = QColor(base_col.red(), base_col.green(), base_col.blue(), max(10, min(255, alpha)))

            if p.type == "사쿠라":
                painter.save()
                painter.translate(p.x, p.y)
                painter.rotate(p.rot)
                scale_x = math.sin(p.phase) * 0.35 + 0.65
                painter.scale(scale_x, 1.0)
                painter.setBrush(col)
                painter.drawEllipse(QRectF(-p.size * 0.45, -p.size * 1.1, p.size * 0.9, p.size * 2.2))
                painter.restore()

            elif p.type == "스타더스트":
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

            elif p.type == "보케 글로우":
                halo_col = QColor(col.red(), col.green(), col.blue(), max(5, alpha // 4))
                painter.setBrush(halo_col)
                painter.drawEllipse(QRectF(p.x - p.size * 1.5, p.y - p.size * 1.5, p.size * 3.0, p.size * 3.0))
                painter.setBrush(col)
                painter.drawEllipse(QRectF(p.x - p.size * 0.5, p.y - p.size * 0.5, p.size, p.size))

            elif p.type == "라이트 레인":
                pen = QPen(col, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                speed = math.hypot(p.vx, p.vy)
                if speed > 0.0001:
                    dx = (p.vx / speed) * p.size
                    dy = (p.vy / speed) * p.size
                else:
                    dx, dy = 0.0, p.size
                painter.drawLine(int(p.x), int(p.y), int(p.x + dx), int(p.y + dy))
                painter.setPen(Qt.PenStyle.NoPen)

            elif p.type == "하트":
                painter.save()
                painter.translate(p.x, p.y)
                sway = math.sin(p.phase) * 15.0
                painter.rotate(p.rot * 0.3 + sway)
                s = p.size
                path = QPainterPath()
                path.moveTo(0, s * 0.35)
                path.cubicTo(-s * 0.7, -s * 0.45, -s * 0.7, -s * 1.05, 0, -s * 0.55)
                path.cubicTo(s * 0.7, -s * 1.05, s * 0.7, -s * 0.45, 0, s * 0.35)
                painter.setBrush(col)
                painter.drawPath(path)
                painter.restore()

            elif p.type == "페더":
                painter.save()
                painter.translate(p.x, p.y)
                sway = math.sin(p.phase) * 25.0
                painter.rotate(p.rot * 0.4 + sway)
                s = p.size
                path = QPainterPath()
                path.moveTo(0, -s)
                path.quadTo(s * 0.38, -s * 0.15, 0, s)
                path.quadTo(-s * 0.38, -s * 0.15, 0, -s)
                painter.setBrush(col)
                painter.drawPath(path)
                spine_c = QColor(255, 255, 255, max(10, min(255, alpha + 35)))
                painter.setPen(QPen(spine_c, 1.0))
                painter.drawLine(0, int(-s * 0.9), 0, int(s * 0.9))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.restore()

            elif p.type == "음표":
                painter.save()
                painter.translate(p.x, p.y)
                painter.rotate(p.rot * 0.25)
                s = p.size
                painter.setBrush(col)
                painter.drawEllipse(QRectF(-s * 0.45, 0, s * 0.9, s * 0.65))
                stem_pen = QPen(col, max(1.2, s * 0.18), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(stem_pen)
                painter.drawLine(int(s * 0.38), int(s * 0.3), int(s * 0.38), int(-s * 0.85))
                flag_path = QPainterPath()
                flag_path.moveTo(s * 0.38, -s * 0.85)
                flag_path.quadTo(s * 0.85, -s * 0.55, s * 0.75, -s * 0.1)
                painter.strokePath(flag_path, stem_pen)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.restore()

            elif p.type == "크로스 스타":
                painter.save()
                painter.translate(p.x, p.y)
                pulse = math.sin(p.phase * 3.0) * 0.32 + 0.68
                s = p.size * pulse
                painter.rotate(p.rot)
                path = QPainterPath()
                path.moveTo(0, -s)
                path.quadTo(0, 0, s, 0)
                path.quadTo(0, 0, 0, s)
                path.quadTo(0, 0, -s, 0)
                path.quadTo(0, 0, 0, -s)
                painter.setBrush(col)
                painter.drawPath(path)
                painter.restore()

            elif p.type == "기하학 큐브":
                painter.save()
                painter.translate(p.x, p.y)
                painter.rotate(p.rot)
                s = p.size
                painter.setPen(QPen(col, 1.2))
                fill_c = QColor(col.red(), col.green(), col.blue(), max(5, alpha // 5))
                painter.setBrush(fill_c)
                painter.drawRect(QRectF(-s * 0.5, -s * 0.5, s, s))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.restore()

            else:
                painter.setBrush(col)
                painter.drawEllipse(QRectF(p.x - p.size * 0.5, p.y - p.size * 0.5, p.size, p.size))

        painter.restore()