from PyQt6.QtCore import Qt, QTimer
from src.main_logic.media import *

def timers(self):
    self.state_timer = QTimer(self)
    self.state_timer.setInterval(120)
    self.state_timer.timeout.connect(lambda:sync_state(self))
    self.state_timer.start()

    self.ambient_timer = QTimer(self)
    self.ambient_timer.setInterval(100)
    self.ambient_timer.timeout.connect(lambda:sync_ambient_glow(self))
    self.ambient_timer.start()

    self.fs_timer = QTimer(self)
    self.fs_timer.setSingleShot(True)
    self.fs_timer.timeout.connect(lambda:hide_floating_controls(self))


def sync_state(self):
    if not self.core:
        return
    try:
        self.ambient_container.set_aspect_ratio(self.core.get_aspect_ratio())

        dur = self.core.player.duration or 0
        pos = self.core.player.time_pos or 0
        eof = getattr(self.core.player, 'eof_reached', False)

        if self.current_idx != -1 and self.core.player.filename:
            if eof or (dur > 0 and pos >= dur - 0.25):
                self.next_track()
                return

        if dur > 0 and not self.is_seeking:
            self.seek_slider.set_duration(dur)
            self.seek_slider.setValue(int((pos / dur) * 1000))
            self.lbl_cur_time.setText(format_time(pos))
            if self.show_remaining_time:
                self.lbl_total_time.setText(f"-{format_time(max(0, dur - pos))}")
            else:
                self.lbl_total_time.setText(format_time(dur))

        self.core.reposition_subtitle()
    except Exception:
        pass
    
def sync_ambient_glow(self):
    if self.core and self.engine_config.get("ambient_glow", True):
        thumb = self.core.capture_ambient_frame(self.video_frame)
        if not thumb.isNull():
            self.ambient_container.update_video_frame(thumb)
            
def hide_floating_controls(self):
    if self.isFullScreen():
        if self.is_seeking:
            self.fs_timer.start(3000)
            return
        self.dock_panel.hide()
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.video_frame.setCursor(Qt.CursorShape.BlankCursor)
        self.ambient_container.setCursor(Qt.CursorShape.BlankCursor)