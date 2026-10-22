import os
import time
from PyQt6.QtCore import Qt, QUrl, QObject, QTimer, QRectF, QSizeF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QGraphicsView, QGraphicsScene
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoFrame
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from src.core.module import *
from src.core.subtitle_core import SubtitleFrame, SubtitleManager


class VideoViewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gl_viewport = QOpenGLWidget(self)
        self.setViewport(self.gl_viewport)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
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
            ratio = float(size.width()) / float(size.height())
            if abs(self.aspect_ratio - ratio) > 0.001:
                self.aspect_ratio = ratio
                self.reposition_subtitle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = self.viewport().size()
        w, h = size.width(), size.height()
        self.scene.setSceneRect(0, 0, w, h)
        self.video_item.setPos(0, 0)
        self.video_item.setSize(QSizeF(w, h))
        self.reposition_subtitle()

    def get_video_presentation_rect(self) -> QRectF:
        w, h = self.viewport().width(), self.viewport().height()
        if w <= 0 or h <= 0:
            return QRectF()
        ratio = self.aspect_ratio if self.aspect_ratio > 0 else 16.0 / 9.0
        tw, th = w, int(w / ratio)
        if th > h:
            th, tw = h, int(h * ratio)
        return QRectF((w - tw) // 2, (h - th) // 2, tw, th)

    def reposition_subtitle(self):
        w, h = self.viewport().width(), self.viewport().height()
        if w <= 0 or h <= 0:
            return
        v_rect = self.get_video_presentation_rect()
        if self.sub_frame.size() != self.viewport().size() or getattr(self.sub_frame, "video_rect", None) != v_rect:
            self.sub_frame.setGeometry(0, 0, w, h)
            self.sub_frame.video_rect = v_rect
            self.sub_frame._cache_dirty = True
            self.sub_frame.update()
            self.sub_frame.raise_()


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
            "font": "Pretendard, Malgun Gothic, sans-serif", "size": 44,
            "color": "#FFFFFF", "outline_color": "#000000", "border_size": 3,
            "blur": 3, "pos": 94, "bold": True, "typewriter_enabled": False,
            "typewriter_speed": 28, "fade_in_enabled": True, "fade_duration": 200,
            "slide_direction": "아래에서 위로", "slide_distance": 16,
            "anim_style": "슬라이드 & 페이드", "max_width_ratio": 0.88
        }
        self._latest_frame = None
        self._cached_ambient_img = QImage()
        self._last_ambient_capture_time = 0.0
        self._ambient_capture_interval = 0.04
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
            if path and not path.startswith(("http://", "https://", "rtsp://", "rtmp://")):
                self.normalizer.analyze_track_gain(path)

    def _on_video_frame(self, frame: QVideoFrame):
        self._latest_frame = frame if frame.isValid() else None

    def _on_position_changed(self, pos_ms: int):
        self.update_subtitle_display(pos_ms / 1000.0)

    def update_subtitle_display(self, sec: float):
        if not self.sub_visible:
            if self.view.sub_frame.text:
                self.view.sub_frame.set_text("")
            return
        self.view.sub_frame.set_text(self.sub_manager.get_text_at(sec))

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
            if now - self._last_ambient_capture_time < self._ambient_capture_interval and not self._cached_ambient_img.isNull():
                return self._cached_ambient_img
            frame = self._latest_frame
            if frame is not None and frame.isValid():
                img = frame.toImage()
                if not img.isNull():
                    self._cached_ambient_img = img.scaled(48, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                    self._last_ambient_capture_time = now
                    return self._cached_ambient_img
            target = fallback_widget or self.view
            if target and target.isVisible() and target.width() > 10 and target.height() > 10:
                pix = target.grab()
                if not pix.isNull():
                    img = pix.toImage()
                    if not img.isNull():
                        self._cached_ambient_img = img.scaled(48, 27, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
                        self._last_ambient_capture_time = now
                        return self._cached_ambient_img
        except Exception:
            pass
        return self._cached_ambient_img

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
        self.view.sub_frame.set_config(self.sub_config, self.sub_visible)
        self.view.reposition_subtitle()
        if self.player:
            self.update_subtitle_display(self.player.time_pos)

    def play(self, filepath: str):
        self.current_file = filepath
        self._latest_frame = None
        self._cached_ambient_img = QImage()
        self._last_ambient_capture_time = 0.0
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
        url = QUrl(filepath) if filepath.startswith(("http://", "https://", "rtsp://", "rtmp://")) else QUrl.fromLocalFile(os.path.abspath(filepath))
        self.qplayer.setSource(url)
        self.qplayer.play()

    def _find_subtitle_file(self, video_path: str) -> str:
        if not video_path or video_path.startswith(("http://", "https://", "rtsp://", "rtmp://")):
            return ""
        dirname = os.path.dirname(os.path.abspath(video_path))
        basename = os.path.splitext(os.path.basename(video_path))[0]
        sub_exts = (".smi", ".srt", ".vtt", ".ass", ".ssa")
        for ext in sub_exts:
            candidate = os.path.join(dirname, basename + ext)
            if os.path.exists(candidate):
                return candidate
        try:
            lower_base = basename.lower()
            for filename in os.listdir(dirname):
                file_base, file_ext = os.path.splitext(filename)
                if file_ext.lower() in sub_exts:
                    lower_file_base = file_base.lower()
                    if lower_file_base == lower_base or lower_file_base.startswith(lower_base) or lower_base.startswith(lower_file_base):
                        return os.path.join(dirname, filename)
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
        if abs(diff) < 0.02:
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
        self.update_subtitle_display(sec)

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
