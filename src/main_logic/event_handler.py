from PyQt6.QtCore import Qt, QPoint, QEvent
from src.mini_mode.mini import (
    reset_all_cursors, exit_mini_mode, get_resize_edge,
    update_cursor_for_edge, is_in_play_click_zone, handle_mini_resizing
)
from src.main_ui.top import check_top_bar_hover, hide_top_bar

def is_video_object(self, obj) -> bool:
    target_view = getattr(self.core, 'view', None) if getattr(self, 'core', None) else None
    target_viewport = target_view.viewport() if target_view else None
    return obj in (self.video_frame, target_view, target_viewport)

def handle_ambient_events(self, event) -> bool:
    t = event.type()
    if t not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
        return False

    pos = self.mapFromGlobal(event.globalPosition().toPoint())

    if getattr(self, "is_mini_mode", False):
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
            else:
                self._mini_resize_edge = None
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            return True

        elif t == QEvent.Type.MouseMove:
            if getattr(self, "_mini_resize_edge", None) and (event.buttons() & Qt.MouseButton.LeftButton):
                handle_mini_resizing(self, event.globalPosition().toPoint())
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
        check_top_bar_hover(self, pos)
        if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton) and not self.isFullScreen():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return True
    elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
        if not self.isFullScreen():
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    elif t == QEvent.Type.MouseButtonRelease:
        self._drag_pos = None

    return False

def handle_video_events(self, event) -> bool:
    t = event.type()
    if t == QEvent.Type.MouseMove:
        reset_all_cursors(self)

    if getattr(self, "is_mini_mode", False):
        if t == QEvent.Type.MouseMove:
            self.mini_top_bar.fast_hide()
            
            if self._drag_pos and (event.buttons() & Qt.MouseButton.LeftButton):
                cur_pos = event.globalPosition().toPoint()
                if getattr(self, "_click_start_pos", None) and (cur_pos - self._click_start_pos).manhattanLength() > 4:
                    self._pending_play_click = False
                self.move(cur_pos - self._drag_pos)
                return True

        elif t == QEvent.Type.MouseButtonDblClick:
            exit_mini_mode(self)
            self.update_window_and_video_radius()
            return True

        elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._click_start_pos = event.globalPosition().toPoint()
            v_pos = self.video_frame.mapFromGlobal(event.globalPosition().toPoint())
            self._pending_play_click = is_in_play_click_zone(self.video_frame, v_pos)
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
        hide_top_bar(self)
    elif t == QEvent.Type.MouseButtonDblClick:
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

def handle_key_press(self, event) -> bool:
    k = event.key()
    if k == Qt.Key.Key_Space:
        self.toggle_play()
    elif k == Qt.Key.Key_Up:
        self.vol_slider.setValue(min(100, self.vol_slider.value() + 5))
    elif k == Qt.Key.Key_Down:
        self.vol_slider.setValue(max(0, self.vol_slider.value() - 5))
    elif k == Qt.Key.Key_P:
        self.toggle_mini_mode()
    elif k == Qt.Key.Key_F:
        if not getattr(self, "is_mini_mode", False):
            self.toggle_fullscreen()
    elif k == Qt.Key.Key_Escape:
        if getattr(self, "is_mini_mode", False):
            exit_mini_mode(self)
            self.update_window_and_video_radius()
        elif self.isFullScreen():
            self.toggle_fullscreen()
    elif k == Qt.Key.Key_L and not getattr(self, "is_mini_mode", False):
        self.toggle_playlist_panel()
    elif k == Qt.Key.Key_M:
        self.toggle_mute()
    elif k == Qt.Key.Key_V:
        self.toggle_subtitle()
    else:
        return False
    return True