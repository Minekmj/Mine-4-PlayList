import os
import sys

from PyQt6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox, QMenu, QListWidgetItem
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QSize, QPropertyAnimation

from src.main_ui.dock import dock_panel
from src.main_ui.playlist import playlist_panel
from src.main_ui.top import top_bar
from src.ui.icons import ModernIcon
from src.widgets.widgets import AmbientVideoContainer, FloatingOSD, PlaylistItemCard
from src.core.player_core import PlayerCore
from src.ui.dialogs import SettingsDialog, UrlDialog

from src.main_logic.file import *
from src.main_logic.timer import *

class EchoMediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mine 4 PlayList")
        self.resize(1300, 820)
        self.setMinimumSize(960, 600)
        self.setMouseTracking(True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._drag_pos = None

        self.playlist = []
        self.current_idx = -1
        self.playback_mode = 0
        self.is_seeking = False
        self.speed_list = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.speed_idx = 2
        self.show_remaining_time = False

        self.sub_visible = True
        self.sub_config = get_default_sub_config()
        self.engine_config = get_default_engine_config()

        self.init_ui()
        top_bar(self)
        self.init_engine()
        load_session(self)
        timers(self)

    def init_ui(self):
        self.ambient_container = AmbientVideoContainer(self)
        self.ambient_container.setMouseTracking(True)
        self.ambient_container.installEventFilter(self)
        self.setCentralWidget(self.ambient_container)

        self.video_frame = QWidget()
        self.video_frame.setStyleSheet("background-color: transparent; border: none;")
        self.video_frame.installEventFilter(self)
        self.video_frame.setMouseTracking(True)
        self.osd = FloatingOSD(self.video_frame)

        dock_panel(self)
        playlist_panel(self)

        self.ambient_container.set_children_widgets(self.video_frame, self.dock_panel, self.right_box)

    def init_engine(self):
        try:
            self.core = PlayerCore(self.video_frame)
            if hasattr(self.core, 'view') and self.core.view:
                self.core.view.viewport().installEventFilter(self)
                self.core.view.installEventFilter(self)
            if hasattr(self, 'osd'):
                self.osd.raise_()

            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_volume(self.vol_slider.value())
            self.core.preload_playlist_gains(self.playlist)
        except Exception as e:
            QMessageBox.critical(self, "엔진 로드 실패", f"미디어 엔진을 초기화하지 못했습니다: {e}")
            self.core = None

    def play_index(self, idx: int):
        if not self.core or not (0 <= idx < len(self.playlist)):
            return
        target = self.playlist[idx]
        if not os.path.exists(target):
            self.osd.show_message("파일을 찾을 수 없습니다.")
            return

        self.current_idx = idx
        self.core.play(target)
        self.core.player.speed = self.speed_list[self.speed_idx]
        self.btn_play.setIcon(ModernIcon.create("pause", "#FFFFFF", 22))

        self.highlight_playing_row()
        self.osd.show_message(f"{os.path.basename(target)}")
        save_session(self)

    def toggle_play(self):
        if not self.core or not self.playlist:
            return
        if self.current_idx == -1:
            self.next_track()
            return
        paused = self.core.pause_toggle()
        icon = "play" if paused else "pause"
        self.btn_play.setIcon(ModernIcon.create(icon, "#FFFFFF", 22))

    def next_track(self):
        next_idx = get_next_track_index(self.current_idx, len(self.playlist), self.playback_mode)
        if next_idx is not None:
            self.play_index(next_idx)

    def prev_track(self):
        prev_idx = get_prev_track_index(self.current_idx, len(self.playlist), self.playback_mode)
        if prev_idx is not None:
            self.play_index(prev_idx)

    def cycle_playback_mode(self):
        self.playback_mode = (self.playback_mode + 1) % len(PLAYBACK_MODE_NAMES)
        self.btn_mode.setText(PLAYBACK_MODE_NAMES[self.playback_mode])
        save_session(self)

    def on_seek_pressed(self):
        self.is_seeking = True

    def on_seek_moved(self, val):
        if self.core and self.core.player.duration:
            target = (val / 1000.0) * self.core.player.duration
            self.lbl_cur_time.setText(format_time(target))

    def on_seek_released(self):
        if self.core and self.core.player.duration:
            pos = (self.seek_slider.value() / 1000.0) * self.core.player.duration
            self.core.seek(pos)
        self.is_seeking = False

    def set_volume(self, val):
        if self.core:
            self.core.set_volume(val)
        icon_name = "mute" if val == 0 else "volume"
        icon_color = "#F43F5E" if val == 0 else "#FFFFFF"
        self.btn_vol.setIcon(ModernIcon.create(icon_name, icon_color, 20))

    def toggle_mute(self):
        if self.vol_slider.value() > 0:
            self._prev_vol = self.vol_slider.value()
            self.vol_slider.setValue(0)
        else:
            self.vol_slider.setValue(getattr(self, '_prev_vol', 70))

    def _update_sub_icon(self):
        icon_name = "subtitle" if self.sub_visible else "subtitle_off"
        icon_color = "#FFFFFF" if self.sub_visible else "#94A3B8"
        self.btn_sub_toggle.setIcon(ModernIcon.create(icon_name, icon_color, 20))
        self.btn_sub_toggle.setToolTip("자막 끄기" if self.sub_visible else "자막 켜기")

    def toggle_subtitle(self):
        self.sub_visible = not self.sub_visible
        self._update_sub_icon()
        if self.core:
            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
        save_session(self)

    def apply_settings(self, sub_cfg: dict, eng_cfg: dict):
        self.sub_config = sub_cfg
        self.engine_config = eng_cfg

        if self.core:
            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_hwdec(self.engine_config.get("hwdec", True))

        self.ambient_container.set_ambient_params(self.engine_config)
        save_session(self)

    def refresh_playlist_view(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for idx, path in enumerate(self.playlist):
            title = os.path.splitext(os.path.basename(path))[0]
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 44))
            item.setData(Qt.ItemDataRole.UserRole, path)

            card = PlaylistItemCard(
                item=item,
                title=f"{idx + 1:02d}.  {title}",
                on_play_callback=self.on_item_double_click
            )
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

        self.list_widget.blockSignals(False)
        self.lbl_list_count.setText(f"({len(self.playlist)})")
        self.highlight_playing_row()

        if hasattr(self, 'core') and self.core:
            self.core.preload_playlist_gains(self.playlist)

    def highlight_playing_row(self):
        if 0 <= self.current_idx < len(self.playlist):
            cur = self.playlist[self.current_idx]
            for i in range(self.list_widget.count()):
                it = self.list_widget.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == cur:
                    self.list_widget.setCurrentRow(i)
                    break

    def on_item_double_click(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path in self.playlist:
            self.play_index(self.playlist.index(path))

    def handle_dropped_files(self, paths):
        added = collect_media_files(paths)
        if added:
            start_first = len(self.playlist) == 0
            for item in added:
                if item not in self.playlist:
                    self.playlist.append(item)
            self.refresh_playlist_view()
            save_session(self)
            if start_first:
                self.play_index(0)

    def open_media_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "파일 선택", "",
            "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.flac *.wav)"
        )
        if files:
            self.handle_dropped_files(files)

    def show_context_menu(self, pos: QPoint):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        a_play = menu.addAction("재생")
        a_show = menu.addAction("파일 위치 탐색기에서 열기")
        menu.addSeparator()
        a_sub = menu.addAction("수동 자막 연결 (.smi, .srt, .vtt, .ass)")
        a_del = menu.addAction("목록에서 삭제")

        act = menu.exec(self.list_widget.mapToGlobal(pos))
        path = item.data(Qt.ItemDataRole.UserRole)
        if act == a_play:
            self.on_item_double_click(item)
        elif act == a_show and sys.platform.startswith('win'):
            os.system(f'explorer /select,"{os.path.abspath(path)}"')
        elif act == a_sub:
            s_file, _ = QFileDialog.getOpenFileName(
                self, "자막 선택", os.path.dirname(path),
                "Subtitles (*.smi *.srt *.vtt *.ass *.ssa)"
            )
            if s_file and self.core:
                self.core.player.sub_add(s_file)
        elif act == a_del:
            if path in self.playlist:
                i = self.playlist.index(path)
                self.playlist.pop(i)
                if self.current_idx == i:
                    self.current_idx = -1
                elif self.current_idx > i:
                    self.current_idx -= 1
                self.refresh_playlist_view()
                save_session(self)
                
    def open_settings(self):
        if hasattr(self, 'settings_panel') and self.settings_panel is not None and self.settings_panel.isVisible():
            self.settings_panel.raise_()
            self.settings_panel.activateWindow()
            return
        self.settings_panel = SettingsDialog(self)
        self.settings_panel.show()

    def open_url_dialog(self):
        if hasattr(self, 'url_panel') and self.url_panel is not None and self.url_panel.isVisible():
            self.url_panel.raise_()
            self.url_panel.activateWindow()
            return
        d = os.path.join(os.environ.get("SCRIPT_DIR", "./"), "Download")
        self.url_panel = UrlDialog(self, d)
        self.url_panel.show()

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.ambient_container.set_playlist_visibility(True)
            self.fs_timer.stop()
            self.show_floating_controls()
            self.btn_fs.setIcon(ModernIcon.create("fullscreen", "#FFFFFF", 20))
        else:
            self.showFullScreen()
            self.ambient_container.set_playlist_visibility(False)
            self.btn_fs.setIcon(ModernIcon.create("restore", "#FFFFFF", 20))
            self.show_floating_controls()

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

    def _check_top_bar_hover(self, pos: QPoint):
        if self.isFullScreen():
            self._hide_top_bar()
            return

        if pos.y() <= 60:
            self.top_bar_timer.stop()
            if self._top_opacity.opacity() < 0.95 and self._top_anim.state() != QPropertyAnimation.State.Running:
                self.top_control_bar.show()
                self.top_control_bar.raise_()
                self._top_anim.stop()
                self._top_anim.setStartValue(self._top_opacity.opacity())
                self._top_anim.setEndValue(1.0)
                self._top_anim.start()
        else:
            if self._top_opacity.opacity() > 0.05 and not self.top_bar_timer.isActive():
                self.top_bar_timer.start()

    def _hide_top_bar(self):
        self._top_anim.stop()
        self._top_anim.setStartValue(self._top_opacity.opacity())
        self._top_anim.setEndValue(0.0)
        self._top_anim.start()

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key.Key_Space:
            self.toggle_play()
        elif k == Qt.Key.Key_Up:
            self.vol_slider.setValue(min(100, self.vol_slider.value() + 5))
        elif k == Qt.Key.Key_Down:
            self.vol_slider.setValue(max(0, self.vol_slider.value() - 5))
        elif k == Qt.Key.Key_F:
            self.toggle_fullscreen()
        elif k == Qt.Key.Key_L:
            self.toggle_playlist_panel()
        elif k == Qt.Key.Key_M:
            self.toggle_mute()
        elif k == Qt.Key.Key_V:
            self.toggle_subtitle()
        elif k == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        save_session(self)
        if self.core:
            self.core.terminate()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'top_control_bar'):
            bx = (self.width() - self.top_control_bar.width()) // 2
            self.top_control_bar.move(bx, 12)
        if hasattr(self, 'core') and self.core:
            self.core.reposition_subtitle()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isFullScreen():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._check_top_bar_hover(event.position().toPoint())

        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton) and not self.isFullScreen():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return

        if self.isFullScreen():
            self.show_floating_controls()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.ambient_container and self._handle_ambient_events(event):
            return True

        if self.isFullScreen() and event.type() in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            self.show_floating_controls()

        if self._is_video_object(obj) and self._handle_video_events(event):
            return True

        return super().eventFilter(obj, event)

    def _handle_ambient_events(self, event) -> bool:
        t = event.type()
        if t == QEvent.Type.MouseMove:
            self._check_top_bar_hover(event.position().toPoint())
            if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton) and not self.isFullScreen():
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
        elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            if not self.isFullScreen():
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif t == QEvent.Type.MouseButtonRelease:
            self._drag_pos = None
        return False

    def _is_video_object(self, obj) -> bool:
        target_view = getattr(self.core, 'view', None) if getattr(self, 'core', None) else None
        target_viewport = target_view.viewport() if target_view else None
        return obj in (self.video_frame, target_view, target_viewport)

    def _handle_video_events(self, event) -> bool:
        t = event.type()
        if t == QEvent.Type.MouseButtonDblClick:
            self.toggle_fullscreen()
            return True
        elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.toggle_play()
            return True
        elif t == QEvent.Type.Wheel:
            step = 4 if event.angleDelta().y() > 0 else -4
            self.vol_slider.setValue(max(0, min(100, self.vol_slider.value() + step)))
            return True
        return False