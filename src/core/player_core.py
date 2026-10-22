import os
from PyQt6.QtCore import Qt, QUrl, QObject, QTimer, QRectF, QSizeF
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QGraphicsView, QGraphicsScene
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoFrame
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem

from src.core.module import *

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
            if path and not path.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
                self.normalizer.analyze_track_gain(path)

    def _on_video_frame(self, frame: QVideoFrame):
        if frame.isValid():
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
        self._latest_frame = None

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
            if self.audio_norm_enabled and not filepath.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
                self.normalizer.analyze_track_gain(filepath)

        if filepath.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
            url = QUrl(filepath)
        else:
            url = QUrl.fromLocalFile(os.path.abspath(filepath))

        self.qplayer.setSource(url)
        self.qplayer.play()

    def _find_subtitle_file(self, video_path: str) -> str:
        if not video_path or video_path.startswith(('http://', 'https://', 'rtsp://', 'rtmp://')):
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
        effective = raw_vol * self.current_gain if self.audio_norm_enabled else raw_vol
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
            self._latest_frame = None
            self.normalizer._pool.shutdown(wait=False)
        except Exception:
            pass