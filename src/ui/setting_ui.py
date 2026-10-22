from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QFormLayout, QPushButton, QSpinBox, QSlider, QCheckBox, QColorDialog,
    QFontComboBox, QLabel, QScrollArea, QFrame, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from src.ui.base import *

class SettingsDialog(AnimatedDialogBase):
    def __init__(self, parent):
        super().__init__(None)
        self.p = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(520, 640)
        
        self.setStyleSheet(Get_qss())

        self.sub_cfg = dict(self.p.sub_config)
        self.engine_cfg = dict(self.p.engine_config)

        self.init_ui()
        self._center_to_parent()

    def _center_to_parent(self):
        if self.p:
            p_geo = self.p.geometry()
            x = p_geo.x() + (p_geo.width() - self.width()) // 2
            y = p_geo.y() + (p_geo.height() - self.height()) // 2
            self.move(max(20, x), max(20, y))

    def _create_card(self) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("cardFrame")
        layout = QFormLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return card, layout

    def _make_val_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedWidth(54)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 11px;")
        return lbl

    def _update_color_btn(self, btn: QPushButton, color_hex: str):
        c = QColor(color_hex)
        text_col = "#0F172A" if c.lightness() > 150 else "#F8FAFC"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                color: {text_col};
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: #2563EB;
            }}
        """)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("dialogContainer")
        root_layout.addWidget(self.container)

        vbox = QVBoxLayout(self.container)
        vbox.setContentsMargins(18, 14, 18, 16)
        vbox.setSpacing(12)

        header = DraggableHeader(self)
        header.setObjectName("dialogHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        title = QLabel("환경 설정")
        title.setObjectName("dialogTitle")
        h_layout.addWidget(title)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogCloseBtn")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.animated_close)
        h_layout.addWidget(btn_close)

        vbox.addWidget(header)

        self.tabs = QTabWidget()
        vbox.addWidget(self.tabs)

        t_fx = QWidget()
        l_fx = QVBoxLayout(t_fx)
        l_fx.setContentsMargins(4, 8, 4, 8)
        l_fx.setSpacing(10)

        c_amb, f_amb = self._create_card()
        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(30, 300)
        self.bright_slider.setValue(int(self.engine_cfg.get("ambient_brightness", 1.65) * 100))
        self.lbl_bright = self._make_val_label(f"{self.bright_slider.value()}%")
        self.bright_slider.valueChanged.connect(lambda v: self.lbl_bright.setText(f"{v}%"))
        h_bright = QHBoxLayout()
        h_bright.addWidget(self.bright_slider)
        h_bright.addWidget(self.lbl_bright)
        f_amb.addRow("배경 밝기", h_bright)

        self.lift_slider = QSlider(Qt.Orientation.Horizontal)
        self.lift_slider.setRange(0, 50)
        self.lift_slider.setValue(int(self.engine_cfg.get("ambient_black_lift", 0.25) * 100))
        self.lbl_lift = self._make_val_label(f"{self.lift_slider.value()}%")
        self.lift_slider.valueChanged.connect(lambda v: self.lbl_lift.setText(f"{v}%"))
        h_lift = QHBoxLayout()
        h_lift.addWidget(self.lift_slider)
        h_lift.addWidget(self.lbl_lift)
        f_amb.addRow("암부 보정", h_lift)

        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(4, 30)
        self.blur_slider.setValue(self.engine_cfg.get("ambient_blur_radius", 12))
        self.lbl_blur = self._make_val_label(f"{self.blur_slider.value()} px")
        self.blur_slider.valueChanged.connect(lambda v: self.lbl_blur.setText(f"{v} px"))
        h_blur = QHBoxLayout()
        h_blur.addWidget(self.blur_slider)
        h_blur.addWidget(self.lbl_blur)
        f_amb.addRow("흐림 반경", h_blur)
        l_fx.addWidget(c_amb)

        c_sh, f_sh = self._create_card()
        self.chk_floating_rim = QCheckBox("비디오 외곽 은은한 림라이트")
        self.chk_floating_rim.setChecked(self.engine_cfg.get("video_floating_rim", True))
        f_sh.addRow(self.chk_floating_rim)

        self.chk_shadow = QCheckBox("드롭 섀도우 효과")
        self.chk_shadow.setChecked(self.engine_cfg.get("video_shadow_enabled", True))
        f_sh.addRow(self.chk_shadow)

        self.shadow_op_slider = QSlider(Qt.Orientation.Horizontal)
        self.shadow_op_slider.setRange(10, 100)
        self.shadow_op_slider.setValue(int(self.engine_cfg.get("video_shadow_opacity", 0.55) * 100))
        self.lbl_sh_op = self._make_val_label(f"{self.shadow_op_slider.value()}%")
        self.shadow_op_slider.valueChanged.connect(lambda v: self.lbl_sh_op.setText(f"{v}%"))
        h_sh_op = QHBoxLayout()
        h_sh_op.addWidget(self.shadow_op_slider)
        h_sh_op.addWidget(self.lbl_sh_op)
        f_sh.addRow("그림자 농도", h_sh_op)

        self.shadow_rad_slider = QSlider(Qt.Orientation.Horizontal)
        self.shadow_rad_slider.setRange(5, 50)
        self.shadow_rad_slider.setValue(self.engine_cfg.get("video_shadow_radius", 20))
        self.lbl_sh_rad = self._make_val_label(f"{self.shadow_rad_slider.value()} px")
        self.shadow_rad_slider.valueChanged.connect(lambda v: self.lbl_sh_rad.setText(f"{v} px"))
        h_sh_rad = QHBoxLayout()
        h_sh_rad.addWidget(self.shadow_rad_slider)
        h_sh_rad.addWidget(self.lbl_sh_rad)
        f_sh.addRow("그림자 번짐", h_sh_rad)

        self.shadow_off_slider = QSlider(Qt.Orientation.Horizontal)
        self.shadow_off_slider.setRange(0, 35)
        self.shadow_off_slider.setValue(self.engine_cfg.get("video_shadow_offset", 10))
        self.lbl_sh_off = self._make_val_label(f"{self.shadow_off_slider.value()} px")
        self.shadow_off_slider.valueChanged.connect(lambda v: self.lbl_sh_off.setText(f"{v} px"))
        h_sh_off = QHBoxLayout()
        h_sh_off.addWidget(self.shadow_off_slider)
        h_sh_off.addWidget(self.lbl_sh_off)
        f_sh.addRow("대각선 거리", h_sh_off)
        l_fx.addWidget(c_sh)

        c_tint, f_tint = self._create_card()
        self.chk_tint = QCheckBox("배경 앰비언트 컬러 틴트 추가")
        self.chk_tint.setChecked(self.engine_cfg.get("ambient_tint_enabled", False))
        f_tint.addRow(self.chk_tint)

        self.btn_tint = QPushButton("틴트 색상")
        self.tint_col = QColor(self.engine_cfg.get("ambient_tint_color", "#8FAACD"))
        self._update_color_btn(self.btn_tint, self.tint_col.name())
        self.btn_tint.clicked.connect(self.pick_tint_color)

        self.tint_ratio_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_ratio_slider.setRange(5, 80)
        self.tint_ratio_slider.setValue(int(self.engine_cfg.get("ambient_tint_ratio", 0.20) * 100))
        self.lbl_tint_ratio = self._make_val_label(f"{self.tint_ratio_slider.value()}%")
        self.tint_ratio_slider.valueChanged.connect(lambda v: self.lbl_tint_ratio.setText(f"{v}%"))

        h_tint = QHBoxLayout()
        h_tint.addWidget(self.btn_tint)
        h_tint.addWidget(self.tint_ratio_slider)
        h_tint.addWidget(self.lbl_tint_ratio)
        f_tint.addRow("틴트 농도", h_tint)
        l_fx.addWidget(c_tint)
        l_fx.addStretch()

        self.tabs.addTab(self._scroll_page(t_fx), "영상 효과")
        
        t_atmos = QWidget()
        l_atmos = QVBoxLayout(t_atmos)
        l_atmos.setContentsMargins(4, 8, 4, 8)
        l_atmos.setSpacing(10)

        c_aurora, f_aurora = self._create_card()
        self.chk_aurora = QCheckBox("오로라 애니메이션 배경 활성화")
        self.chk_aurora.setChecked(self.engine_cfg.get("aurora_enabled", True))
        f_aurora.addRow(self.chk_aurora)

        self.aurora_style_cb = QComboBox()
        self.aurora_style_cb.addItems(["오로라", "네온 파동", "없음"])
        self.aurora_style_cb.setCurrentText(self.engine_cfg.get("aurora_style", "오로라"))
        f_aurora.addRow("오로라 유형", self.aurora_style_cb)

        self.aurora_palette_cb = QComboBox()
        self.aurora_palette_cb.addItems(["청록", "벚꽃", "바다", "보라", "노을"])
        self.aurora_palette_cb.setCurrentText(self.engine_cfg.get("aurora_palette", "청록"))
        f_aurora.addRow("오로라 색상", self.aurora_palette_cb)

        self.aurora_intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.aurora_intensity_slider.setRange(0, 100)
        self.aurora_intensity_slider.setValue(int(self.engine_cfg.get("aurora_intensity", 0.55) * 100))
        self.lbl_aurora_intensity = self._make_val_label(f"{self.aurora_intensity_slider.value()}%")
        self.aurora_intensity_slider.valueChanged.connect(lambda v: self.lbl_aurora_intensity.setText(f"{v}%"))
        row_aurora = QHBoxLayout()
        row_aurora.addWidget(self.aurora_intensity_slider)
        row_aurora.addWidget(self.lbl_aurora_intensity)
        f_aurora.addRow("오로라 강도", row_aurora)
        l_atmos.addWidget(c_aurora)

        c_pt, f_pt = self._create_card()
        self.chk_particles = QCheckBox("파티클 효과 활성화")
        self.chk_particles.setChecked(self.engine_cfg.get("particle_enabled", True))
        f_pt.addRow(self.chk_particles)

        self.particle_type_cb = QComboBox()
        self.particle_type_cb.addItems(["눈 / 먼지", "벚꽃", "별빛", "빛망울", "비"])
        self.particle_type_cb.setCurrentText(self.engine_cfg.get("particle_type", "눈 / 먼지"))
        f_pt.addRow("파티클 종류", self.particle_type_cb)

        self.particle_dir_cb = QComboBox()
        self.particle_dir_cb.addItems(["아래로", "위로", "왼쪽 대각선", "오른쪽 대각선", "부유 / 흩날림"])
        self.particle_dir_cb.setCurrentText(self.engine_cfg.get("particle_direction", "아래로"))
        f_pt.addRow("이동 방향", self.particle_dir_cb)

        self.particle_palette_cb = QComboBox()
        self.particle_palette_cb.addItems(["청록", "벚꽃", "바다", "보라", "노을", "화이트"])
        self.particle_palette_cb.setCurrentText(self.engine_cfg.get("particle_palette", "화이트"))
        f_pt.addRow("파티클 색상", self.particle_palette_cb)

        self.particle_density_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_density_slider.setRange(0, 100)
        self.particle_density_slider.setValue(int(self.engine_cfg.get("particle_density", 0.45) * 100))
        self.lbl_particle_density = self._make_val_label(f"{self.particle_density_slider.value()}%")
        self.particle_density_slider.valueChanged.connect(lambda v: self.lbl_particle_density.setText(f"{v}%"))
        row_pt_den = QHBoxLayout()
        row_pt_den.addWidget(self.particle_density_slider)
        row_pt_den.addWidget(self.lbl_particle_density)
        f_pt.addRow("입자 밀도", row_pt_den)

        self.particle_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_speed_slider.setRange(10, 300)
        self.particle_speed_slider.setValue(int(self.engine_cfg.get("particle_speed", 1.0) * 100))
        self.lbl_particle_speed = self._make_val_label(f"{self.particle_speed_slider.value() / 100:.1f}x")
        self.particle_speed_slider.valueChanged.connect(lambda v: self.lbl_particle_speed.setText(f"{v / 100:.1f}x"))
        row_pt_spd = QHBoxLayout()
        row_pt_spd.addWidget(self.particle_speed_slider)
        row_pt_spd.addWidget(self.lbl_particle_speed)
        f_pt.addRow("이동 속도", row_pt_spd)
        l_atmos.addWidget(c_pt)

        l_atmos.addStretch()
        self.tabs.addTab(self._scroll_page(t_atmos), "배경 효과")

        t_sub = QWidget()
        l_sub = QVBoxLayout(t_sub)
        l_sub.setContentsMargins(4, 8, 4, 8)
        l_sub.setSpacing(10)

        c_preset, f_preset = self._create_card()
        self.subtitle_preset_cb = QComboBox()
        self.subtitle_preset_cb.addItems(["직접 설정", "기본", "시인성", "네온", "부드러운 자막"])
        f_preset.addRow("스타일 프리셋", self.subtitle_preset_cb)
        self.subtitle_preset_cb.currentTextChanged.connect(self.apply_subtitle_preset)

        self.font_cb = QFontComboBox()
        self.font_cb.setCurrentFont(QFont(self.sub_cfg.get("font", "sans-serif")))
        f_preset.addRow("폰트 패밀리", self.font_cb)

        self.chk_bold = QCheckBox("폰트 굵게 (Bold)")
        self.chk_bold.setChecked(self.sub_cfg.get("bold", True))
        f_preset.addRow(self.chk_bold)
        l_sub.addWidget(c_preset)

        c_detail, f_detail = self._create_card()
        self.size_spin = QSpinBox()
        self.size_spin.setRange(18, 96)
        self.size_spin.setValue(self.sub_cfg.get("size", 44))
        f_detail.addRow("글자 크기", self.size_spin)

        self.btn_fg = QPushButton("색상 선택")
        self.fg_color = QColor(self.sub_cfg.get("color", "#FFFFFF"))
        self._update_color_btn(self.btn_fg, self.fg_color.name())
        self.btn_fg.clicked.connect(lambda: self.pick_color("color", self.btn_fg))
        f_detail.addRow("텍스트 색상", self.btn_fg)

        self.border_spin = QSpinBox()
        self.border_spin.setRange(0, 10)
        self.border_spin.setValue(self.sub_cfg.get("border_size", 3))
        f_detail.addRow("외곽선 두께", self.border_spin)

        self.btn_border = QPushButton("외곽선 색상")
        self.outline_color = QColor(self.sub_cfg.get("outline_color", "#101010"))
        self._update_color_btn(self.btn_border, self.outline_color.name())
        self.btn_border.clicked.connect(lambda: self.pick_color("outline_color", self.btn_border))
        f_detail.addRow("외곽선 색상", self.btn_border)

        self.blur_spin = QSpinBox()
        self.blur_spin.setRange(0, 20)
        self.blur_spin.setValue(self.sub_cfg.get("blur", 3))
        f_detail.addRow("글로우 블러", self.blur_spin)

        self.pos_spin = QSpinBox()
        self.pos_spin.setRange(30, 100)
        self.pos_spin.setValue(self.sub_cfg.get("pos", 94))
        f_detail.addRow("수직 위치 (%)", self.pos_spin)

        self.width_ratio_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_ratio_slider.setRange(50, 98)
        self.width_ratio_slider.setValue(int(self.sub_cfg.get("max_width_ratio", 0.88) * 100))
        self.lbl_width_ratio = self._make_val_label(f"{self.width_ratio_slider.value()}%")
        self.width_ratio_slider.valueChanged.connect(lambda v: self.lbl_width_ratio.setText(f"{v}%"))
        row_w = QHBoxLayout()
        row_w.addWidget(self.width_ratio_slider)
        row_w.addWidget(self.lbl_width_ratio)
        f_detail.addRow("줄바꿈 너비", row_w)
        l_sub.addWidget(c_detail)

        c_anim, f_anim = self._create_card()
        self.anim_style_cb = QComboBox()
        self.anim_style_cb.addItems(["슬라이드 & 페이드", "자연스러운 페이드", "타자기", "팝업 바운스", "웨이브", "없음"])
        self.anim_style_cb.setCurrentText(self.sub_cfg.get("anim_style", "슬라이드 & 페이드"))
        f_anim.addRow("적용 애니메이션", self.anim_style_cb)

        self.slide_dir_cb = QComboBox()
        self.slide_dir_cb.addItems(["아래에서 위로", "위에서 아래로", "왼쪽에서", "오른쪽에서", "없음"])
        self.slide_dir_cb.setCurrentText(self.sub_cfg.get("slide_direction", "아래에서 위로"))
        f_anim.addRow("나타나는 방향", self.slide_dir_cb)

        self.slide_dist_slider = QSlider(Qt.Orientation.Horizontal)
        self.slide_dist_slider.setRange(4, 40)
        self.slide_dist_slider.setValue(self.sub_cfg.get("slide_distance", 16))
        self.lbl_slide_dist = self._make_val_label(f"{self.slide_dist_slider.value()} px")
        self.slide_dist_slider.valueChanged.connect(lambda v: self.lbl_slide_dist.setText(f"{v} px"))
        row_sdist = QHBoxLayout()
        row_sdist.addWidget(self.slide_dist_slider)
        row_sdist.addWidget(self.lbl_slide_dist)
        f_anim.addRow("이동 거리", row_sdist)

        self.chk_fade = QCheckBox("자연스럽게 나타나기 (Fade-in)")
        self.chk_fade.setChecked(self.sub_cfg.get("fade_in_enabled", True))
        f_anim.addRow(self.chk_fade)

        self.fade_dur_slider = QSlider(Qt.Orientation.Horizontal)
        self.fade_dur_slider.setRange(50, 600)
        self.fade_dur_slider.setValue(self.sub_cfg.get("fade_duration", 220))
        self.lbl_fade_dur = self._make_val_label(f"{self.fade_dur_slider.value()} ms")
        self.fade_dur_slider.valueChanged.connect(lambda v: self.lbl_fade_dur.setText(f"{v} ms"))
        row_fdur = QHBoxLayout()
        row_fdur.addWidget(self.fade_dur_slider)
        row_fdur.addWidget(self.lbl_fade_dur)
        f_anim.addRow("페이드 시간", row_fdur)

        self.chk_typewriter = QCheckBox("글자 차례대로 나타나기 (타자기 효과)")
        self.chk_typewriter.setChecked(self.sub_cfg.get("typewriter_enabled", False))
        f_anim.addRow(self.chk_typewriter)

        self.tw_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.tw_speed_slider.setRange(10, 80)
        self.tw_speed_slider.setValue(self.sub_cfg.get("typewriter_speed", 28))
        self.lbl_tw_speed = self._make_val_label(f"{self.tw_speed_slider.value()} ms")
        self.tw_speed_slider.valueChanged.connect(lambda v: self.lbl_tw_speed.setText(f"{v} ms"))
        row_tw = QHBoxLayout()
        row_tw.addWidget(self.tw_speed_slider)
        row_tw.addWidget(self.lbl_tw_speed)
        f_anim.addRow("타이핑 속도", row_tw)

        l_sub.addWidget(c_anim)
        l_sub.addStretch()

        self.tabs.addTab(self._scroll_page(t_sub), "자막 스타일")

        t_eng = QWidget()
        l_eng = QVBoxLayout(t_eng)
        l_eng.setContentsMargins(4, 8, 4, 8)
        l_eng.setSpacing(10)

        c_eng, f_eng = self._create_card()
        self.chk_norm = QCheckBox("오디오 자동 볼륨 노멀라이제이션")
        self.chk_norm.setChecked(self.engine_cfg.get("audio_norm", True))
        f_eng.addRow(self.chk_norm)

        self.chk_hw = QCheckBox("하드웨어 GPU 가속 디코딩 (권장)")
        self.chk_hw.setChecked(self.engine_cfg.get("hwdec", True))
        f_eng.addRow(self.chk_hw)
        l_eng.addWidget(c_eng)
        l_eng.addStretch()

        self.tabs.addTab(self._scroll_page(t_eng), "재생 엔진")

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.animated_close)
        btn_cancel.setFixedWidth(80)

        btn_apply = QPushButton("저장")
        btn_apply.setObjectName("accentBtn")
        btn_apply.clicked.connect(self.save)
        btn_apply.setFixedWidth(90)

        h_btn.addWidget(btn_cancel)
        h_btn.addWidget(btn_apply)
        vbox.addLayout(h_btn)

    def _scroll_page(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page.setMinimumWidth(0)
        scroll.setWidget(page)
        return scroll

    def pick_color(self, key: str, btn: QPushButton):
        curr = QColor(self.sub_cfg.get(key, "#FFFFFF"))
        c = QColorDialog.getColor(curr, self, "색상 선택")
        if c.isValid():
            self.sub_cfg[key] = c.name()
            if key == "color":
                self.fg_color = c
            elif key == "outline_color":
                self.outline_color = c
            self._update_color_btn(btn, c.name())

    def apply_subtitle_preset(self, name: str):
        presets = {
            "기본": {"size": 44, "color": "#FFFFFF", "outline_color": "#101010", "border_size": 4, "blur": 3, "pos": 94, "bold": True, "anim_style": "슬라이드 & 페이드", "fade_in_enabled": True},
            "시인성": {"size": 40, "color": "#FFF4D8", "outline_color": "#17131B", "border_size": 3, "blur": 2, "pos": 92, "bold": False, "anim_style": "자연스러운 페이드", "fade_in_enabled": True},
            "네온": {"size": 44, "color": "#D9F8FF", "outline_color": "#173CFF", "border_size": 4, "blur": 8, "pos": 94, "bold": True, "anim_style": "팝업 바운스", "fade_in_enabled": True},
            "부드러운 자막": {"size": 40, "color": "#F1F5F9", "outline_color": "#242936", "border_size": 2, "blur": 2, "pos": 93, "bold": False, "anim_style": "슬라이드 & 페이드", "fade_in_enabled": True},
        }
        preset = presets.get(name)
        if not preset:
            return
        self.size_spin.setValue(preset["size"])
        self.border_spin.setValue(preset["border_size"])
        self.blur_spin.setValue(preset["blur"])
        self.pos_spin.setValue(preset["pos"])
        self.chk_bold.setChecked(preset["bold"])
        self.anim_style_cb.setCurrentText(preset.get("anim_style", "슬라이드 & 페이드"))
        self.chk_fade.setChecked(preset.get("fade_in_enabled", True))
        self.fg_color = QColor(preset["color"])
        self.outline_color = QColor(preset["outline_color"])
        self.sub_cfg["color"] = preset["color"]
        self.sub_cfg["outline_color"] = preset["outline_color"]
        self._update_color_btn(self.btn_fg, preset["color"])
        self._update_color_btn(self.btn_border, preset["outline_color"])

    def pick_tint_color(self):
        c = QColorDialog.getColor(self.tint_col, self, "틴트 색상 선택")
        if c.isValid():
            self.tint_col = c
            self._update_color_btn(self.btn_tint, c.name())

    def save(self):
        self.sub_cfg.update({
            "font": self.font_cb.currentFont().family(),
            "size": self.size_spin.value(),
            "border_size": self.border_spin.value(),
            "blur": self.blur_spin.value(),
            "pos": self.pos_spin.value(),
            "bold": self.chk_bold.isChecked(),
            "color": self.sub_cfg.get("color", self.fg_color.name()),
            "outline_color": self.sub_cfg.get("outline_color", self.outline_color.name()),
            "max_width_ratio": self.width_ratio_slider.value() / 100.0,
            "anim_style": self.anim_style_cb.currentText(),
            "slide_direction": self.slide_dir_cb.currentText(),
            "slide_distance": self.slide_dist_slider.value(),
            "fade_in_enabled": self.chk_fade.isChecked(),
            "fade_duration": self.fade_dur_slider.value(),
            "typewriter_enabled": self.chk_typewriter.isChecked(),
            "typewriter_speed": self.tw_speed_slider.value()
        })
        self.engine_cfg.update({
            "ambient_glow": True,
            "ambient_brightness": self.bright_slider.value() / 100.0,
            "ambient_black_lift": self.lift_slider.value() / 100.0,
            "ambient_blur_radius": self.blur_slider.value(),
            "video_floating_rim": self.chk_floating_rim.isChecked(),
            "video_shadow_enabled": self.chk_shadow.isChecked(),
            "video_shadow_opacity": self.shadow_op_slider.value() / 100.0,
            "video_shadow_radius": self.shadow_rad_slider.value(),
            "video_shadow_offset": self.shadow_off_slider.value(),
            "ambient_tint_enabled": self.chk_tint.isChecked(),
            "ambient_tint_color": self.tint_col.name(),
            "ambient_tint_ratio": self.tint_ratio_slider.value() / 100.0,
            "aurora_enabled": self.chk_aurora.isChecked(),
            "aurora_style": self.aurora_style_cb.currentText(),
            "aurora_palette": self.aurora_palette_cb.currentText(),
            "aurora_intensity": self.aurora_intensity_slider.value() / 100.0,
            "particle_enabled": self.chk_particles.isChecked(),
            "particle_type": self.particle_type_cb.currentText(),
            "particle_direction": self.particle_dir_cb.currentText(),
            "particle_palette": self.particle_palette_cb.currentText(),
            "particle_density": self.particle_density_slider.value() / 100.0,
            "particle_speed": self.particle_speed_slider.value() / 100.0,
            "audio_norm": self.chk_norm.isChecked(),
            "hwdec": self.chk_hw.isChecked()
        })
        self.p.apply_settings(self.sub_cfg, self.engine_cfg)
        self.animated_close()
