import math
import random
import functools
from typing import Callable, Dict
from PyQt6.QtCore import Qt, QRectF, QLineF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QRegion
from src.C.native_bridge import get_native_engine, NativeParticle

DIR_ENUM = {
    "위로": 0,
    "왼쪽 대각선": 1,
    "오른쪽 대각선": 2,
    "흩날림": 3,
    "아래로": 4
}
DEFAULT_CONFIG = (1.8, 3.5, 0.8, 1.8, 0.4, 0.8)

PARTICLE_REGISTRY: Dict[str, Callable] = {}


def register_particle(name: str, type_id: int = 0, config: tuple = DEFAULT_CONFIG):
    def decorator(fn: Callable):
        fn.type_id = type_id
        fn.config = config
        PARTICLE_REGISTRY[name] = fn
        return fn
    return decorator


class ParticleHandlerProxy(dict):
    def __init__(self, sys):
        super().__init__()
        self._sys = sys

    def __getitem__(self, key):
        if key in PARTICLE_REGISTRY:
            return functools.partial(PARTICLE_REGISTRY[key], self._sys)
        raise KeyError(key)

    def get(self, key, default=None):
        fn = PARTICLE_REGISTRY.get(key)
        if fn is not None:
            return functools.partial(fn, self._sys)
        return default

    def __contains__(self, key):
        return key in PARTICLE_REGISTRY

    def keys(self):
        return PARTICLE_REGISTRY.keys()

    def items(self):
        for k, fn in PARTICLE_REGISTRY.items():
            yield k, functools.partial(fn, self._sys)


class ParticleSystem:
    def __init__(self, **kwargs):

        self.c_engine = get_native_engine()
        self.enabled = True
        self.p_type = "먼지"
        self.direction = "아래로"
        self.palette_name = "흰색"
        self.density = 0.45
        self.speed = 1.0
        self.size_scale = 1.0
        self.prev_w = 0
        self.prev_h = 0
        self._temp_pen = QPen()
        self._max_particles = 260
        self.active_count = 0
        self.particle_array = (NativeParticle * self._max_particles)()
        self._color_cache = {}

        raw_palettes = {
            "청록": [(40, 235, 190), (90, 145, 255), (190, 105, 255)],
            "분홍": [(255, 155, 195), (255, 205, 225), (240, 135, 200)],
            "파랑": [(35, 180, 255), (60, 130, 250), (95, 240, 230)],
            "보라": [(170, 105, 255), (110, 110, 255), (255, 110, 215)],
            "주황": [(255, 125, 90), (255, 185, 110), (255, 110, 175)],
            "흰색": [(240, 245, 255), (215, 230, 255), (255, 255, 255)],
            "노랑": [(255, 215, 0), (255, 190, 60), (255, 242, 150)],
            "형광": [(0, 255, 210), (255, 0, 135), (0, 195, 255)],
            "연분홍": [(255, 110, 180), (195, 120, 255), (255, 200, 235)],
        }
        self.palettes = {k: [QColor(*rgb) for rgb in v] for k, v in raw_palettes.items()}
        self._palette_rgbs = raw_palettes

        self._draw_handlers = ParticleHandlerProxy(self)

        if kwargs:
            self.configure(**kwargs)

    def configure(self, **kwargs):
        new_enabled = kwargs.get("enabled", self.enabled)
        new_ptype = kwargs.get("p_type", self.p_type)
        new_dir = kwargs.get("direction", self.direction)
        new_pal = kwargs.get("palette", kwargs.get("palette_name", self.palette_name))
        new_density = kwargs.get("density", self.density)
        new_speed = kwargs.get("speed", self.speed)
        self.set_params(new_enabled, new_ptype, new_dir, new_pal, new_density, new_speed)

    def set_params(self, enabled: bool, p_type: str, direction: str, palette: str, density: float, speed: float, size: float = 1.0):
        reset_needed = (self.p_type != p_type or self.direction != direction)
        cache_changed = self.palette_name != palette or self.density != max(0.0, min(1.0, density))
        old_size = self.size_scale
        self.enabled = enabled
        self.p_type = p_type
        self.direction = direction
        self.palette_name = palette
        self.density = max(0.0, min(1.0, density))
        self.speed = max(0.1, min(5.0, float(speed)))
        self.size_scale = max(0.2, min(5.0, float(size)))

        if abs(old_size - self.size_scale) > 0.01 and old_size > 0:
            scale_ratio = self.size_scale / old_size
            for i in range(self.active_count):
                self.particle_array[i].size *= scale_ratio
                self.particle_array[i].pad = self.particle_array[i].size + 15.0

        if cache_changed:
            self._color_cache.clear()

        if reset_needed:
            self.active_count = 0
            self.prev_w = 0
            self.prev_h = 0

    def _reset_particle(self, idx: int, w: int, h: int, randomize_pos: bool = False):
        p = self.particle_array[idx]
        p_type = self.p_type
        p_dir = self.direction

        handler = PARTICLE_REGISTRY.get(p_type, PARTICLE_REGISTRY.get("먼지"))
        p.type = getattr(handler, "type_id", 0)
        p.direction = DIR_ENUM.get(p_dir, 4)
        p.rot = random.uniform(0.0, 360.0)
        p.rot_speed = random.uniform(-2.5, 2.5)
        p.phase = random.uniform(0.0, 6.2831853)

        cfg = getattr(handler, "config", DEFAULT_CONFIG)
        p.size = random.uniform(cfg[0], cfg[1]) * self.size_scale
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
        elif p_dir == "흩날림":
            p.x = random.uniform(0.0, w)
            p.y = random.uniform(0.0, h)
        else:
            p.x = random.uniform(0.0, w)
            p.y = -pad

    def _sync_count(self, w: int, h: int):
        scale = max(1.0, (w * h) / 921600.0)
        target = min(self._max_particles, int(140 * self.density * min(scale, 3.0))) if self.enabled else 0
        if self.active_count < target:
            for i in range(self.active_count, target):
                self._reset_particle(i, w, h, randomize_pos=True)
            self.active_count = target
        elif self.active_count > target:
            self.active_count = target

    def update(self, w: int, h: int, dt_sec: float = 0.01667):
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

        dt = dt_sec * 60.0 * self.speed
        phase_dt = 0.03 * dt
        sway_speed = 0.45 * dt

        self.c_engine.c_update_particles(
            self.particle_array, self.active_count,
            float(w), float(h), float(dt), float(phase_dt), float(sway_speed)
        )
        for i in range(self.active_count):
            if self.particle_array[i].out_of_bounds:
                self._reset_particle(i, w, h, False)

    def draw(self, painter: QPainter, w: int, h: int, exclude_rect: QRectF = None):
        if not self.enabled or self.active_count == 0 or w <= 0 or h <= 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        has_exclude = exclude_rect is not None and not exclude_rect.isEmpty()
        if has_exclude:
            ex_x1, ex_y1 = exclude_rect.left(), exclude_rect.top()
            ex_x2, ex_y2 = exclude_rect.right(), exclude_rect.bottom()
        else:
            ex_x1 = ex_y1 = ex_x2 = ex_y2 = 0

        cols = self._palette_rgbs.get(self.palette_name, self._palette_rgbs["흰색"])
        c_count = len(cols)
        alpha_scale = 255.0 * min(1.0, self.density * 1.5)

        default_handler = self._draw_handlers.get("먼지")
        draw_handler = self._draw_handlers.get(self.p_type, default_handler)

        if draw_handler is not None:
            if has_exclude:
                self._draw_with_culling(painter, draw_handler, cols, c_count, alpha_scale, ex_x1, ex_y1, ex_x2, ex_y2)
            else:
                draw_handler(painter, cols, c_count, alpha_scale)

        painter.restore()

    def _draw_with_culling(self, painter, draw_handler, cols, c_count, alpha_scale, ex_x1, ex_y1, ex_x2, ex_y2):
        full_reg = QRegion(0, 0, int(painter.device().width()), int(painter.device().height()))
        video_reg = QRegion(int(ex_x1), int(ex_y1), int(ex_x2 - ex_x1), int(ex_y2 - ex_y1))
        painter.setClipRegion(full_reg.subtracted(video_reg))
        draw_handler(painter, cols, c_count, alpha_scale)

    def _color(self, r: int, g: int, b: int, a: int) -> QColor:
        key = (r, g, b, a)
        color = self._color_cache.get(key)
        if color is None:
            if len(self._color_cache) > 600:
                self._color_cache.clear()
            color = QColor(r, g, b, a)
            self._color_cache[key] = color
        return color