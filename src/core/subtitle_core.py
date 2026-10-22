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
    __slots__ = ('start', 'end', 'text')

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
        self.items = []
        self._starts = []
        self._max_duration = 10.0

    def load_file(self, filepath: str) -> bool:
        self.clear()
        if not filepath or not os.path.exists(filepath):
            return False

        content = ""
        for enc in ['utf-8-sig', 'utf-8', 'cp949', 'euc-kr', 'utf-16', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                if content:
                    break
            except Exception:
                continue

        if not content:
            return False

        ext = os.path.splitext(filepath)[1].lower()
        if ext in ('.smi', '.sami'):
            self.items = self._parse_smi(content)
        else:
            self.items = self._parse_srt_vtt(content)

        if self.items:
            self.items.sort(key=lambda x: x.start)
            self._starts = [it.start for it in self.items]
            self._max_duration = max((it.end - it.start for it in self.items), default=10.0)
            return True
        return False

    def _parse_smi(self, content: str):
        items = []
        sync_regex = re.compile(r'<sync\s+[^>]*?start\s*=\s*["\']?(\d+)["\']?[^>]*>', re.IGNORECASE)
        tag_regex = re.compile(r'<[^>]+>')
        br_regex = re.compile(r'<br\s*/?>', re.IGNORECASE)
        splits = sync_regex.split(content)

        for i in range(1, len(splits), 2):
            try:
                start_sec = int(splits[i]) / 1000.0
                raw_text = splits[i + 1] if i + 1 < len(splits) else ""
                clean = br_regex.sub('\n', raw_text)
                clean = tag_regex.sub('', clean)
                clean = html.unescape(clean).strip()

                if not clean:
                    if items:
                        items[-1].end = start_sec
                    continue

                if i + 2 < len(splits):
                    next_start = int(splits[i + 2]) / 1000.0
                    end_sec = min(start_sec + 7.0, next_start)
                else:
                    end_sec = start_sec + 5.0

                items.append(SubtitleItem(start_sec, end_sec, clean))
            except Exception:
                continue

        return items

    def _parse_srt_vtt(self, content: str):
        items = []
        content = content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
        time_pattern = re.compile(r'((?:\d{1,2}:)?\d{1,2}:\d{2}[,\.]\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[,\.]\d{1,3})')
        tag_regex = re.compile(r'<[^>]+>')
        blocks = re.split(r'\n\s*\n+', content)

        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            for idx, line in enumerate(lines):
                match = time_pattern.search(line)
                if match:
                    try:
                        start_sec = self._parse_time(match.group(1))
                        end_sec = self._parse_time(match.group(2))
                        raw_text = "\n".join(lines[idx + 1:])
                        clean = tag_regex.sub('', raw_text).strip()
                        clean = html.unescape(clean)
                        if clean:
                            items.append(SubtitleItem(start_sec, end_sec, clean))
                    except Exception:
                        pass
                    break

        return items

    def _parse_time(self, time_str: str) -> float:
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        try:
            if len(parts) == 3:
                return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60.0 + float(parts[1])
            elif len(parts) == 1:
                return float(parts[0])
        except ValueError:
            pass
        return 0.0

    def get_text_at(self, current_sec: float) -> str:
        if not self.items:
            return ""

        t = current_sec + self.sub_delay
        idx = bisect.bisect_right(self._starts, t)
        if idx == 0:
            return ""

        matched = []
        for i in range(idx - 1, -1, -1):
            item = self.items[i]
            if (t - item.start) > self._max_duration:
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
            "font": "Pretendard, Malgun Gothic, sans-serif",
            "size": 44,
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "border_size": 3,
            "blur": 3,
            "pos": 94,
            "bold": True,
            "typewriter_enabled": False,
            "typewriter_speed": 28,
            "fade_in_enabled": True,
            "fade_duration": 200,
            "slide_direction": "아래에서 위로",
            "slide_distance": 16,
            "anim_style": "슬라이드 & 페이드",
            "max_width_ratio": 0.88
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
        self.config.update(cfg)
        self.visible_sub = visible
        self._cache_dirty = True
        self.update()

    def set_text(self, text: str):
        if self.text != text:
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
        anim_style = cfg.get("anim_style", "슬라이드 & 페이드")
        if cfg.get("typewriter_enabled", False) or anim_style == "타자기":
            return len(self.text) * cfg.get("typewriter_speed", 28) + 100
        return cfg.get("fade_duration", 200) + 50

    def _on_anim_tick(self):
        if not self.anim_active or not self.text.strip():
            self.anim_timer.stop()
            return

        elapsed_ms = (time.perf_counter() - self.anim_start_time) * 1000.0
        if elapsed_ms >= self._get_anim_duration():
            self.anim_active = False
            self.anim_timer.stop()

        self.update()

    def _wrap_text(self, raw_text: str, fm: QFontMetrics, max_w: int) -> list[str]:
        lines = []
        for paragraph in raw_text.split('\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if fm.horizontalAdvance(paragraph) <= max_w:
                lines.append(paragraph)
                continue

            words = paragraph.split(' ')
            cur_line = ""
            for w in words:
                candidate = f"{cur_line} {w}" if cur_line else w
                if fm.horizontalAdvance(candidate) <= max_w:
                    cur_line = candidate
                else:
                    if cur_line:
                        lines.append(cur_line)
                        cur_line = w
                    else:
                        chunk = ""
                        for ch in w:
                            if fm.horizontalAdvance(chunk + ch) <= max_w:
                                chunk += ch
                            else:
                                if chunk:
                                    lines.append(chunk)
                                chunk = ch
                        cur_line = chunk

            if cur_line:
                lines.append(cur_line)

        return lines if lines else [raw_text]

    def _rebuild_cached_pixmap(self):
        self._cache_dirty = False
        if not self.text.strip():
            self._cached_pixmap = QPixmap()
            return

        cfg = self.config
        font_family = cfg.get("font", "sans-serif").split(",")[0].strip()
        bold = cfg.get("bold", True)

        base_h = self.video_rect.height() if self.video_rect.height() > 0 else self.height()
        font_size = max(16, int(cfg.get("size", 44) * (base_h / 900.0)))
        font = QFont(font_family, font_size)
        font.setBold(bold)

        fm = QFontMetrics(font)
        self._cached_fm = fm

        video_w = self.video_rect.width() if (self.video_rect.isValid() and self.video_rect.width() > 0) else self.width()
        max_text_w = max(180, int(video_w * float(cfg.get("max_width_ratio", 0.88))))
        lines = self._wrap_text(self.text, fm, max_text_w)
        self._cached_lines = lines

        line_height = fm.lineSpacing()
        self._cached_line_h = line_height

        border_size = max(1, int(cfg.get("border_size", 3) * (base_h / 900.0)))
        blur = max(1, int(cfg.get("blur", 3)))

        pad = int(blur * 3 + border_size * 2 + 12)
        self._cached_pad = pad

        max_w = max(fm.horizontalAdvance(l) for l in lines) if lines else 100
        pix_w = max_w + pad * 2
        pix_h = (len(lines) * line_height) + pad * 2

        self._cached_w = pix_w
        self._cached_h = pix_h

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
            line_w = fm.horizontalAdvance(line)
            x = (pix_w - line_w) // 2
            y = start_y + (i * line_height)
            full_path.addText(x, y, font, line)

        shadow_offset = max(2, border_size)
        shadow_path = QPainterPath(full_path)
        shadow_path.translate(shadow_offset, shadow_offset + 1)
        s_pen = QPen(QColor(0, 0, 0, 160))
        s_pen.setWidth(border_size * 2 + 3)
        s_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        s_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.strokePath(shadow_path, s_pen)

        g_col1 = QColor(outline_color)
        g_col1.setAlpha(55)
        g_pen1 = QPen(g_col1)
        g_pen1.setWidth(border_size * 2 + blur * 4)
        g_pen1.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        g_pen1.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.strokePath(full_path, g_pen1)

        g_col2 = QColor(outline_color)
        g_col2.setAlpha(110)
        g_pen2 = QPen(g_col2)
        g_pen2.setWidth(border_size * 2 + blur * 2)
        g_pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        g_pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.strokePath(full_path, g_pen2)

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
        target_y = vy + (vh * pos_pct) - self._cached_h + self._cached_pad
        target_y = max(vy, min(vy + vh - self._cached_h + self._cached_pad / 2, target_y))

        elapsed_ms = (time.perf_counter() - self.anim_start_time) * 1000.0 if self.anim_start_time > 0 else 99999.0
        anim_style = cfg.get("anim_style", "슬라이드 & 페이드")
        fade_enabled = cfg.get("fade_in_enabled", True) or (anim_style in ("자연스러운 페이드", "슬라이드 & 페이드", "팝업 바운스"))
        typewriter_enabled = cfg.get("typewriter_enabled", False) or (anim_style == "타자기")
        direction = cfg.get("slide_direction", "아래에서 위로")
        fade_dur = max(40, cfg.get("fade_duration", 200))
        slide_dist = max(4, cfg.get("slide_distance", 16))
        tw_speed = max(10, cfg.get("typewriter_speed", 28))

        progress = min(1.0, elapsed_ms / fade_dur) if fade_dur > 0 else 1.0
        ease_out = 1.0 - math.pow(1.0 - progress, 3)

        if fade_enabled and progress < 1.0:
            painter.setOpacity(ease_out)

        offset_x = 0.0
        offset_y = 0.0
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
            scale_factor = 0.90 + (0.10 * ease_out) + (math.sin(progress * math.pi) * 0.05)
            center_x = target_x + self._cached_w / 2.0
            center_y = target_y + self._cached_h / 2.0
            painter.translate(center_x, center_y)
            painter.scale(scale_factor, scale_factor)
            painter.translate(-center_x, -center_y)

        if typewriter_enabled and self._cached_fm:
            total_chars = sum(len(l) for l in self._cached_lines)
            revealed_chars = int(elapsed_ms / tw_speed)
            if revealed_chars < total_chars:
                clip_region = QRegion()
                char_acc = 0
                for line_idx, line in enumerate(self._cached_lines):
                    line_len = len(line)
                    if revealed_chars <= char_acc:
                        break
                    elif revealed_chars < char_acc + line_len:
                        show_len = revealed_chars - char_acc
                        w_clip = self._cached_fm.horizontalAdvance(line[:show_len])
                    else:
                        w_clip = self._cached_fm.horizontalAdvance(line)
                    char_acc += line_len

                    line_w = self._cached_fm.horizontalAdvance(line)
                    lx = target_x + (self._cached_w - line_w) / 2.0 + offset_x - self._cached_pad
                    ly = target_y + self._cached_pad + (line_idx * self._cached_line_h) + offset_y - 4
                    clip_region = clip_region.united(QRect(int(lx), int(ly), int(w_clip + self._cached_pad * 2), int(self._cached_line_h + 8)))

                painter.setClipRegion(clip_region)

        painter.drawPixmap(int(target_x + offset_x), int(target_y + offset_y), self._cached_pixmap)