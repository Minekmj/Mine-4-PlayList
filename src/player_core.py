import os
import sys
import re
import math
import time
import threading
import av
import numpy as np
from PyQt6.QtCore import Qt, QUrl, QObject, QTimer, QRectF, QRect, QSizeF, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPen, QColor, QFont, QFontMetrics, QBrush, QPixmap, QRegion
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QGraphicsView, QGraphicsScene
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoFrame
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem


class SubtitleItem:
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


class SubtitleManager:
    def __init__(self):
        self.items = []
        self.sub_delay = 0.0

    def clear(self):
        self.items = []

    def load_file(self, filepath: str) -> bool:
        self.clear()
        if not filepath or not os.path.exists(filepath):
            return False

        content = ""
        for enc in ['cp949', 'euc-kr', 'utf-8-sig', 'utf-8', 'utf-16', 'latin-1']:
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

        return len(self.items) > 0

    def _parse_smi(self, content: str):
        items = []
        sync_regex = re.compile(r'<sync\s+[^>]*?start\s*=\s*["\']?(\d+)["\']?[^>]*>', re.IGNORECASE)
        splits = sync_regex.split(content)

        for i in range(1, len(splits), 2):
            try:
                start_sec = int(splits[i]) / 1000.0
                raw_text = splits[i + 1] if i + 1 < len(splits) else ""

                clean = re.sub(r'<br\s*/?>', '\n', raw_text, flags=re.IGNORECASE)
                clean = re.sub(r'<[^>]+>', '', clean)
                clean = clean.replace('&nbsp;', ' ').replace('&quot;', '"').replace('&apos;', "'")
                clean = clean.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()

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

        items.sort(key=lambda x: x.start)
        return items

    def _parse_srt_vtt(self, content: str):
        items = []
        content = content.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
        pattern = re.compile(
            r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})[^\n]*\n([\s\S]*?)(?=\n\s*(?:\d+\s*\n|\d{1,2}:)|\Z)'
        )
        for m in pattern.finditer(content):
            try:
                start_sec = self._parse_time(m.group(1))
                end_sec = self._parse_time(m.group(2))
                raw_text = m.group(3).strip()
                clean = re.sub(r'<[^>]+>', '', raw_text).strip()
                if clean:
                    items.append(SubtitleItem(start_sec, end_sec, clean))
            except Exception:
                continue

        items.sort(key=lambda x: x.start)
        return items

    def _parse_time(self, time_str: str) -> float:
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        if len(parts) == 3:
            return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60.0 + float(parts[1])
        return 0.0

    def get_text_at(self, current_sec: float) -> str:
        t = current_sec + self.sub_delay
        matched = []
        for item in self.items:
            if item.start <= t <= item.end:
                matched.append(item.text)
            elif item.start > t + 5.0:
                break
        return "\n".join(matched)


class AudioNormalizer(QObject):
    gain_ready = pyqtSignal(str, float)

    def __init__(self, target_base_db: float = -24.0):
        super().__init__()
        self.target_db = target_base_db
        self.gain_cache = {}
        self._analyzing = set()

    def _measure_base_volume_db(self, filepath: str) -> float:
        with av.open(filepath) as container:
            audio_streams = [s for s in container.streams if s.type == 'audio']
            if not audio_streams:
                return -24.0

            stream = audio_streams[0]
            rate = stream.rate or 44100

            dur = float(container.duration / 1000000.0) if container.duration else 0.0

            if dur > 20.0:
                seek_pos = max(3.0, dur * 0.10)
                try:
                    container.seek(int(seek_pos * 1000000))
                except Exception:
                    pass

            samples = []
            collected_sec = 0.0

            for packet in container.demux(stream):
                for frame in packet.decode():
                    arr = frame.to_ndarray()
                    if np.issubdtype(arr.dtype, np.integer):
                        arr = arr.astype(np.float32) / np.iinfo(arr.dtype).max
                    else:
                        arr = arr.astype(np.float32)

                    if arr.ndim > 1:
                        arr = arr.mean(axis=0)

                    samples.append(arr.ravel())
                    collected_sec += frame.samples / rate
                    if collected_sec >= 12.0:
                        break
                if collected_sec >= 12.0:
                    break

            if not samples:
                return -24.0

            audio = np.concatenate(samples)
            if len(audio) < rate * 0.5:
                return -24.0

            chunk_size = int(rate * 0.05)
            n_chunks = len(audio) // chunk_size
            if n_chunks == 0:
                return -24.0

            audio_trimmed = audio[:n_chunks * chunk_size].reshape(n_chunks, chunk_size)
            rms_per_chunk = np.sqrt(np.mean(audio_trimmed ** 2, axis=1) + 1e-9)
            db_per_chunk = 20.0 * np.log10(rms_per_chunk + 1e-9)

            active_db = db_per_chunk[db_per_chunk > -50.0]
            if len(active_db) < 10:
                active_db = db_per_chunk[db_per_chunk > -65.0]
            if len(active_db) == 0:
                return -24.0

            p15 = np.percentile(active_db, 15)
            p85 = np.percentile(active_db, 85)
            core_db = active_db[(active_db >= p15) & (active_db <= p85)]

            if len(core_db) == 0:
                return float(np.mean(active_db))

            return float(np.mean(core_db))

    def analyze_track_gain(self, filepath: str):
        if not filepath or not os.path.exists(filepath):
            return

        if filepath in self.gain_cache:
            self.gain_ready.emit(filepath, self.gain_cache[filepath])
            return

        if filepath in self._analyzing:
            return
        self._analyzing.add(filepath)

        def run():
            gain = 1.0
            try:
                base_db = self._measure_base_volume_db(filepath)
                diff_db = self.target_db - base_db
                gain = math.pow(10.0, diff_db / 20.0)
                gain = max(0.35, min(3.0, gain))
            except Exception:
                gain = 1.0

            self.gain_cache[filepath] = gain
            self._analyzing.discard(filepath)
            self.gain_ready.emit(filepath, gain)

        threading.Thread(target=run, daemon=True).start()


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
                candidate = f"{cur_line} {w}".strip() if cur_line else w
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

        for i, line in enumerate(lines):
            line_w = fm.horizontalAdvance(line)
            x = (pix_w - line_w) // 2
            y = start_y + (i * line_height)

            path = QPainterPath()
            path.addText(x, y, font, line)

            shadow_offset = max(2, border_size)
            shadow_path = QPainterPath(path)
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
            p.strokePath(path, g_pen1)

            g_col2 = QColor(outline_color)
            g_col2.setAlpha(110)
            g_pen2 = QPen(g_col2)
            g_pen2.setWidth(border_size * 2 + blur * 2)
            g_pen2.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            g_pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.strokePath(path, g_pen2)

            out_pen = QPen(outline_color)
            out_pen.setWidth(border_size * 2)
            out_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            out_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.strokePath(path, out_pen)

            p.fillPath(path, QBrush(text_color))

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

        scale_factor = 1.0
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
                        char_acc += line_len
                        continue
                    elif revealed_chars < char_acc + line_len:
                        show_len = revealed_chars - char_acc
                        w_clip = self._cached_fm.horizontalAdvance(line[:show_len])
                    else:
                        w_clip = self._cached_fm.horizontalAdvance(line)
                    char_acc += line_len

                    line_w = self._cached_fm.horizontalAdvance(line)
                    lx = target_x + (self._cached_w - line_w) / 2.0 + offset_x - 10
                    ly = target_y + self._cached_pad + (line_idx * self._cached_line_h) + offset_y
                    clip_region += QRegion(QRect(int(lx), int(ly), int(w_clip + 20), int(self._cached_line_h + 10)))

                painter.setClipRegion(clip_region)

        painter.drawPixmap(int(target_x + offset_x), int(target_y + offset_y), self._cached_pixmap)


class VideoViewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.scene.addItem(self.video_item)

        self.sub_frame = SubtitleFrame(self.viewport())

        self.aspect_ratio = 16.0 / 9.0
        self.video_item.nativeSizeChanged.connect(self._on_native_size_changed)

    def _on_native_size_changed(self, size):
        if size.isValid() and size.height() > 0:
            self.aspect_ratio = float(size.width()) / float(size.height())
            self.reposition_subtitle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = self.viewport().size()
        self.scene.setSceneRect(0, 0, size.width(), size.height())
        self.video_item.setSize(QSizeF(size.width(), size.height()))
        self.reposition_subtitle()

    def get_video_presentation_rect(self) -> QRectF:
        w = self.viewport().width()
        h = self.viewport().height()
        if w <= 0 or h <= 0:
            return QRectF()

        tw = w
        th = int(w / self.aspect_ratio) if self.aspect_ratio > 0 else h
        if th > h:
            th = h
            tw = int(h * self.aspect_ratio)

        vx = (w - tw) // 2
        vy = (h - th) // 2
        return QRectF(vx, vy, tw, th)

    def reposition_subtitle(self):
        w = self.viewport().width()
        h = self.viewport().height()
        if w <= 0 or h <= 0:
            return

        v_rect = self.get_video_presentation_rect()
        if self.sub_frame.size() != self.viewport().size() or self.sub_frame.video_rect != v_rect:
            self.sub_frame.setGeometry(0, 0, w, h)
            self.sub_frame.video_rect = v_rect
            self.sub_frame._cache_dirty = True
            self.sub_frame.update()
            self.sub_frame.raise_()


class MPVProxy:
    def __init__(self, core: 'PlayerCore'):
        self._core = core

    @property
    def speed(self) -> float:
        return self._core.qplayer.playbackRate()

    @speed.setter
    def speed(self, val: float):
        self._core.qplayer.setPlaybackRate(val)

    @property
    def duration(self) -> float:
        d = self._core.qplayer.duration()
        return (d / 1000.0) if d > 0 else 0.0

    @property
    def time_pos(self) -> float:
        p = self._core.qplayer.position()
        return (p / 1000.0) if p > 0 else 0.0

    @time_pos.setter
    def time_pos(self, sec: float):
        self._core.seek(sec)

    @property
    def eof_reached(self) -> bool:
        return self._core.qplayer.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia

    @property
    def filename(self) -> str:
        return self._core.current_file or ""

    @property
    def pause(self) -> bool:
        return self._core.qplayer.playbackState() == QMediaPlayer.PlaybackState.PausedState

    @pause.setter
    def pause(self, val: bool):
        if val:
            self._core.qplayer.pause()
        else:
            self._core.qplayer.play()

    @property
    def volume(self) -> int:
        return self._core.user_volume

    @volume.setter
    def volume(self, val: int):
        self._core.set_volume(val)

    def sub_add(self, filepath: str):
        self._core.sub_manager.load_file(filepath)
        self._core.update_subtitle_display(self.time_pos)

    def command(self, cmd: str, *args):
        if cmd == 'stop':
            self._core.qplayer.stop()

    def __setitem__(self, key, value):
        pass

    def __getitem__(self, key):
        return None


class PlayerCore(QObject):
    def __init__(self, parent_video_frame):
        super().__init__()
        self.parent_frame = parent_video_frame

        self.view = VideoViewWidget(self.parent_frame)
        layout = QVBoxLayout(self.parent_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.current_file = ""
        self.sub_delay = 0.0
        self.sub_visible = True
        self.sub_config = {
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
        self._latest_frame = None

        self.user_volume = 80
        self.target_gain = 1.0
        self.current_gain = 1.0
        self.audio_norm_enabled = True

        self.normalizer = AudioNormalizer(target_base_db=-24.0)
        self.normalizer.gain_ready.connect(self._on_gain_ready)

        self.vol_smooth_timer = QTimer(self)
        self.vol_smooth_timer.setInterval(25)
        self.vol_smooth_timer.timeout.connect(self._step_volume_smoothing)

        self.qplayer = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.qplayer.setAudioOutput(self.audio_output)
        self.qplayer.setVideoOutput(self.view.video_item)

        self.video_sink = self.view.video_item.videoSink()
        if self.video_sink:
            self.video_sink.videoFrameChanged.connect(self._on_video_frame)

        self.sub_manager = SubtitleManager()
        self.qplayer.positionChanged.connect(self._on_position_changed)

        self.player = MPVProxy(self)
        self.set_volume(80)

    def preload_playlist_gains(self, playlist):
        if not self.audio_norm_enabled:
            return
        for path in playlist:
            if path and path not in self.normalizer.gain_cache:
                self.normalizer.analyze_track_gain(path)

    def _on_video_frame(self, frame: QVideoFrame):
        self._latest_frame = frame

    def _on_position_changed(self, pos_ms: int):
        self.update_subtitle_display(pos_ms / 1000.0)

    def update_subtitle_display(self, sec: float):
        if not self.sub_visible:
            self.view.sub_frame.set_text("")
            return

        text = self.sub_manager.get_text_at(sec)
        self.view.sub_frame.set_text(text)

    def reposition_subtitle(self):
        if hasattr(self, 'view') and self.view:
            self.view.reposition_subtitle()

    def get_aspect_ratio(self) -> float:
        if hasattr(self, 'view') and self.view:
            return self.view.aspect_ratio
        return 16.0 / 9.0

    def capture_ambient_frame(self, fallback_widget=None) -> QImage:
        try:
            if not self.qplayer or self.qplayer.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
                return QImage()

            if self._latest_frame and self._latest_frame.isValid():
                img = self._latest_frame.toImage()
                if img.isNull():
                    clone = QVideoFrame(self._latest_frame)
                    if clone.map(QVideoFrame.MapMode.ReadOnly):
                        try:
                            img = clone.toImage().copy()
                        finally:
                            clone.unmap()
                if not img.isNull():
                    return img.scaled(48, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

            target = fallback_widget or getattr(self, 'view', None)
            if target and target.isVisible() and target.width() > 10 and target.height() > 10:
                pix = target.grab()
                if not pix.isNull():
                    img = pix.toImage()
                    if not img.isNull():
                        return img.scaled(48, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        except Exception:
            pass
        return QImage()

    def set_hwdec(self, enabled: bool):
        pass

    def set_floating_rim(self, enabled: bool):
        pass

    def set_audio_normalization(self, enabled: bool):
        self.audio_norm_enabled = enabled
        self._apply_volume()

    def apply_subtitle_config(self, cfg: dict, visible: bool = True):
        self.sub_config.update(cfg)
        self.sub_visible = visible
        self.sub_delay = cfg.get("delay", 0.0)
        self.sub_manager.sub_delay = self.sub_delay

        if hasattr(self, 'view') and self.view:
            self.view.sub_frame.set_config(self.sub_config, self.sub_visible)
            self.view.reposition_subtitle()

        if self.player:
            self.update_subtitle_display(self.player.time_pos)

    def play(self, filepath: str):
        self.current_file = filepath

        sub_file = self._find_subtitle_file(filepath)
        if sub_file:
            self.sub_manager.load_file(sub_file)
        else:
            self.sub_manager.clear()
            self.view.sub_frame.set_text("")

        if filepath in self.normalizer.gain_cache:
            cached_gain = self.normalizer.gain_cache[filepath]
            self.target_gain = cached_gain
            self.current_gain = cached_gain
            self._apply_volume()
        else:
            self.target_gain = 1.0
            self.current_gain = 1.0
            self._apply_volume()
            if self.audio_norm_enabled:
                self.normalizer.analyze_track_gain(filepath)

        if filepath.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
            url = QUrl(filepath)
        else:
            url = QUrl.fromLocalFile(os.path.abspath(filepath))

        self.qplayer.setSource(url)
        self.qplayer.play()

    def _find_subtitle_file(self, video_path: str) -> str:
        if not video_path:
            return ""
        dirname = os.path.dirname(os.path.abspath(video_path))
        basename = os.path.splitext(os.path.basename(video_path))[0]
        sub_exts = ('.smi', '.srt', '.vtt', '.ass', '.ssa')

        for ext in sub_exts:
            p = os.path.join(dirname, basename + ext)
            if os.path.exists(p):
                return p

        try:
            files = os.listdir(dirname)
            lower_base = basename.lower()
            for f in files:
                f_base, f_ext = os.path.splitext(f)
                if f_ext.lower() in sub_exts:
                    if f_base.lower() == lower_base or f_base.lower().startswith(lower_base) or lower_base.startswith(f_base.lower()):
                        return os.path.join(dirname, f)
        except Exception:
            pass
        return ""

    def _on_gain_ready(self, filepath: str, gain: float):
        if self.current_file == filepath:
            self.target_gain = gain
            if self.qplayer.position() < 1200:
                self.current_gain = gain
                self._apply_volume()
            else:
                if not self.vol_smooth_timer.isActive():
                    self.vol_smooth_timer.start()

    def _step_volume_smoothing(self):
        diff = self.target_gain - self.current_gain
        if abs(diff) < 0.02:
            self.current_gain = self.target_gain
            self.vol_smooth_timer.stop()
        else:
            self.current_gain += diff * 0.25
        self._apply_volume()

    def _apply_volume(self):
        raw_vol = self.user_volume / 100.0
        if self.audio_norm_enabled:
            effective = raw_vol * self.current_gain
        else:
            effective = raw_vol

        clamped = max(0.0, min(1.0, effective))
        self.audio_output.setVolume(clamped)

    def pause_toggle(self) -> bool:
        if self.qplayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.qplayer.pause()
            return True
        else:
            self.qplayer.play()
            return False

    def seek(self, sec: float):
        dur = self.qplayer.duration()
        target_ms = int(max(0, sec * 1000))
        if dur > 0:
            target_ms = min(target_ms, dur)
        self.qplayer.setPosition(target_ms)
        self.update_subtitle_display(sec)

    def set_volume(self, val: int):
        self.user_volume = max(0, min(100, val))
        self._apply_volume()

    def terminate(self):
        try:
            self.vol_smooth_timer.stop()
            self.qplayer.stop()
        except Exception:
            pass