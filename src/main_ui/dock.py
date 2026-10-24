from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt

from src.main_logic.media import format_time
from src.ui.icons import ModernIcon
from src.widgets.widgets import FloatingGlassPanel, FluidSeekSlider

from src.base import *

def dock_panel(self):
    self.dock_panel = FloatingGlassPanel()
    self.dock_panel.setMouseTracking(True)
    self.dock_panel.installEventFilter(self)

    dock_layout = QVBoxLayout(self.dock_panel)
    dock_layout.setContentsMargins(18, 10, 18, 12)
    dock_layout.setSpacing(6)

    dock_layout.addLayout(time_row(self))
    dock_layout.addLayout(btn_row(self))
    
    self.dock_panel.raise_()

def time_row(self) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)

    self.lbl_cur_time = QLabel("00:00")
    self.lbl_cur_time.setObjectName("lbl_cur_time")

    self.seek_slider = FluidSeekSlider()
    self.seek_slider.setRange(0, 1000)
    self.seek_slider.sliderMoved.connect(lambda x:on_seek_moved(self, x))
    self.seek_slider.sliderPressed.connect(lambda:on_seek_pressed(self))
    self.seek_slider.sliderReleased.connect(lambda:on_seek_released(self))

    self.lbl_total_time = QLabel("00:00")
    self.lbl_total_time.setObjectName("lbl_total_time")
    self.lbl_total_time.setCursor(Qt.CursorShape.PointingHandCursor)
    self.lbl_total_time.mousePressEvent = lambda:toggle_time_mode(self)

    row.addWidget(self.lbl_cur_time)
    row.addWidget(self.seek_slider)
    row.addWidget(self.lbl_total_time)
    return row

def btn_row(self) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)

    self.btn_prev = QPushButton()
    self.btn_prev.setIcon(ModernIcon.create("prev", "#FFFFFF", 20))
    self.btn_prev.setObjectName("iconBtn")
    self.btn_prev.clicked.connect(self.prev_track)

    self.btn_play = QPushButton()
    self.btn_play.setIcon(ModernIcon.create("play", "#FFFFFF", 22))
    self.btn_play.setObjectName("playBtn")
    self.btn_play.clicked.connect(self.toggle_play)

    self.btn_next = QPushButton()
    self.btn_next.setIcon(ModernIcon.create("next", "#FFFFFF", 20))
    self.btn_next.setObjectName("iconBtn")
    self.btn_next.clicked.connect(self.next_track)

    row.addWidget(self.btn_prev)
    row.addWidget(self.btn_play)
    row.addWidget(self.btn_next)
    row.addSpacing(6)

    self.btn_mode = QPushButton(PLAYBACK_MODE_NAMES[self.playback_mode])
    self.btn_mode.setObjectName("btn_mode")
    self.btn_mode.clicked.connect(self.cycle_playback_mode)
    row.addWidget(self.btn_mode)

    row.addStretch()

    self.btn_vol = QPushButton()
    self.btn_vol.setIcon(ModernIcon.create("volume", "#FFFFFF", 20))
    self.btn_vol.setObjectName("iconBtn")
    self.btn_vol.clicked.connect(self.toggle_mute)

    self.vol_slider = QSlider(Qt.Orientation.Horizontal)
    self.vol_slider.setRange(0, 100)
    self.vol_slider.setValue(80)
    self.vol_slider.setFixedWidth(80)
    self.vol_slider.valueChanged.connect(self.set_volume)

    row.addWidget(self.btn_vol)
    row.addWidget(self.vol_slider)
    row.addSpacing(8)

    self.btn_sub_toggle = QPushButton()
    self.btn_sub_toggle.setObjectName("iconBtn")
    self.btn_sub_toggle.clicked.connect(self.toggle_subtitle)
    self._update_sub_icon()

    self.btn_settings = QPushButton()
    self.btn_settings.setIcon(ModernIcon.create("gear", "#FFFFFF", 20))
    self.btn_settings.setObjectName("iconBtn")
    self.btn_settings.clicked.connect(self.open_settings)
    
    self.btn_pip_toggle = QPushButton()
    self.btn_pip_toggle.setIcon(ModernIcon.create("mini_mode", "#FFFFFF", 20))
    self.btn_pip_toggle.setObjectName("iconBtn")
    self.btn_pip_toggle.clicked.connect(self.toggle_mini_mode)

    self.btn_list_toggle = QPushButton()
    self.btn_list_toggle.setIcon(ModernIcon.create("playlist", "#FFFFFF", 20))
    self.btn_list_toggle.setObjectName("iconBtn")
    self.btn_list_toggle.clicked.connect(self.toggle_playlist_panel)

    self.btn_fs = QPushButton()
    self.btn_fs.setIcon(ModernIcon.create("fullscreen", "#FFFFFF", 20))
    self.btn_fs.setObjectName("iconBtn")
    self.btn_fs.clicked.connect(self.toggle_fullscreen)

    row.addWidget(self.btn_sub_toggle)
    row.addWidget(self.btn_settings)
    row.addWidget(self.btn_pip_toggle)
    row.addWidget(self.btn_list_toggle)
    row.addWidget(self.btn_fs)
    return row

def toggle_time_mode(self):
    self.show_remaining_time = not self.show_remaining_time
    
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