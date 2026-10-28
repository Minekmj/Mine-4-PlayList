import os
import time
from PyQt6.QtCore import Qt, QUrl, QObject, QTimer, QRectF, QSizeF
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPen, QBrush, QSurfaceFormat
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QGraphicsView, QGraphicsScene, QGraphicsPathItem, QGraphicsItem
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoFrame
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from src.core.module import *
from src.core.subtitle_core import SubtitleFrame, SubtitleManager

SUBTITLE_MAX_FPS = 30

_env_opengl = os.environ.get("mine4playlist_use_opengl_video", "False")
IS_OPENGL = _env_opengl == "True"

class VideoViewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.corner_radius = 8.0
        self.on_aspect_ratio_changed = None
        self.aspect_ratio = 16.0 / 9.0

        if IS_OPENGL:
            try:
                fmt = QSurfaceFormat()
                fmt.setStencilBufferSize(8)
                fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)

                self.gl_widget = QOpenGLWidget(self)
                self.gl_widget.setFormat(fmt)
                self.setViewport(self.gl_widget)
                
            except Exception:
                self.setViewport(None)
        else:
            self.setViewport(None)

        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)

        if not IS_OPENGL:
            self.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.clip_item = QGraphicsPathItem()
        self.clip_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        self.clip_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.clip_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.scene.addItem(self.clip_item)

        self.video_item = QGraphicsVideoItem()
        self.video_item.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
        self.video_item.setParentItem(self.clip_item)

        self.sub_frame = SubtitleFrame(self.viewport())
        self.video_item.nativeSizeChanged.connect(self._on_native_size_changed)

    def _on_native_size_changed(self, size):
        if size.isValid() and size.height() > 0:
            ratio = float(size.width()) / float(size.height())
            if abs(self.aspect_ratio - ratio) > 0.001:
                self.aspect_ratio = ratio
                self._update_clipping_shape()
                self.reposition_subtitle()
                if self.on_aspect_ratio_changed and callable(self.on_aspect_ratio_changed):
                    self.on_aspect_ratio_changed(ratio)

    def get_video_presentation_rect(self) -> QRectF:
        vp = self.viewport()
        w, h = vp.width(), vp.height()
        if w <= 0 or h <= 0:
            return QRectF()
        return QRectF(0.0, 0.0, float(w), float(h))

    def set_corner_radius(self, radius: float):
        radius = max(0.0, float(radius))
        if abs(self.corner_radius - radius) > 0.01:
            self.corner_radius = radius
            self._update_clipping_shape()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        vp = self.viewport()
        w, h = vp.width(), vp.height()
        if w <= 0 or h <= 0:
            return

        self.scene.setSceneRect(0, 0, w, h)
        self.video_item.setPos(0, 0)
        self.video_item.setSize(QSizeF(w, h))
        self._update_clipping_shape()
        self.reposition_subtitle()

    def _update_clipping_shape(self):
        vp = self.viewport()
        w, h = vp.width(), vp.height()
        if w <= 0 or h <= 0:
            return
        
        path = QPainterPath()
        if self.corner_radius > 0.5:
            r = min(self.corner_radius, w / 2.0, h / 2.0)
            path.addRoundedRect(QRectF(0, 0, w, h), r, r)
        else:
            path.addRect(QRectF(0, 0, w, h))
        self.clip_item.setPath(path)

    def reposition_subtitle(self):
        vp = self.viewport()
        w, h = vp.width(), vp.height()
        if w <= 0 or h <= 0:
            return
        
        v_rect = self.get_video_presentation_rect()
        if self.sub_frame.size() != vp.size() or getattr(self.sub_frame, "video_rect", None) != v_rect:
            self.sub_frame.setGeometry(0, 0, w, h)
            self.sub_frame.video_rect = v_rect
            self.sub_frame._cache_dirty = True
            self.sub_frame.update()
            self.sub_frame.raise_()


class PlayerCore(QObject):
    def __init__(self, parent_video_frame):
        super().__init__()
        self.parent_frame = parent_video_frame
        self.parent_frame.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.hwdec_enabled = True
        self.ambient_crop_margin = 0.05
        self.fps_subtitle = SUBTITLE_MAX_FPS

        self.view = VideoViewWidget(self.parent_frame)
        self.view.on_aspect_ratio_changed = self._on_aspect_ratio_changed

        layout = QVBoxLayout(self.parent_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self.current_file = ""
        self.sub_delay = 0.0
        self.sub_visible = True
        self.sub_config = {
            "font": "Pretendard, Malgun Gothic, sans-serif", "size": 44,
            "color": "#FFFFFF", "outline_color": "#000000", "border_size": 3,
            "blur": 3, "pos": 94, "bold": True, "typewriter_enabled": False,
            "typewriter_speed": 28, "fade_in_enabled": True, "fade_duration": 200,
            "slide_direction": "아래에서 위로", "slide_distance": 16,
            "anim_style": "슬라이드 & 페이드", "max_width_ratio": 0.88,
            "shadow_enabled": True, "shadow_color": "#000000", "shadow_opacity": 0.75,
            "shadow_offset": 4, "shadow_blur": 4
        }

        self._latest_frame = None
        self._last_ambient_frame_time = -1
        self._cached_ambient_img = QImage()
        self._last_ambient_capture_time = 0.0
        self._last_sub_update_time = 0.0

        self.user_volume = 80
        self.target_gain = 1.0
        self.current_gain = 1.0
        self.audio_norm_enabled = True

        self.normalizer = AudioNormalizer()
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

    def _on_aspect_ratio_changed(self, ratio: float):
        container = self.parent_frame.parent()
        if container and hasattr(container, "set_aspect_ratio"):
            container.set_aspect_ratio(ratio)

    def set_video_radius(self, radius: float):
        if self.view:
            self.view.set_corner_radius(radius)

    def set_ambient_crop_margin(self, pct: float):
        self.ambient_crop_margin = max(0.0, min(0.30, float(pct)))

    def set_subtitle_fps(self, fps: int):
        self.fps_subtitle = max(1, min(60, int(fps)))

    def preload_playlist_gains(self, playlist):
        if not self.audio_norm_enabled:
            return
        for path in playlist:
            if path and not path.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                self.normalizer.analyze_track_gain(path)

    def _on_video_frame(self, frame: QVideoFrame):
        self._latest_frame = frame if (frame and frame.isValid()) else None

    def _on_position_changed(self, pos_ms: int):
        self.update_subtitle_display(pos_ms / 1000.0)

    def update_subtitle_display(self, sec: float, force: bool = False):
        if not self.sub_visible:
            if self.view.sub_frame.text:
                self.view.sub_frame.set_text("")
            return

        now = time.monotonic()
        min_sub_interval = 1.0 / max(1, self.fps_subtitle)
        if not force and (now - self._last_sub_update_time < min_sub_interval):
            return

        target_text = self.sub_manager.get_text_at(sec)
        if force or (target_text != self.view.sub_frame.text):
            self.view.sub_frame.set_text(target_text)
            self._last_sub_update_time = now

    def reposition_subtitle(self):
        if getattr(self, "view", None):
            self.view.reposition_subtitle()

    def get_aspect_ratio(self) -> float:
        return self.view.aspect_ratio if getattr(self, "view", None) else 16.0 / 9.0

    def capture_ambient_frame(self, fallback_widget=None) -> QImage:
        try:
            if not self.qplayer or self.qplayer.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
                return QImage()
            
            now = time.monotonic()
            container = self.parent_frame.parent() if self.parent_frame else None
            target_fps = getattr(container, "fps_ambient", 25) if container else 25
            capture_interval = 1.0 / max(1, target_fps)

            if (now - self._last_ambient_capture_time < capture_interval) and not self._cached_ambient_img.isNull():
                return self._cached_ambient_img

            frame = self._latest_frame
            if frame is None or not frame.isValid():
                return self._cached_ambient_img

            frame_time = frame.startTime()
            if frame_time != -1 and frame_time == self._last_ambient_frame_time and not self._cached_ambient_img.isNull():
                return self._cached_ambient_img

            img = frame.toImage()
            if img.isNull():
                return self._cached_ambient_img

            cw, ch = img.width(), img.height()
            margin_pct = getattr(self, "ambient_crop_margin", 0.05)
            
            if margin_pct > 0.001:
                mx = int(cw * margin_pct)
                my = int(ch * margin_pct)
                src_rect = QRectF(mx, my, cw - 2 * mx, ch - 2 * my) if (cw - 2 * mx > 10 and ch - 2 * my > 10) else QRectF(0, 0, cw, ch)
            else:
                src_rect = QRectF(0, 0, cw, ch)

            thumb = QImage(48, 27, QImage.Format.Format_RGB32)
            p = QPainter(thumb)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            p.drawImage(QRectF(0, 0, 48, 27), img, src_rect)
            p.end()

            self._cached_ambient_img = thumb
            self._last_ambient_capture_time = now
            self._last_ambient_frame_time = frame_time
            return self._cached_ambient_img

        except Exception:
            return self._cached_ambient_img

    def set_hwdec(self, enabled: bool):
        self.hwdec_enabled = enabled
        if enabled:
            os.environ.pop("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", None)
            os.environ.pop("QT_DISABLE_HW_TEXTURES_CONVERSION", None)
        else:
            os.environ["QT_FFMPEG_DECODING_HW_DEVICE_TYPES"] = ""
            os.environ["QT_DISABLE_HW_TEXTURES_CONVERSION"] = "1"

        if self.player is not None:
            try:
                self.player.set_hwdec(enabled)
                self.player.hwdec = "auto" if enabled else "no"
                self.player.set_property("hwdec", "auto" if enabled else "no")
            except Exception:
                pass

        if self.current_file and self.qplayer.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            current_pos = self.qplayer.position()
            is_playing = (self.qplayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

            def _on_restored_media_loaded(status):
                if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
                    try:
                        self.qplayer.mediaStatusChanged.disconnect(_on_restored_media_loaded)
                    except Exception:
                        pass
                    self.qplayer.setPosition(current_pos)
                    if is_playing:
                        self.qplayer.play()
                    else:
                        self.qplayer.pause()
                elif status == QMediaPlayer.MediaStatus.InvalidMedia:
                    try:
                        self.qplayer.mediaStatusChanged.disconnect(_on_restored_media_loaded)
                    except Exception:
                        pass

            try:
                self.qplayer.mediaStatusChanged.connect(_on_restored_media_loaded)
            except Exception:
                pass

            url = (
                QUrl(self.current_file)
                if self.current_file.startswith(("http://", "https://", "rtsp://", "rtmp://"))
                else QUrl.fromLocalFile(os.path.abspath(self.current_file))
            )
            self.qplayer.setSource(url)

    def set_audio_normalization(self, enabled: bool):
        self.audio_norm_enabled = enabled
        self._apply_volume()

    def apply_subtitle_config(self, cfg: dict, visible: bool = True):
        self.sub_config.update(cfg)
        self.sub_visible = visible
        self.sub_delay = cfg.get("delay", 0.0)
        self.sub_manager.sub_delay = self.sub_delay
        if "fps_subtitle" in cfg:
            self.fps_subtitle = max(1, min(60, int(cfg["fps_subtitle"])))
        self.view.sub_frame.set_config(self.sub_config, self.sub_visible)
        self.view.reposition_subtitle()
        if self.player:
            time_pos = getattr(self.player, "time_pos", 0.0) or 0.0
            self.update_subtitle_display(time_pos, force=True)

    def play(self, filepath: str):
        self.current_file = filepath
        self._latest_frame = None
        self._cached_ambient_img = QImage()
        self._last_ambient_frame_time = -1
        self._last_ambient_capture_time = 0.0
        self._last_sub_update_time = 0.0

        sub_file = self._find_subtitle_file(filepath)
        if sub_file:
            self.sub_manager.load_file(sub_file)
        else:
            self.sub_manager.clear()
            self.view.sub_frame.set_text("")

        with self.normalizer._lock:
            cached_gain = self.normalizer.gain_cache.get(filepath)
            
        if cached_gain is not None:
            self.target_gain = cached_gain
            self.current_gain = cached_gain
            self._apply_volume()
        else:
            self.target_gain = 1.0
            self.current_gain = 1.0
            self._apply_volume()
            if self.audio_norm_enabled and not filepath.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                self.normalizer.analyze_track_gain(filepath)

        url = (
            QUrl(filepath)
            if filepath.startswith(("http://", "https://", "rtsp://", "rtmp://"))
            else QUrl.fromLocalFile(os.path.abspath(filepath))
        )
        self.qplayer.setSource(url)
        self.qplayer.play()

    def _find_subtitle_file(self, video_path: str) -> str:
        if not video_path or video_path.startswith(("http://", "https://", "rtsp://", "rtmp://")):
            return ""

        dirname, filename = os.path.split(os.path.abspath(video_path))
        basename, _ = os.path.splitext(filename)
        sub_exts = (".smi", ".srt", ".vtt", ".ass", ".ssa")

        for ext in sub_exts:
            candidate = os.path.join(dirname, basename + ext)
            if os.path.isfile(candidate):
                return candidate

        try:
            lower_base = basename.lower()
            with os.scandir(dirname) as entries:
                for entry in entries:
                    if entry.is_file():
                        f_base, f_ext = os.path.splitext(entry.name)
                        if f_ext.lower() in sub_exts:
                            lower_f_base = f_base.lower()
                            if lower_f_base == lower_base or lower_f_base.startswith(lower_base) or lower_base.startswith(lower_f_base):
                                return entry.path
        except OSError:
            pass

        return ""

    def _on_gain_ready(self, filepath: str, gain: float):
        if self.current_file != filepath:
            return
        self.target_gain = gain
        if self.qplayer.position() < 1200:
            self.current_gain = gain
            self._apply_volume()
        elif not self.vol_smooth_timer.isActive():
            self.vol_smooth_timer.start()

    def _step_volume_smoothing(self):
        diff = self.target_gain - self.current_gain
        if abs(diff) < 0.01:
            self.current_gain = self.target_gain
            self.vol_smooth_timer.stop()
        else:
            self.current_gain += diff * 0.25
        self._apply_volume()

    def _apply_volume(self):
        raw_vol = self.user_volume / 100.0
        effective = raw_vol * self.current_gain if self.audio_norm_enabled else raw_vol
        self.audio_output.setVolume(max(0.0, min(1.0, effective)))

    def pause_toggle(self) -> bool:
        if self.qplayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.qplayer.pause()
            return True
        self.qplayer.play()
        return False

    def seek(self, sec: float):
        dur = self.qplayer.duration()
        target_ms = max(0, int(sec * 1000))
        if dur > 0:
            target_ms = min(target_ms, dur)
        self.qplayer.setPosition(target_ms)
        self.update_subtitle_display(sec, force=True)

    def set_volume(self, val: int):
        self.user_volume = max(0, min(100, val))
        self._apply_volume()

    def terminate(self):
        self.vol_smooth_timer.stop()
        try:
            self.qplayer.stop()
        except Exception:
            pass
        self._latest_frame = None
        self._cached_ambient_img = QImage()
        try:
            self.normalizer._pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            try:
                self.normalizer._pool.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass