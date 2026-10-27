import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent

from src.main_ui.dock import dock_panel
from src.main_ui.playlist import playlist_panel
from src.main_ui.top import top_bar, hide_top_bar, check_top_bar_hover
from src.ui.icons import ModernIcon
from src.widgets.backs import AmbientVideoContainer
from src.core.player_core import PlayerCore
from src.ui.dialogs import SettingsDialog, UrlDialog
from src.mini_mode.mini import (
    reset_all_cursors, toggle_mini_mode,
    reposition_mini_bar, get_resize_edge, update_cursor_for_edge,
    handle_mini_resizing
)

import src.main_logic.file as fi
import src.main_logic.timer as ti
import src.main_logic.playback as pb
import src.main_logic.playlist_ops as pl_ops
import src.main_logic.event_handler as evt_handler


class EchoMediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mine 4 PlayList")
        self.resize(1300, 820)
        self.setMinimumSize(960, 600)
        self.setMouseTracking(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._drag_pos = None
        self.playlist = []
        self.current_idx = -1
        self.playback_mode = 0
        self.is_seeking = False
        self.speed_list = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.speed_idx = 2
        self.show_remaining_time = False

        self.sub_visible = True
        self.sub_config = fi.get_default_sub_config()
        self.engine_config = fi.get_default_engine_config()

        self.init_ui()
        top_bar(self)
        self.init_engine()
        self.update_window_and_video_radius()
        
        fi.load_session(self)
        fi.save_session(self)
        fi.load_session(self)
        
        ti.timers(self)

    def init_ui(self):
        self.ambient_container = AmbientVideoContainer(self)
        self.ambient_container.setMouseTracking(True)
        self.ambient_container.installEventFilter(self)
        self.setCentralWidget(self.ambient_container)

        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: transparent; border: none;")
        self.video_frame.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.video_frame.installEventFilter(self)
        self.video_frame.setMouseTracking(True)

        dock_panel(self)
        playlist_panel(self)
        self.ambient_container.set_children_widgets(self.video_frame, self.dock_panel, self.right_box)

    def init_engine(self):
        try:
            self.core = PlayerCore(self.video_frame)
            if hasattr(self.core, 'view') and self.core.view:
                self.core.view.viewport().installEventFilter(self)
                self.core.view.installEventFilter(self)

            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_ambient_crop_margin(self.engine_config.get("ambient_crop_margin", 5) / 100.0)
            self.core.set_volume(self.vol_slider.value())
            self.core.preload_playlist_gains(self.playlist)
        except Exception as e:
            QMessageBox.critical(self, "엔진 로드 실패", f"미디어 엔진을 초기화하지 못했습니다: {e}")
            self.core = None

    def update_window_and_video_radius(self):
        cfg = self.engine_config
        vr = float(cfg.get("video_radius", 8))
        wr = 0.0 if self.isFullScreen() else float(cfg.get("window_radius", 12))

        self.ambient_container.set_video_radius(vr)
        self.ambient_container.set_window_radius(wr)
        if hasattr(self, 'core') and self.core:
            self.core.set_video_radius(vr)
        self.clearMask()

    def play_index(self, idx: int): pb.play_index(self, idx)
    def toggle_play(self): pb.toggle_play(self)
    def next_track(self): pb.next_track(self)
    def prev_track(self): pb.prev_track(self)
    def cycle_playback_mode(self): pb.cycle_playback_mode(self)
    def set_volume(self, val): pb.set_volume(self, val)
    def toggle_mute(self): pb.toggle_mute(self)
    def toggle_subtitle(self): pb.toggle_subtitle(self)

    def refresh_playlist_view(self): pl_ops.refresh_playlist_view(self)
    def highlight_playing_row(self): pl_ops.highlight_playing_row(self)
    def on_item_double_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path in self.playlist:
            self.play_index(self.playlist.index(path))
    def handle_dropped_files(self, paths): pl_ops.handle_dropped_files(self, paths)
    def open_media_files(self): pl_ops.open_media_files(self)
    def show_context_menu(self, pos: QPoint): pl_ops.show_context_menu(self, pos)

    def apply_settings(self, sub_cfg: dict, eng_cfg: dict):
        self.sub_config, self.engine_config = sub_cfg, eng_cfg
        if self.core:
            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_hwdec(self.engine_config.get("hwdec", True))
            self.core.set_ambient_crop_margin(self.engine_config.get("ambient_crop_margin", 5) / 100.0)
        self.ambient_container.set_ambient_params(self.engine_config)
        self.update_window_and_video_radius()
        fi.save_session(self)

    def open_settings(self):
        if hasattr(self, 'settings_panel') and self.settings_panel and self.settings_panel.isVisible():
            self.settings_panel.raise_()
            self.settings_panel.activateWindow()
            return
        self.settings_panel = SettingsDialog(self)
        self.settings_panel.show()

    def open_url_dialog(self):
        if hasattr(self, 'url_panel') and self.url_panel and self.url_panel.isVisible():
            self.url_panel.raise_()
            self.url_panel.activateWindow()
            return
        d = os.path.join(os.environ.get("SCRIPT_DIR", "./"), "..")
        self.url_panel = UrlDialog(self, d)
        self.url_panel.show()

    def toggle_fullscreen(self):
        if getattr(self, "is_mini_mode", False):
            return
        if self.isFullScreen():
            self.showNormal()
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.ambient_container.set_playlist_visibility(True)
            self.fs_timer.stop()
            self.show_floating_controls()
            self.btn_fs.setIcon(ModernIcon.create("fullscreen", "#FFFFFF", 20))
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.showFullScreen()
            self.ambient_container.set_playlist_visibility(False)
            self.btn_fs.setIcon(ModernIcon.create("restore", "#FFFFFF", 20))
            self.show_floating_controls()

        self.update_window_and_video_radius()
        QTimer.singleShot(60, lambda: self.core.reposition_subtitle() if self.core else None)

    def show_floating_controls(self):
        self.dock_panel.show()
        self.unsetCursor()
        self.video_frame.unsetCursor()
        self.ambient_container.unsetCursor()
        if self.isFullScreen():
            self.fs_timer.start(3000)

    def toggle_playlist_panel(self):
        self.ambient_container.set_playlist_visibility(not self.ambient_container.playlist_visible)
        QTimer.singleShot(60, lambda: self.core.reposition_subtitle() if self.core else None)

    def toggle_mini_mode(self):
        toggle_mini_mode(self)
        self.update_window_and_video_radius()

    def keyPressEvent(self, event):
        if not evt_handler.handle_key_press(self, event):
            super().keyPressEvent(event)

    def closeEvent(self, event):
        fi.save_session(self)
        if self.core:
            self.core.terminate()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_window_and_video_radius()
        if hasattr(self, 'top_control_bar'):
            bx = (self.width() - self.top_control_bar.width()) // 2
            self.top_control_bar.move(bx, 12)
        if getattr(self, "is_mini_mode", False):
            reposition_mini_bar(self)
        if hasattr(self, 'core') and self.core:
            self.core.reposition_subtitle()
        if hasattr(self, 'dock_panel'):
            self.dock_panel.raise_()

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition().toPoint()
        pos = self.mapFromGlobal(gpos)

        if getattr(self, "is_mini_mode", False):
            if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                if pos.y() <= 36:
                    self.mini_top_bar.on_top_activity()
                else:
                    self.mini_top_bar.fast_hide()

            if getattr(self, "_mini_resize_edge", None) and (event.buttons() & Qt.MouseButton.LeftButton):
                handle_mini_resizing(self, gpos)
                event.accept()
                return

            if not (event.buttons() & Qt.MouseButton.LeftButton):
                edge = get_resize_edge(self, pos)
                update_cursor_for_edge(self, edge)

            if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                self.move(gpos - self._drag_pos)
                event.accept()
                return
            super().mouseMoveEvent(event)
            return

        check_top_bar_hover(self, pos)
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton) and not self.isFullScreen():
            self.move(gpos - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if getattr(self, "is_mini_mode", False) and event.button() == Qt.MouseButton.LeftButton:
            edge = get_resize_edge(self, event.position().toPoint())
            if edge:
                self._mini_resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geo = self.geometry()
            else:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._mini_resize_edge = None
        self._drag_pos = None
        self.unsetCursor()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if getattr(self, "is_mini_mode", False):
            if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                self.mini_top_bar.fast_hide()
        else:
            hide_top_bar(self)
        reset_all_cursors(self)
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            return evt_handler.handle_key_press(self, event)

        if obj == self.ambient_container and evt_handler.handle_ambient_events(self, event):
            return True

        if self.isFullScreen() and event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            self.show_floating_controls()

        if evt_handler.is_video_object(self, obj) and evt_handler.handle_video_events(self, event):
            return True

        return super().eventFilter(obj, event)
    
    def _update_sub_icon(self):
        pb.update_sub_icon(self)