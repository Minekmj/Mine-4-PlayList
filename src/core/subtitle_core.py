import os
import re
import bisect
import html
import math
import time
from PyQt6.QtCore import Qt, QTimer, QRectF, QRect
from PyQt6.QtGui import QPainter, QPainterPath, QPen, QColor, QFont, QFontMetrics, QBrush, QPixmap, QRegion
from PyQt6.QtWidgets import QFrame


class SubtitleItem:
    __slots__ = ("start", "end", "text")

    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


class SubtitleManager:
    def __init__(self):
        self.items = []
        self._starts = []
        self._max_duration = 10.0
        self.sub_delay = 0.0

    def clear(self):
        self.items.clear()
        self._starts.clear()
        self._max_duration = 10.0

    def load_file(self, filepath: str) -> bool:
        self.clear()
        if not filepath or not os.path.exists(filepath):
            return False
        content = ""
        for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr", "utf-16", "latin-1"):
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    content = f.read()
                if content:
                    break
            except (UnicodeError, OSError):
                continue
        if not content:
            return False
        ext = os.path.splitext(filepath)[1].lower()
        self.items = self._parse_smi(content) if ext in (".smi", ".sami") else self._parse_srt_vtt(content)
        if not self.items:
            return False
        self.items.sort(key=lambda item: item.start)
        self._starts = [item.start for item in self.items]
        self._max_duration = max((item.end - item.start for item in self.items), default=10.0)
        return True

    def _parse_smi(self, content: str):
        items = []
        sync_regex = re.compile(r'<sync\s+[^>]*?start\s*=\s*["\']?(\d+)["\']?[^>]*>', re.IGNORECASE)
        tag_regex = re.compile(r"<[^>]+>")
        br_regex = re.compile(r"<br\s*/?>", re.IGNORECASE)
        splits = sync_regex.split(content)
        for i in range(1, len(splits), 2):
            try:
                start_sec = int(splits[i]) / 1000.0
                raw_text = splits[i + 1] if i + 1 < len(splits) else ""
                clean = html.unescape(tag_regex.sub("", br_regex.sub("\n", raw_text))).strip()
                if not clean:
                    if items:
                        items[-1].end = start_sec
                    continue
                next_start = int(splits[i + 2]) / 1000.0 if i + 2 < len(splits) else start_sec + 5.0
                items.append(SubtitleItem(start_sec, min(start_sec + 7.0, next_start), clean))
            except (ValueError, IndexError):
                continue
        return items

    def _parse_srt_vtt(self, content: str):
        items = []
        content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        time_pattern = re.compile(r"((?:\d{1,2}:)?\d{1,2}:\d{2}[,\.]\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[,\.]\d{1,3})")
        tag_regex = re.compile(r"<[^>]+>")
        for block in re.split(r"\n\s*\n+", content):
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            for idx, line in enumerate(lines):
                match = time_pattern.search(line)
                if not match:
                    continue
                try:
                    start_sec = self._parse_time(match.group(1))
                    end_sec = self._parse_time(match.group(2))
                    clean = html.unescape(tag_regex.sub("", "\n".join(lines[idx + 1:])).strip())
                    if clean and end_sec >= start_sec:
                        items.append(SubtitleItem(start_sec, end_sec, clean))
                except (ValueError, IndexError):
                    pass
                break
        return items

    def _parse_time(self, time_str: str) -> float:
        parts = time_str.replace(",", ".").split(":")
        try:
            if len(parts) == 3:
                return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
            if len(parts) == 2:
                return float(parts[0]) * 60.0 + float(parts[1])
            if len(parts) == 1:
                return float(parts[0])
        except ValueError:
            pass
        return 0.0

    def get_text_at(self, current_sec: float) -> str:
        if not self.items:
            return ""
        t = current_sec + self.sub_delay
        idx = bisect.bisect_right(self._starts, t)
        if idx <= 0:
            return ""
        matched = []
        for i in range(idx - 1, -1, -1):
            item = self.items[i]
            if t - item.start > self._max_duration:
                break
            if item.start <= t <= item.end:
                matched.append(item.text)
        if not matched:
            return ""
        matched.reverse()
        return "\n".join(matched)


class SubtitleFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.text = ""
        self.visible_sub = True
        self.config = {
            "font": "Pretendard, Malgun Gothic, sans-serif", "size": 44,
            "color": "#FFFFFF", "outline_color": "#000000", "border_size": 3,
            "blur": 3, "pos": 94, "bold": True, "typewriter_enabled": False,
            "typewriter_speed": 28, "fade_in_enabled": True, "fade_duration": 200,
            "slide_direction": "아래에서 위로", "slide_distance": 16,
            "anim_style": "슬라이드 & 페이드", "max_width_ratio": 0.88
        }
        self.video_rect = QRectF()
        self._cache_dirty = True
        self._cached_pixmap = QPixmap()
        self._cached_w = 0
        self._cached_h = 0
        self._cached_pad = 0
        self._cached_lines = []
        self._cached_line_h = 0
        self._cached_fm = None
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_start_time = 0.0
        self.anim_active = False

    def set_config(self, cfg: dict, visible: bool = True):
        changed = any(self.config.get(key) != value for key, value in cfg.items())
        visibility_changed = self.visible_sub != visible
        if not changed and not visibility_changed:
            return
        self.config.update(cfg)
        self.visible_sub = visible
        if changed:
            self._cache_dirty = True
        self.update()

    def set_text(self, text: str):
        if self.text == text:
            return
        self.text = text
        self._cache_dirty = True
        if text.strip() and self.visible_sub:
            self.anim_start_time = time.perf_counter()
            self.anim_active = True
            if not self.anim_timer.isActive():
                self.anim_timer.start()
        else:
            self.anim_active = False
            self.anim_timer.stop()
        self.update()

    def _get_anim_duration(self) -> float:
        cfg = self.config
        if cfg.get("typewriter_enabled", False) or cfg.get("anim_style") == "타자기":
            return len(self.text) * max(10, int(cfg.get("typewriter_speed", 28))) + 100
        return max(40, int(cfg.get("fade_duration", 200))) + 50

    def _on_anim_tick(self):
        if not self.anim_active or not self.text.strip():
            self.anim_timer.stop()
            return
        if (time.perf_counter() - self.anim_start_time) * 1000.0 >= self._get_anim_duration():
            self.anim_active = False
            self.anim_timer.stop()
        self.update()

    def _wrap_text(self, raw_text: str, fm: QFontMetrics, max_w: int) -> list[str]:
        lines = []
        for paragraph in raw_text.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if fm.horizontalAdvance(paragraph) <= max_w:
                lines.append(paragraph)
                continue
            current = ""
            for word in paragraph.split(" "):
                candidate = f"{current} {word}" if current else word
                if fm.horizontalAdvance(candidate) <= max_w:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                        current = ""
                    if fm.horizontalAdvance(word) <= max_w:
                        current = word
                    else:
                        chunk = ""
                        for char in word:
                            if fm.horizontalAdvance(chunk + char) <= max_w:
                                chunk += char
                            else:
                                if chunk:
                                    lines.append(chunk)
                                chunk = char
                        current = chunk
            if current:
                lines.append(current)
        return lines if lines else [raw_text]

    def _rebuild_cached_pixmap(self):
        self._cache_dirty = False
        if not self.text.strip():
            self._cached_pixmap = QPixmap()
            self._cached_w = self._cached_h = self._cached_pad = 0
            return
        cfg = self.config
        font_family = cfg.get("font", "sans-serif").split(",")[0].strip()
        base_h = self.video_rect.height() if self.video_rect.height() > 0 else self.height()
        font_size = max(16, int(float(cfg.get("size", 44)) * (base_h / 900.0)))
        font = QFont(font_family, font_size)
        font.setBold(bool(cfg.get("bold", True)))
        fm = QFontMetrics(font)
        self._cached_fm = fm
        video_w = self.video_rect.width() if self.video_rect.isValid() and self.video_rect.width() > 0 else self.width()
        max_text_w = max(180, int(video_w * max(0.2, min(1.0, float(cfg.get("max_width_ratio", 0.88))))))
        lines = self._wrap_text(self.text, fm, max_text_w)
        self._cached_lines = lines
        line_height = fm.lineSpacing()
        self._cached_line_h = line_height
        border_size = max(1, int(float(cfg.get("border_size", 3)) * (base_h / 900.0)))
        blur = max(1, min(12, int(cfg.get("blur", 3))))
        pad = int(blur * 3 + border_size * 2 + 12)
        self._cached_pad = pad
        max_w = max((fm.horizontalAdvance(line) for line in lines), default=100)
        pix_w = max_w + pad * 2
        pix_h = len(lines) * line_height + pad * 2
        self._cached_w, self._cached_h = pix_w, pix_h
        pixmap = QPixmap(pix_w, pix_h)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        outline_color = QColor(cfg.get("outline_color", "#000000"))
        text_color = QColor(cfg.get("color", "#FFFFFF"))
        start_y = pad + fm.ascent()
        full_path = QPainterPath()
        for i, line in enumerate(lines):
            x = (pix_w - fm.horizontalAdvance(line)) // 2
            full_path.addText(x, start_y + i * line_height, font, line)
        shadow_path = QPainterPath(full_path)
        shadow_path.translate(max(2, border_size), max(2, border_size) + 1)
        s_pen = QPen(QColor(0, 0, 0, 160))
        s_pen.setWidth(border_size * 2 + 3)
        s_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        s_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.strokePath(shadow_path, s_pen)
        for alpha, width in ((55, border_size * 2 + blur * 4), (110, border_size * 2 + blur * 2)):
            glow = QColor(outline_color)
            glow.setAlpha(alpha)
            pen = QPen(glow)
            pen.setWidth(width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.strokePath(full_path, pen)
        out_pen = QPen(outline_color)
        out_pen.setWidth(border_size * 2)
        out_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        out_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.strokePath(full_path, out_pen)
        p.fillPath(full_path, QBrush(text_color))
        p.end()
        self._cached_pixmap = pixmap

    def paintEvent(self, event):
        if not self.visible_sub or not self.text.strip():
            return
        if self._cache_dirty or self._cached_pixmap.isNull():
            self._rebuild_cached_pixmap()
        if self._cached_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        cfg = self.config
        pos_pct = float(cfg.get("pos", 94)) / 100.0
        vy = self.video_rect.y() if self.video_rect.isValid() else 0
        vh = self.video_rect.height() if self.video_rect.isValid() else self.height()
        target_x = (self.width() - self._cached_w) / 2.0
        target_y = vy + vh * pos_pct - self._cached_h + self._cached_pad
        target_y = max(vy, min(vy + vh - self._cached_h + self._cached_pad / 2, target_y))
        elapsed_ms = (time.perf_counter() - self.anim_start_time) * 1000.0 if self.anim_start_time > 0 else 99999.0
        anim_style = cfg.get("anim_style", "슬라이드 & 페이드")
        fade_enabled = bool(cfg.get("fade_in_enabled", True)) or anim_style in ("자연스러운 페이드", "슬라이드 & 페이드", "팝업 바운스")
        typewriter_enabled = bool(cfg.get("typewriter_enabled", False)) or anim_style == "타자기"
        direction = cfg.get("slide_direction", "아래에서 위로")
        fade_dur = max(40, int(cfg.get("fade_duration", 200)))
        slide_dist = max(4, int(cfg.get("slide_distance", 16)))
        tw_speed = max(10, int(cfg.get("typewriter_speed", 28)))
        progress = min(1.0, elapsed_ms / fade_dur) if fade_dur > 0 else 1.0
        ease_out = 1.0 - (1.0 - progress) ** 3
        if fade_enabled and progress < 1.0:
            painter.setOpacity(ease_out)
        offset_x = offset_y = 0.0
        if (anim_style == "슬라이드 & 페이드" or direction != "없음") and progress < 1.0:
            shift = (1.0 - ease_out) * slide_dist
            if direction == "아래에서 위로":
                offset_y = shift
            elif direction == "위에서 아래로":
                offset_y = -shift
            elif direction in ("왼쪽에서", "왼쪽에서 오른쪽으로"):
                offset_x = -shift
            elif direction in ("오른쪽에서", "오른쪽에서 왼쪽으로"):
                offset_x = shift
        if anim_style == "팝업 바운스" and progress < 1.0:
            scale_factor = 0.90 + 0.10 * ease_out + math.sin(progress * math.pi) * 0.05
            center_x = target_x + self._cached_w / 2.0
            center_y = target_y + self._cached_h / 2.0
            painter.translate(center_x, center_y)
            painter.scale(scale_factor, scale_factor)
            painter.translate(-center_x, -center_y)
        if typewriter_enabled and self._cached_fm:
            total_chars = sum(map(len, self._cached_lines))
            revealed_chars = int(elapsed_ms / tw_speed)
            if revealed_chars < total_chars:
                clip_region = QRegion()
                char_acc = 0
                for line_idx, line in enumerate(self._cached_lines):
                    line_len = len(line)
                    if revealed_chars <= char_acc:
                        break
                    show_len = min(line_len, revealed_chars - char_acc)
                    w_clip = self._cached_fm.horizontalAdvance(line[:show_len])
                    line_w = self._cached_fm.horizontalAdvance(line)
                    lx = target_x + (self._cached_w - line_w) / 2.0 + offset_x - self._cached_pad
                    ly = target_y + self._cached_pad + line_idx * self._cached_line_h + offset_y - 4
                    clip_region = clip_region.united(QRect(int(lx), int(ly), int(w_clip + self._cached_pad * 2), int(self._cached_line_h + 8)))
                    char_acc += line_len
                painter.setClipRegion(clip_region)
        painter.drawPixmap(int(target_x + offset_x), int(target_y + offset_y), self._cached_pixmap)
