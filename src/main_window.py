import os
import sys

from PyQt6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox, QMenu, QListWidgetItem
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QSize, QPropertyAnimation

from src.main_ui.dock import dock_panel
from src.main_ui.playlist import playlist_panel
from src.main_ui.top import top_bar
from src.ui.icons import ModernIcon
from src.widgets.widgets import AmbientVideoContainer, PlaylistItemCard
from src.core.player_core import PlayerCore
from src.ui.dialogs import SettingsDialog, UrlDialog
from src.mini_mode.mini import (
    reset_all_cursors, toggle_mini_mode, enter_mini_mode, exit_mini_mode,
    reposition_mini_bar, get_resize_edge, update_cursor_for_edge,
    is_in_play_click_zone
)

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
        save_session(self)
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
            return

        self.current_idx = idx
        self.core.play(target)
        self.core.player.speed = self.speed_list[self.speed_idx]
        self.btn_play.setIcon(ModernIcon.create("pause", "#FFFFFF", 22))

        self.highlight_playing_row()
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
                    self.list_set(i)
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
        d = os.path.join(os.environ.get("SCRIPT_DIR", "./"), "..")
        self.url_panel = UrlDialog(self, d)
        self.url_panel.show()

    def toggle_fullscreen(self):
        if getattr(self, "is_mini_mode", False):
            return

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
        if self.isFullScreen() or getattr(self, "is_mini_mode", False):
            self._hide_top_bar()
            return

        if pos.y() <= 50:
            if self._top_opacity.opacity() < 0.95:
                self.top_control_bar.show()
                self.top_control_bar.raise_()
                self._top_anim.stop()
                self._top_anim.setStartValue(self._top_opacity.opacity())
                self._top_anim.setEndValue(1.0)
                self._top_anim.start()
            self.top_bar_timer.start(1500)
        else:
            if self._top_opacity.opacity() > 0.05:
                self._hide_top_bar()

    def _hide_top_bar(self):
        self._top_anim.stop()
        self._top_anim.setStartValue(self._top_opacity.opacity())
        self._top_anim.setEndValue(0.0)
        self._top_anim.start()
        
    def toggle_mini_mode(self):
        toggle_mini_mode(self)

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key.Key_Space:
            self.toggle_play()
        elif k == Qt.Key.Key_Up:
            self.vol_slider.setValue(min(100, self.vol_slider.value() + 5))
        elif k == Qt.Key.Key_Down:
            self.vol_slider.setValue(max(0, self.vol_slider.value() - 5))
        elif k == Qt.Key.Key_P:
            toggle_mini_mode(self)
        elif k == Qt.Key.Key_F:
            if not getattr(self, "is_mini_mode", False):
                self.toggle_fullscreen()
        elif k == Qt.Key.Key_Escape:
            if getattr(self, "is_mini_mode", False):
                exit_mini_mode(self)
            elif self.isFullScreen():
                self.toggle_fullscreen()
        elif k == Qt.Key.Key_L and not getattr(self, "is_mini_mode", False):
            self.toggle_playlist_panel()
        elif k == Qt.Key.Key_M:
            self.toggle_mute()
        elif k == Qt.Key.Key_V:
            self.toggle_subtitle()
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
        if getattr(self, "is_mini_mode", False):
            reposition_mini_bar(self)
        if hasattr(self, 'core') and self.core:
            self.core.reposition_subtitle()
        if hasattr(self, 'dock_panel'):
            self.dock_panel.raise_()

    def mouseMoveEvent(self, event):
        pos = self.mapFromGlobal(event.globalPosition().toPoint()) if hasattr(event, 'globalPosition') else event.position().toPoint()

        if getattr(self, "is_mini_mode", False):
            if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                if pos.y() <= 36:
                    self.mini_top_bar.on_top_activity()
                else:
                    self.mini_top_bar.fast_hide()

            if getattr(self, "_mini_resize_edge", None) and (event.buttons() & Qt.MouseButton.LeftButton):
                self._handle_mini_resizing(event.globalPosition().toPoint())
                event.accept()
                return

            if not (event.buttons() & Qt.MouseButton.LeftButton):
                edge = get_resize_edge(self, pos)
                update_cursor_for_edge(self, edge)

            if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()
                return

            super().mouseMoveEvent(event)
            return

        self._check_top_bar_hover(pos)
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton) and not self.isFullScreen():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
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
                event.accept()
                return
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

    def eventFilter(self, obj, event):
        t = event.type()

        if t == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True

        if obj == self.ambient_container and self._handle_ambient_events(event):
            return True

        if self.isFullScreen() and t in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            self.show_floating_controls()

        if self._is_video_object(obj) and self._handle_video_events(event):
            return True

        return super().eventFilter(obj, event)

    def _handle_ambient_events(self, event) -> bool:
        t = event.type()

        if t not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return False

        if hasattr(event, "globalPosition"):
            pos = self.mapFromGlobal(event.globalPosition().toPoint())
        elif hasattr(event, "position"):
            pos = event.position().toPoint()
        else:
            pos = QPoint(0, 0)

        if getattr(self, "is_mini_mode", False):
            if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                if pos.y() <= 36:
                    self.mini_top_bar.on_top_activity()
                else:
                    self.mini_top_bar.fast_hide()

            if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                edge = get_resize_edge(self, pos)
                if edge:
                    self._mini_resize_edge = edge
                    self._resize_start_pos = event.globalPosition().toPoint()
                    self._resize_start_geo = self.geometry()
                    self._drag_pos = None
                    return True
                else:
                    self._mini_resize_edge = None
                    self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    return True

            elif t == QEvent.Type.MouseMove:
                if getattr(self, "_mini_resize_edge", None) and (event.buttons() & Qt.MouseButton.LeftButton):
                    self._handle_mini_resizing(event.globalPosition().toPoint())
                    return True

                if not (event.buttons() & Qt.MouseButton.LeftButton):
                    edge = get_resize_edge(self, pos)
                    update_cursor_for_edge(self, edge)

                if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
                return False

            elif t == QEvent.Type.MouseButtonRelease:
                self._mini_resize_edge = None
                self._drag_pos = None
                reset_all_cursors(self)
                return True

            return False

        if t == QEvent.Type.MouseMove:
            self._check_top_bar_hover(pos)
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

        if t == QEvent.Type.MouseMove:
            reset_all_cursors(self)

        if getattr(self, "is_mini_mode", False):
            if t == QEvent.Type.MouseMove:
                if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                    self.mini_top_bar.fast_hide()

                if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                    cur_pos = event.globalPosition().toPoint()
                    if getattr(self, "_click_start_pos", None) and (cur_pos - self._click_start_pos).manhattanLength() > 4:
                        self._pending_play_click = False
                    self.move(cur_pos - self._drag_pos)
                    return True

            elif t == QEvent.Type.MouseButtonDblClick:
                exit_mini_mode(self)
                return True

            elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._click_start_pos = event.globalPosition().toPoint()
                v_pos = self.video_frame.mapFromGlobal(event.globalPosition().toPoint())

                if is_in_play_click_zone(self.video_frame, v_pos):
                    self._pending_play_click = True
                else:
                    self._pending_play_click = False

                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True

            elif t == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if getattr(self, "_pending_play_click", False):
                    self.toggle_play()
                self._pending_play_click = False
                self._drag_pos = None
                return True

            return False

        if t == QEvent.Type.MouseMove:
            self._hide_top_bar()

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
    
    def _handle_mini_resizing(self, gpos: QPoint):
        diff = gpos - self._resize_start_pos
        geo = self._resize_start_geo
        edge = self._mini_resize_edge

        new_x, new_y = geo.x(), geo.y()
        new_w, new_h = geo.width(), geo.height()
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        if "right" in edge:
            new_w = max(min_w, geo.width() + diff.x())
        if "bottom" in edge:
            new_h = max(min_h, geo.height() + diff.y())
        if "left" in edge:
            calc_w = geo.width() - diff.x()
            if calc_w >= min_w:
                new_w = calc_w
                new_x = geo.x() + diff.x()
        if "top" in edge:
            calc_h = geo.height() - diff.y()
            if calc_h >= min_h:
                new_h = calc_h
                new_y = geo.y() + diff.y()

        self.setGeometry(new_x, new_y, new_w, new_h)
        
    def leaveEvent(self, event):
        if getattr(self, "is_mini_mode", False):
            if hasattr(self, "mini_top_bar") and self.mini_top_bar:
                self.mini_top_bar.fast_hide()
        else:
            self._hide_top_bar()
        reset_all_cursors(self)
        super().leaveEvent(event)