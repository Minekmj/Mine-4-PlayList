import os
import sys
import json
import random
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QFileDialog, QMessageBox, QMenu, QFrame,
    QGraphicsOpacityEffect, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QEvent, QSize, QPropertyAnimation, QEasingCurve

from src.ui.icons import ModernIcon
from src.widgets.widgets import AmbientVideoContainer, FloatingGlassPanel, FluidSeekSlider, FloatingOSD, PlaylistWidget, PlaylistItemCard
from src.core.player_core import PlayerCore
from src.ui.dialogs import SettingsDialog, UrlDialog

SESSION_FILE = "./session_state.json"


class EchoMediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mine 4 PlayList")
        self.resize(1300, 820)
        self.setMinimumSize(960, 600)
        self.setMouseTracking(True)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._session_loaded = False
        self._drag_pos = None

        self.playlist = []
        self.current_idx = -1
        self.playback_mode = 0
        self.is_seeking = False
        self.speed_list = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
        self.speed_idx = 2
        self.loop_a = None
        self.loop_b = None
        self.show_remaining_time = False
        
        true = True
        false = False
        
        self.sub_visible = True
        self.sub_config = {
            "font": "HY견고딕",
            "size": 40,
            "color": "#f9f9f9",
            "outline_color": "#232323",
            "border_size": 4,
            "blur": 1,
            "pos": 95,
            "bold": true,
            "typewriter_enabled": false,
            "typewriter_speed": 28,
            "fade_in_enabled": true,
            "fade_duration": 220,
            "slide_direction": "아래에서 위로",
            "slide_distance": 16,
            "anim_style": "팝업 바운스",
            "max_width_ratio": 0.88,
            "visible": true,
            "outside_video": true,
            "bg_color": "#000000",
            "bg_opacity": 0.0
        }
            
        self.engine_config = {
            "ambient_glow": true,
            "aurora_enabled": true,
            "aurora_style": "네온 파동",
            "aurora_palette": "바다",
            "aurora_intensity": 0.65,
            "particle_enabled": true,
            "particle_type": "눈 / 먼지",
            "particle_direction": "아래로",
            "particle_palette": "화이트",
            "particle_density": 0.7,
            "particle_speed": 1.0,
            "ambient_brightness": 0.6,
            "ambient_black_lift": 0.1,
            "ambient_gamma": 1.07,
            "ambient_blur_radius": 8,
            "ambient_motion_intensity": 0.42,
            "ambient_motion_speed": 2.5,
            "video_floating_rim": true,
            "video_shadow_enabled": true,
            "video_shadow_opacity": 0.1,
            "video_shadow_radius": 35,
            "video_shadow_offset": 6,
            "ambient_tint_enabled": true,
            "ambient_tint_color": "#000000",
            "ambient_tint_ratio": 0.7,
            "audio_norm": true,
            "hwdec": true,
            "border_margin": 0,
            "border_glow_spread": 20,
            "border_color_mode": "단색",
            "border_color1": "#f8f8f8",
            "border_color2": "#b3b3b3",
            "border_anim_mode": "정적",
            "border_anim_speed": 0.2,
            "border_wave_intensity": 0.2,
            "border_pulse_depth": 0.0,
            "border_reactive": true,
            "border_enabled": false,
            "border_style": "게이머 네온",
            "border_width": 5,
            "border_radius": 0,
            "border_opacity": 0.3
        }

        self.init_ui()
        self.init_top_bar()
        self.init_engine()
        self.load_session()
        self.save_session()
        self.load_session()
        
        self.state_timer = QTimer(self)
        self.state_timer.setInterval(120)
        self.state_timer.timeout.connect(self.sync_state)
        self.state_timer.start()

        self.ambient_timer = QTimer(self)
        self.ambient_timer.setInterval(100)
        self.ambient_timer.timeout.connect(self.sync_ambient_glow)
        self.ambient_timer.start()

        self.fs_timer = QTimer(self)
        self.fs_timer.setSingleShot(True)
        self.fs_timer.timeout.connect(self.hide_floating_controls)

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

        self.dock_panel = FloatingGlassPanel()
        self.dock_panel.setMouseTracking(True)
        self.dock_panel.installEventFilter(self)
        dock_layout = QVBoxLayout(self.dock_panel)
        dock_layout.setContentsMargins(18, 10, 18, 12)
        dock_layout.setSpacing(6)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        self.lbl_cur_time = QLabel("00:00")
        self.lbl_cur_time.setObjectName("lbl_cur_time")

        self.seek_slider = FluidSeekSlider()
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.sliderMoved.connect(self.on_seek_moved)
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)

        self.lbl_total_time = QLabel("00:00")
        self.lbl_total_time.setObjectName("lbl_total_time")
        self.lbl_total_time.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_total_time.mousePressEvent = self.toggle_time_mode

        time_row.addWidget(self.lbl_cur_time)
        time_row.addWidget(self.seek_slider)
        time_row.addWidget(self.lbl_total_time)
        dock_layout.addLayout(time_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

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

        btn_row.addWidget(self.btn_prev)
        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_next)
        btn_row.addSpacing(6)

        self.btn_mode = QPushButton("순차 재생")
        self.btn_mode.setObjectName("btn_mode")
        self.btn_mode.clicked.connect(self.cycle_playback_mode)
        btn_row.addWidget(self.btn_mode)

        btn_row.addStretch()

        self.btn_vol = QPushButton()
        self.btn_vol.setIcon(ModernIcon.create("volume", "#FFFFFF", 20))
        self.btn_vol.setObjectName("iconBtn")
        self.btn_vol.clicked.connect(self.toggle_mute)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(self.set_volume)

        btn_row.addWidget(self.btn_vol)
        btn_row.addWidget(self.vol_slider)
        btn_row.addSpacing(8)

        self.btn_sub_toggle = QPushButton()
        self.btn_sub_toggle.setObjectName("iconBtn")
        self.btn_sub_toggle.clicked.connect(self.toggle_subtitle)
        self._update_sub_icon()

        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(ModernIcon.create("gear", "#FFFFFF", 20))
        self.btn_settings.setObjectName("iconBtn")
        self.btn_settings.clicked.connect(self.open_settings)

        self.btn_list_toggle = QPushButton()
        self.btn_list_toggle.setIcon(ModernIcon.create("playlist", "#CBD5E1", 20))
        self.btn_list_toggle.setObjectName("iconBtn")
        self.btn_list_toggle.clicked.connect(self.toggle_playlist_panel)

        self.btn_fs = QPushButton()
        self.btn_fs.setIcon(ModernIcon.create("fullscreen", "#FFFFFF", 20))
        self.btn_fs.setObjectName("iconBtn")
        self.btn_fs.clicked.connect(self.toggle_fullscreen)

        btn_row.addWidget(self.btn_sub_toggle)
        btn_row.addWidget(self.btn_settings)
        btn_row.addWidget(self.btn_list_toggle)
        btn_row.addWidget(self.btn_fs)

        dock_layout.addLayout(btn_row)

        self.right_box = QFrame()
        self.right_box.setObjectName("right_ppanel")
        right_vbox = QVBoxLayout(self.right_box)
        right_vbox.setSpacing(8)

        option_bar = FloatingGlassPanel()
        option_layout = QHBoxLayout(option_bar)
        option_layout.setContentsMargins(14, 7, 14, 7)
        option_layout.setSpacing(10)

        lbl_list = QLabel("PLAYLIST")
        lbl_list.setObjectName("lbl_list")
        self.lbl_list_count = QLabel("(0)")
        self.lbl_list_count.setObjectName("lbl_list_count")

        btn_url = QPushButton()
        btn_url.setIcon(ModernIcon.create("url", "#FFFFFF", 16))
        btn_url.setObjectName("iconBtn")
        btn_url.clicked.connect(self.open_url_dialog)

        btn_files = QPushButton()
        btn_files.setIcon(ModernIcon.create("folder", "#FFFFFF", 16))
        btn_files.setObjectName("iconBtn")
        btn_files.clicked.connect(self.open_media_files)

        option_layout.addWidget(lbl_list)
        option_layout.addWidget(self.lbl_list_count)
        option_layout.addStretch(3)
        option_layout.addWidget(btn_url)
        option_layout.addWidget(btn_files)
        option_layout.addStretch(1)
        right_vbox.addWidget(option_bar)

        self.list_widget = PlaylistWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(self.list_widget.ScrollMode.ScrollPerPixel)
        self.list_widget.setSpacing(4)
        self.list_widget.files_dropped.connect(self.handle_dropped_files)
        self.list_widget.model().rowsMoved.connect(self.on_list_rows_moved)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.currentItemChanged.connect(self.on_list_item_changed)
        right_vbox.addWidget(self.list_widget)

        self.ambient_container.set_children_widgets(self.video_frame, self.dock_panel, self.right_box)

    def init_top_bar(self):
        self.top_control_bar = QFrame(self)
        self.top_control_bar.setObjectName("topControlBar")
        
        top_bar_layout = QHBoxLayout(self.top_control_bar)
        top_bar_layout.setContentsMargins(12, 6, 12, 6)
        top_bar_layout.setSpacing(10)

        self.btn_win_min = QPushButton()
        self.btn_win_min.setObjectName("trafficBtn")
        self.btn_win_min.setStyleSheet("background-color: #F59E0B;")
        self.btn_win_min.setToolTip("최소화")
        self.btn_win_min.clicked.connect(self.showMinimized)

        self.btn_win_max = QPushButton()
        self.btn_win_max.setObjectName("trafficBtn")
        self.btn_win_max.setStyleSheet("background-color: #10B981;")
        self.btn_win_max.setToolTip("최대화 / 이전 크기")
        self.btn_win_max.clicked.connect(self._toggle_maximize_restore)
        
        self.btn_win_close = QPushButton()
        self.btn_win_close.setObjectName("trafficBtn")
        self.btn_win_close.setStyleSheet("background-color: #EF4444;")
        self.btn_win_close.setToolTip("닫기")
        self.btn_win_close.clicked.connect(self.close)

        top_bar_layout.addWidget(self.btn_win_min)
        top_bar_layout.addWidget(self.btn_win_max)
        top_bar_layout.addWidget(self.btn_win_close)

        self.top_control_bar.adjustSize()

        self._top_opacity = QGraphicsOpacityEffect(self.top_control_bar)
        self._top_opacity.setOpacity(0.0)
        self.top_control_bar.setGraphicsEffect(self._top_opacity)

        self._top_anim = QPropertyAnimation(self._top_opacity, b"opacity")
        self._top_anim.setDuration(160)
        self._top_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.top_bar_timer = QTimer(self)
        self.top_bar_timer.setSingleShot(True)
        self.top_bar_timer.setInterval(220)
        self.top_bar_timer.timeout.connect(self._hide_top_bar)

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

    def sync_ambient_glow(self):
        if self.core and self.engine_config.get("ambient_glow", True):
            thumb = self.core.capture_ambient_frame(self.video_frame)
            if not thumb.isNull():
                self.ambient_container.update_video_frame(thumb)

    def apply_settings(self, sub_cfg: dict, eng_cfg: dict):
        self.sub_config = sub_cfg
        self.engine_config = eng_cfg

        if self.core:
            self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
            self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
            self.core.set_hwdec(self.engine_config.get("hwdec", True))

        self.ambient_container.set_ambient_params(self.engine_config)
        self.save_session()

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
        self.save_session()

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
        self.save_session()

    def toggle_play(self):
        if not self.core or not self.playlist:
            return
        if self.current_idx == -1:
            self.next_track()
            return
        paused = self.core.pause_toggle()
        if paused:
            self.btn_play.setIcon(ModernIcon.create("play", "#FFFFFF", 22))
        else:
            self.btn_play.setIcon(ModernIcon.create("pause", "#FFFFFF", 22))

    def next_track(self):
        if not self.playlist:
            return
        n = len(self.playlist)

        if self.playback_mode == 3:
            self.play_index(random.randint(0, n - 1))
            return

        if self.playback_mode == 1 and 0 <= self.current_idx < n:
            self.play_index(self.current_idx)
            return

        next_idx = self.current_idx + 1 if self.current_idx != -1 else 0
        if next_idx >= n:
            if self.playback_mode == 0:
                return
            next_idx = 0
        
        self.play_index(next_idx)

    def prev_track(self):
        if not self.playlist:
            return
        n = len(self.playlist)

        if self.playback_mode == 3:
            self.play_index(random.randint(0, n - 1))
            return

        start = self.current_idx if self.current_idx != -1 else 0
        idx = (start - 1) % n
        self.play_index(idx)

    def cycle_playback_mode(self):
        self.playback_mode = (self.playback_mode + 1) % 4
        names = ["순차 재생", "1곡 반복", "전체 반복", "랜덤 재생"]
        self.btn_mode.setText(names[self.playback_mode])
        self.save_session()

    def sync_state(self):
        if not self.core:
            return
        try:
            aspect = self.core.get_aspect_ratio()
            self.ambient_container.set_aspect_ratio(aspect)

            dur = self.core.player.duration or 0
            pos = self.core.player.time_pos or 0
            eof = getattr(self.core.player, 'eof_reached', False)

            if self.loop_a is not None and self.loop_b is not None:
                if pos >= self.loop_b:
                    self.core.player.time_pos = self.loop_a
                    return

            if self.current_idx != -1 and self.core.player.filename:
                if eof or (dur > 0 and pos >= dur - 0.25):
                    self.next_track()
                    return

            if dur > 0 and not self.is_seeking:
                self.seek_slider.set_duration(dur)
                pct = int((pos / dur) * 1000)
                self.seek_slider.setValue(pct)
                self.lbl_cur_time.setText(f"{int(pos)//60:02d}:{int(pos)%60:02d}")
                if self.show_remaining_time:
                    rem = max(0, dur - pos)
                    self.lbl_total_time.setText(f"-{int(rem)//60:02d}:{int(rem)%60:02d}")
                else:
                    self.lbl_total_time.setText(f"{int(dur)//60:02d}:{int(dur)%60:02d}")

            if hasattr(self.core, 'reposition_subtitle'):
                self.core.reposition_subtitle()
        except Exception:
            pass

    def on_seek_pressed(self):
        self.is_seeking = True

    def on_seek_moved(self, val):
        if self.core and self.core.player.duration:
            target = (val / 1000.0) * self.core.player.duration
            self.lbl_cur_time.setText(f"{int(target)//60:02d}:{int(target)%60:02d}")

    def on_seek_released(self):
        if self.core and self.core.player.duration:
            pos = (self.seek_slider.value() / 1000.0) * self.core.player.duration
            self.core.seek(pos)
        self.is_seeking = False

    def toggle_time_mode(self, event):
        self.show_remaining_time = not self.show_remaining_time

    def set_volume(self, val):
        if self.core:
            self.core.set_volume(val)
        if val == 0:
            self.btn_vol.setIcon(ModernIcon.create("mute", "#F43F5E", 20))
        else:
            self.btn_vol.setIcon(ModernIcon.create("volume", "#FFFFFF", 20))

    def toggle_mute(self):
        if self.vol_slider.value() > 0:
            self._prev_vol = self.vol_slider.value()
            self.vol_slider.setValue(0)
        else:
            self.vol_slider.setValue(getattr(self, '_prev_vol', 70))

    def refresh_playlist_view(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for idx, path in enumerate(self.playlist):
            title = os.path.splitext(os.path.basename(path))[0]
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 44))
            item.setData(Qt.ItemDataRole.UserRole, path)

            card_widget = PlaylistItemCard(
                item=item,
                title=f"{idx + 1:02d}.  {title}",
                on_play_callback=self.on_item_double_click
            )

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card_widget)

        self.list_widget.blockSignals(False)
        self.lbl_list_count.setText(f"({len(self.playlist)})")
        self.highlight_playing_row()

        if hasattr(self, 'core') and self.core:
            self.core.preload_playlist_gains(self.playlist)

    def on_list_item_changed(self, current, previous):
        if previous:
            prev_card = self.list_widget.itemWidget(previous)
            if isinstance(prev_card, PlaylistItemCard):
                prev_card.set_selected(False)
        if current:
            cur_card = self.list_widget.itemWidget(current)
            if isinstance(cur_card, PlaylistItemCard):
                cur_card.set_selected(True)

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

    def on_list_rows_moved(self, parent, start, end, dest, row):
        new_list = []
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            new_list.append(it.data(Qt.ItemDataRole.UserRole))

        cur_item = self.playlist[self.current_idx] if 0 <= self.current_idx < len(self.playlist) else None
        self.playlist = new_list
        if cur_item in self.playlist:
            self.current_idx = self.playlist.index(cur_item)

        self.refresh_playlist_view()
        self.save_session()

    def clear_playlist(self):
        if not self.playlist:
            return
        if QMessageBox.question(self, "확인", "목록을 비우시겠습니까?") == QMessageBox.StandardButton.Yes:
            self.playlist.clear()
            self.current_idx = -1
            if self.core:
                self.core.player.command('stop')
            self.refresh_playlist_view()
            self.save_session()

    def handle_dropped_files(self, paths):
        valid = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.mp3', '.flac', '.wav')
        added = []
        for p in paths:
            abs_p = os.path.abspath(p)
            if os.path.isdir(abs_p):
                for r, _, files in os.walk(abs_p):
                    for f in sorted(files):
                        if f.lower().endswith(valid):
                            added.append(os.path.join(r, f))
            elif abs_p.lower().endswith(valid):
                added.append(abs_p)

        if added:
            start_first = len(self.playlist) == 0
            for item in added:
                if item not in self.playlist:
                    self.playlist.append(item)
            self.refresh_playlist_view()
            self.save_session()
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
                self.save_session()

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

    def hide_floating_controls(self):
        if self.isFullScreen():
            if self.is_seeking:
                self.fs_timer.start(3000)
                return
            self.dock_panel.hide()
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.video_frame.setCursor(Qt.CursorShape.BlankCursor)
            self.ambient_container.setCursor(Qt.CursorShape.BlankCursor)

    def toggle_playlist_panel(self):
        self.ambient_container.set_playlist_visibility(not self.ambient_container.playlist_visible)
        QTimer.singleShot(60, lambda: self.core.reposition_subtitle() if self.core else None)

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

    def save_session(self):
        if not getattr(self, '_session_loaded', False):
            return

        pos = 0.0
        if self.core and self.core.player and self.core.player.time_pos:
            try:
                pos = float(self.core.player.time_pos)
            except Exception:
                pass

        data = {
            "playlist": [os.path.abspath(p) for p in self.playlist],
            "current_idx": self.current_idx,
            "time_pos": pos,
            "mode": self.playback_mode,
            "volume": self.vol_slider.value(),
            "sub_visible": self.sub_visible,
            "sub_config": self.sub_config,
            "engine_config": self.engine_config
        }
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_session(self):
        try:
            if not os.path.exists(SESSION_FILE):
                return

            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)

            raw_list = d.get("playlist", [])
            self.playlist = [os.path.abspath(p) for p in raw_list if os.path.exists(p)]

            saved_idx = d.get("current_idx", -1)
            if 0 <= saved_idx < len(self.playlist):
                self.current_idx = saved_idx
            elif self.playlist:
                self.current_idx = 0
            else:
                self.current_idx = -1

            self.playback_mode = d.get("mode", 0)
            self.vol_slider.setValue(d.get("volume", 80))
            self.sub_visible = d.get("sub_visible", True)
            self._update_sub_icon()

            if isinstance(d.get("sub_config"), dict):
                self.sub_config.update(d.get("sub_config"))
            if isinstance(d.get("engine_config"), dict):
                self.engine_config.update(d.get("engine_config"))

            names = ["순차 재생", "1곡 반복", "전체 반복", "랜덤 재생"]
            self.btn_mode.setText(names[self.playback_mode])

            self.refresh_playlist_view()

            if self.core:
                self.core.apply_subtitle_config(self.sub_config, self.sub_visible)
                self.core.set_audio_normalization(self.engine_config.get("audio_norm", True))
                self.core.set_hwdec(self.engine_config.get("hwdec", True))
                self.core.preload_playlist_gains(self.playlist)
            
            self.ambient_container.set_ambient_params(self.engine_config)

            saved_pos = d.get("time_pos", 0.0)
            if self.playlist and 0 <= self.current_idx < len(self.playlist):
                QTimer.singleShot(250, lambda: self._restore_playback(saved_pos))
        except Exception as e:
            print(f"세션 로드 오류: {e}")
        finally:
            self._session_loaded = True

    def _restore_playback(self, saved_pos: float):
        if 0 <= self.current_idx < len(self.playlist):
            self.play_index(self.current_idx)
            if saved_pos > 3.0:
                QTimer.singleShot(350, lambda: self.core.seek(saved_pos))

    def closeEvent(self, event):
        self.save_session()
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

    def _toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
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
        t = event.type()

        if obj == self.ambient_container:
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

        if self.isFullScreen() and t in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            self.show_floating_controls()

        target_view = getattr(self.core, 'view', None) if getattr(self, 'core', None) else None
        target_viewport = target_view.viewport() if target_view else None
        if obj in (self.video_frame, target_view, target_viewport):
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

        return super().eventFilter(obj, event)