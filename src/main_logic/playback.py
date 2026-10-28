import os
from src.ui.icons import ModernIcon
from src.main_logic.file import save_session
from src.main_logic.media import get_next_track_index, get_prev_track_index, PLAYBACK_MODE_NAMES

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
        next_track(self)
        return
    paused = self.core.pause_toggle()
    icon = "play" if paused else "pause"
    self.btn_play.setIcon(ModernIcon.create(icon, "#FFFFFF", 22))

def next_track(self):
    next_idx = get_next_track_index(self.current_idx, len(self.playlist), self.playback_mode)
    if next_idx is not None:
        play_index(self, next_idx)

def prev_track(self):
    prev_idx = get_prev_track_index(self.current_idx, len(self.playlist), self.playback_mode)
    if prev_idx is not None:
        play_index(self, prev_idx)

def cycle_playback_mode(self):
    self.playback_mode = (self.playback_mode + 1) % len(PLAYBACK_MODE_NAMES)
    self.btn_mode.setText(PLAYBACK_MODE_NAMES[self.playback_mode])
    save_session(self)

def set_volume(self, val: int):
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

def update_sub_icon(self):
    icon_name = "subtitle" if self.sub_visible else "subtitle_off"
    icon_color = "#FFFFFF" if self.sub_visible else "#94A3B8"
    self.btn_sub_toggle.setIcon(ModernIcon.create(icon_name, icon_color, 20))

def toggle_subtitle(self):
    self.sub_visible = not self.sub_visible
    update_sub_icon(self)
    if self.core:
        self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
    save_session(self)