from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout,
    QPushButton, QSpinBox, QSlider, QCheckBox, QColorDialog,
    QFontComboBox, QLabel, QScrollArea, QFrame, QComboBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from src.ui.base import *


class ConfigBinder:
    def __init__(self, dialog: QWidget):
        self.dlg = dialog
        self.bindings: list[tuple[dict, str, callable]] = []
        self.setters: dict[str, callable] = {}

    def slider(self, form: QFormLayout, label: str, target: dict, key: str,
               v_min: int, v_max: int, scale: float = 1.0,
               fmt="{}%", default=0) -> QWidget:
        val = target.get(key, default)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(v_min, v_max)
        slider.setValue(int(val / scale if scale != 1.0 else val))

        lbl = QLabel()
        lbl.setFixedWidth(64)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet("color: #475569; font-weight: 600; font-size: 11px;")

        def update(v):
            lbl.setText(fmt(v) if callable(fmt) else fmt.format(v))

        slider.valueChanged.connect(update)
        update(slider.value())

        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(slider, 1)
        h.addWidget(lbl)
        form.addRow(label, container)

        self.bindings.append((
            target, key,
            lambda: slider.value() * scale if scale != 1.0 else slider.value()
        ))
        self.setters[key] = lambda v: slider.setValue(
            int(v / scale if scale != 1.0 else v)
        )
        return container

    def combo(self, form: QFormLayout, label: str, target: dict, key: str,
              items: list[str], default: str = "", val_map: dict = None,
              on_change=None) -> QComboBox:
        cb = QComboBox()
        cb.addItems(items)
        curr = target.get(key, default)
        curr_text = val_map.get(curr, str(curr)) if val_map else str(curr)

        if curr_text in items:
            cb.setCurrentText(curr_text)
        elif items:
            cb.setCurrentIndex(0)

        if on_change:
            cb.currentTextChanged.connect(on_change)

        form.addRow(label, cb)
        rev_map = {v: k for k, v in val_map.items()} if val_map else None

        self.bindings.append((
            target, key,
            lambda: rev_map.get(cb.currentText(), cb.currentText())
            if rev_map else cb.currentText()
        ))
        self.setters[key] = lambda v: cb.setCurrentText(
            val_map.get(v, str(v)) if val_map else str(v)
        )
        return cb

    def check(self, form: QFormLayout, text: str, target: dict, key: str,
              default: bool = False, on_change=None) -> QCheckBox:
        chk = QCheckBox(text)
        chk.setChecked(bool(target.get(key, default)))
        chk.setMinimumSize(0, 30)
        chk.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        chk.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if on_change:
            chk.toggled.connect(on_change)

        if form is not None:
            row = QWidget()
            row.setMinimumHeight(32)
            row.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed
            )
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(chk)
            layout.addStretch(1)
            form.addRow(row)

        self.bindings.append((target, key, chk.isChecked))
        self.setters[key] = chk.setChecked
        return chk

    def spin(self, form: QFormLayout, label: str, target: dict, key: str,
             v_min: int, v_max: int, default: int = 0) -> QSpinBox:
        sp = QSpinBox()
        sp.setRange(v_min, v_max)
        sp.setValue(int(target.get(key, default)))
        form.addRow(label, sp)
        self.bindings.append((target, key, sp.value))
        self.setters[key] = sp.setValue
        return sp

    def color_btn(self, target: dict, key: str, text: str = "색상 선택",
                  default: str = "#FFFFFF", on_change=None) -> QPushButton:
        btn = QPushButton(text)
        btn.color = QColor(target.get(key, default))
        self._update_color_style(btn, btn.color.name())

        def pick():
            c = QColorDialog.getColor(btn.color, self.dlg, f"{text} 선택")
            if c.isValid():
                self.set_color(btn, c.name())
                if on_change:
                    on_change(c)

        btn.clicked.connect(pick)
        self.bindings.append((target, key, lambda: btn.color.name()))
        self.setters[key] = lambda hex_val: self.set_color(btn, hex_val)
        return btn

    def set_color(self, btn: QPushButton, hex_val: str):
        btn.color = QColor(hex_val)
        self._update_color_style(btn, hex_val)

    def _update_color_style(self, btn: QPushButton, color_hex: str):
        c = QColor(color_hex)
        text_col = "#0F172A" if c.lightness() > 150 else "#F8FAFC"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_hex};
                color: {text_col};
                border: 1px solid rgba(0,0,0,0.15);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: #2563EB;
            }}
        """)

    def set_val(self, key: str, val):
        if key in self.setters:
            self.setters[key](val)

    def save(self):
        for target, key, getter in self.bindings:
            target[key] = getter()


class SettingsGroup(QFrame):
    def __init__(self, binder: ConfigBinder, title: str = "",
                 target: dict = None, check_key: str = None,
                 check_default: bool = False, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.b = binder
        self.form = QFormLayout(self)
        self.form.setContentsMargins(14, 12, 14, 12)
        self.form.setSpacing(10)
        self.form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self.inner_fields: list[QWidget] = []
        self.chk_toggle: QCheckBox | None = None

        if check_key is not None and target is not None:
            self.chk_toggle = self.b.check(
                self.form, title or "활성화", target, check_key,
                check_default, self._on_toggle
            )
        elif title:
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: 700;")
            self.form.addRow(lbl)

    def _register_field(self, field: QWidget):
        self.inner_fields.append(field)
        visible = self.chk_toggle is None or self.chk_toggle.isChecked()
        field.setVisible(visible)
        label = self.form.labelForField(field)
        if label:
            label.setVisible(visible)

    def _on_toggle(self, checked: bool):
        for field in self.inner_fields:
            field.setVisible(checked)
            label = self.form.labelForField(field)
            if label:
                label.setVisible(checked)

    def slider(self, label: str, target: dict, key: str,
               v_min: int, v_max: int, scale: float = 1.0,
               fmt="{}%", default=0) -> QWidget:
        w = self.b.slider(
            self.form, label, target, key, v_min, v_max,
            scale, fmt, default
        )
        self._register_field(w)
        return w

    def combo(self, label: str, target: dict, key: str,
              items: list[str], default: str = "",
              val_map: dict = None, on_change=None) -> QComboBox:
        cb = self.b.combo(
            self.form, label, target, key, items, default, val_map, on_change
        )
        self._register_field(cb)
        return cb

    def check(self, text: str, target: dict, key: str,
              default: bool = False, on_change=None) -> QCheckBox:
        chk = self.b.check(
            self.form, text, target, key, default, on_change
        )
        self._register_field(chk)
        return chk

    def spin(self, label: str, target: dict, key: str,
             v_min: int, v_max: int, default: int = 0) -> QSpinBox:
        sp = self.b.spin(
            self.form, label, target, key, v_min, v_max, default
        )
        self._register_field(sp)
        return sp

    def color_btn(self, label: str, target: dict, key: str,
                  text: str = "색상 선택", default: str = "#FFFFFF",
                  on_change=None) -> QPushButton:
        btn = self.b.color_btn(target, key, text, default, on_change)
        self.form.addRow(label, btn)
        self._register_field(btn)
        return btn

    def add_row(self, label_or_widget, field: QWidget = None):
        if field is None:
            self.form.addRow(label_or_widget)
            if isinstance(label_or_widget, QWidget):
                self._register_field(label_or_widget)
        else:
            self.form.addRow(label_or_widget, field)
            self._register_field(field)


class BaseSettingsTab(QScrollArea):
    def __init__(self, dialog: "SettingsDialog", parent=None):
        super().__init__(parent)
        self.dlg = dialog
        self.b = dialog.b
        self.engine_cfg = dialog.engine_cfg
        self.sub_cfg = dialog.sub_cfg
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.page = QWidget()
        self.page.setMinimumWidth(0)
        self.layout = QVBoxLayout(self.page)
        self.layout.setContentsMargins(4, 8, 4, 8)
        self.layout.setSpacing(10)
        self.setWidget(self.page)
        self.setup_ui()
        self.layout.addStretch()

    def setup_ui(self):
        pass

    def add_group(self, title: str = "", target: dict = None,
                  check_key: str = None,
                  check_default: bool = False) -> SettingsGroup:
        grp = SettingsGroup(
            binder=self.b, title=title, target=target,
            check_key=check_key, check_default=check_default,
            parent=self.page
        )
        self.layout.addWidget(grp)
        return grp
class FxTab(BaseSettingsTab):
    def setup_ui(self):
        e = self.engine_cfg

        g_amb = self.add_group("화면 화질 및 앰비언트 밝기")
        q_map = {35: "최소 (35%)", 50: "보통 (50%)", 85: "최대 (85%)", 100: "맥스 (100%)"}
        g_amb.combo("화면 화질 축소 비율", e, "ambient_quality_percent", list(q_map.values()), val_map=q_map, default=35)
        g_amb.slider("배경 밝기", e, "ambient_brightness", 30, 300, scale=0.01, default=1.65)
        g_amb.slider("암부 보정", e, "ambient_black_lift", 0, 50, scale=0.01, default=0.25)
        g_amb.slider("흐림 반경", e, "ambient_blur_radius", 4, 30, fmt="{} px", default=12)
        g_amb.slider("캡처 안쪽 여백", e, "ambient_crop_margin", 0, 25, default=5)

        g_vig = self.add_group("비네트 효과 활성화", target=e, check_key="ambient_vignette_enabled", check_default=True)
        g_vig.slider("광원 최대 도달 거리", e, "ambient_vignette_max_dist", 20, 150, fmt="{}%", default=85)
        g_vig.slider("광원 선명도 및 강도", e, "ambient_vignette_intensity", 50, 300, scale=0.01, fmt=lambda v: f"{v/100:.2f}x", default=1.65)
        g_vig.slider("색상별 형상 굴곡 깊이", e, "ambient_vignette_shape_depth", 0, 100, scale=0.01, fmt="{}%", default=0.85)
        g_vig.slider("외곽 암부 페이드 깊이", e, "ambient_vignette_darkness", 0, 100, scale=0.01, fmt="{}%", default=0.80)

        g_crn = self.add_group("모서리 및 외곽 림라이트 효과")
        g_crn.check("비디오 외곽 은은한 림라이트", e, "video_floating_rim", True)
        g_crn.slider("동영상 모서리 둥글기", e, "video_radius", 0, 48, fmt="{} px", default=8)
        g_crn.slider("창 모서리 둥글기", e, "window_radius", 0, 48, fmt="{} px", default=12)

        g_sh = self.add_group("드롭 섀도우 효과 활성화", target=e, check_key="video_shadow_enabled", check_default=True)
        g_sh.slider("그림자 농도", e, "video_shadow_opacity", 5, 100, scale=0.01, default=0.25)
        g_sh.slider("그림자 번짐", e, "video_shadow_radius", 4, 60, fmt="{} px", default=28)
        g_sh.slider("대각선 거리", e, "video_shadow_offset", 0, 35, fmt="{} px", default=8)

        g_tint = self.add_group("배경 앰비언트 컬러 틴트 추가", target=e, check_key="ambient_tint_enabled", check_default=False)
        g_tint.color_btn("틴트 색상", e, "ambient_tint_color", "틴트 색상", "#8FAACD")
        g_tint.slider("틴트 농도", e, "ambient_tint_ratio", 5, 80, scale=0.01, default=0.20)


class AtmosTab(BaseSettingsTab):
    def setup_ui(self):
        e = self.engine_cfg

        g_aurora = self.add_group("오로라 효과 켜기", target=e, check_key="aurora_enabled", check_default=True)
        g_aurora.combo("오로라 형태", e, "aurora_style", ["오로라", "물결", "없음"], "오로라")
        g_aurora.combo("오로라 색상", e, "aurora_palette", ["청록", "분홍", "파랑", "보라", "주황"], "청록")
        g_aurora.slider("오로라 강도", e, "aurora_intensity", 0, 100, scale=0.01, default=0.55)

        g_pt = self.add_group("파티클 효과 켜기", target=e, check_key="particle_enabled", check_default=True)
        g_pt.combo("파티클 모양", e, "particle_type",
                   ["먼지", "벚꽃", "별", "빛망울", "비", "하트", "깃털", "음표", "반짝이", "큐브"], "먼지")
        g_pt.combo("이동 방향", e, "particle_direction", ["아래로", "위로", "왼쪽 대각선", "오른쪽 대각선", "흩날림"], "아래로")
        g_pt.combo("파티클 색상", e, "particle_palette",
                   ["청록", "분홍", "파랑", "보라", "주황", "흰색", "노랑", "형광", "연분홍"], "청록")
        g_pt.slider("입자 밀도", e, "particle_density", 0, 100, scale=0.01, default=0.45)
        g_pt.slider("이동 속도", e, "particle_speed", 10, 300, scale=0.01, fmt=lambda v: f"{v/100:.1f}x", default=1.0)


class BorderTab(BaseSettingsTab):
    def setup_ui(self):
        e = self.engine_cfg

        g_b = self.add_group("화면 테두리 켜기", target=e, check_key="border_enabled", check_default=True)
        g_b.combo("테두리 모양", e, "border_style", [
            "네온", "기본", "이중선", "브래킷", "액자", "모따기",
            "도트", "분할선", "비네트", "상하 바", "십자", "강조 네온", "없음"
        ], "네온")

        row_b_cols = QWidget()
        row_l = QHBoxLayout(row_b_cols)
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(8)
        btn_col1 = self.b.color_btn(e, "border_color1", "1차 색상", e.get("border_color", "#38BDF8"))
        btn_col2 = self.b.color_btn(e, "border_color2", "2차 색상", "#818CF8")
        row_l.addWidget(btn_col1)
        row_l.addWidget(btn_col2)

        def on_cmode_change(m):
            vis = m in ["단색", "그라디언트"]
            row_b_cols.setVisible(vis)
            btn_col1.setVisible(vis)
            btn_col2.setVisible(m == "그라디언트")

        g_b.combo("색상 방식", e, "border_color_mode", ["단색", "그라디언트", "무지개"], "단색", on_change=on_cmode_change)
        g_b.add_row("지정 색상", row_b_cols)
        on_cmode_change(e.get("border_color_mode", "단색"))

        g_b.combo("효과", e, "border_anim_mode", ["정지", "숨쉬기", "회전", "깜빡임"], "숨쉬기")
        g_b.slider("펄스 호흡 깊이", e, "border_pulse_depth", 0, 80, scale=0.01, default=0.35)
        g_b.slider("효과 속도", e, "border_anim_speed", 20, 300, scale=0.01, fmt=lambda v: f"{v/100:.1f}x", default=1.0)
        g_b.slider("선 두께", e, "border_width", 1, 24, fmt="{} px", default=3)
        g_b.slider("화면 여백", e, "border_margin", 0, 50, fmt=lambda v: "화면 밀착" if v == 0 else f"{v} px", default=0)
        g_b.slider("글로우 번짐", e, "border_glow_spread", 0, 40, fmt="{} px", default=14)
        g_b.slider("불투명도", e, "border_opacity", 10, 100, scale=0.01, default=0.75)


class SubTab(BaseSettingsTab):
    def setup_ui(self):
        s = self.sub_cfg

        g_pre = self.add_group("스타일 및 글꼴")
        cb_preset = QComboBox()
        cb_preset.addItems(["직접 설정", "기본", "시인성", "네온", "부드러운 자막"])
        cb_preset.currentTextChanged.connect(self.dlg.apply_subtitle_preset)
        g_pre.add_row("스타일 프리셋", cb_preset)

        font_cb = QFontComboBox()
        font_cb.setCurrentFont(QFont(s.get("font", "sans-serif")))
        g_pre.add_row("폰트 패밀리", font_cb)
        self.b.bindings.append((s, "font", lambda: font_cb.currentFont().family()))
        self.b.setters["font"] = lambda f_name: font_cb.setCurrentFont(QFont(f_name))

        g_pre.check("폰트 굵게 (Bold)", s, "bold", True)

        g_dt = self.add_group("글자 세부 속성")
        g_dt.spin("글자 크기", s, "size", 18, 96, 44)
        g_dt.color_btn("텍스트 색상", s, "color", "텍스트 색상", "#FFFFFF")
        g_dt.spin("외곽선 두께", s, "border_size", 0, 10, 3)
        g_dt.color_btn("외곽선 색상", s, "outline_color", "외곽선 색상", "#101010")
        g_dt.spin("글로우 블러", s, "blur", 0, 20, 3)
        g_dt.spin("수직 위치 (%)", s, "pos", 30, 100, 94)
        g_dt.slider("줄바꿈 너비", s, "max_width_ratio", 50, 98, scale=0.01, default=0.88)

        g_sh = self.add_group("텍스트 그림자 효과 활성화", target=s, check_key="shadow_enabled", check_default=True)
        g_sh.color_btn("그림자 색상", s, "shadow_color", "그림자 색상", "#000000")
        g_sh.slider("그림자 농도", s, "shadow_opacity", 0, 100, scale=0.01, default=0.75)
        g_sh.slider("그림자 거리", s, "shadow_offset", 0, 20, fmt="{} px", default=4)
        g_sh.slider("그림자 번짐", s, "shadow_blur", 0, 15, fmt="{} px", default=4)

        g_an = self.add_group("등장 애니메이션")
        g_an.combo("적용 애니메이션", s, "anim_style", ["슬라이드 & 페이드", "자연스러운 페이드", "타자기", "팝업 바운스", "웨이브", "없음"], "슬라이드 & 페이드")
        g_an.combo("나타나는 방향", s, "slide_direction", ["아래에서 위로", "위에서 아래로", "왼쪽에서", "오른쪽에서", "없음"], "아래에서 위로")
        g_an.slider("이동 거리", s, "slide_distance", 4, 40, fmt="{} px", default=16)
        g_an.check("자연스럽게 나타나기 (Fade-in)", s, "fade_in_enabled", True)
        g_an.slider("페이드 시간", s, "fade_duration", 50, 600, fmt="{} ms", default=220)
        g_an.check("글자 차례대로 나타나기 (타자기 효과)", s, "typewriter_enabled", False)
        g_an.slider("타이핑 속도", s, "typewriter_speed", 10, 80, fmt="{} ms", default=28)


class EngineTab(BaseSettingsTab):
    def setup_ui(self):
        e = self.engine_cfg

        g_eng = self.add_group("엔진 최적화 및 디코딩")
        g_eng.check("오디오 자동 볼륨 노멀라이제이션", e, "audio_norm", True)
        g_eng.check("하드웨어 GPU 가속 디코딩 (권장)", e, "hwdec", True)

        g_fps = self.add_group("재생 및 효과 프레임 레이트 (FPS)")
        g_fps.slider("이펙트 애니메이션 FPS", e, "fps_effect", 10, 60, fmt="{} fps", default=24)
        g_fps.slider("앰비언트 백라이트 FPS", e, "fps_ambient", 10, 60, fmt="{} fps", default=30)
        g_fps.slider("그림자 FPS", e, "fps_shadow", 5, 60, fmt="{} fps", default=24)
        g_fps.slider("자막 갱신 FPS", e, "fps_subtitle", 10, 60, fmt="{} fps", default=self.sub_cfg.get("fps_subtitle", 30))
class SettingsDialog(AnimatedDialogBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.p = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(540, 680)
        self.setStyleSheet(Get_qss())

        self.sub_cfg = dict(self.p.sub_config)
        self.engine_cfg = dict(self.p.engine_config)
        self.b = ConfigBinder(self)

        self.init_ui()
        self._center_to_parent()

    def _center_to_parent(self):
        if self.p:
            geo = self.p.geometry()
            self.move(
                max(20, geo.x() + (geo.width() - self.width()) // 2),
                max(20, geo.y() + (geo.height() - self.height()) // 2)
            )

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        container = QFrame()
        container.setObjectName("dialogContainer")
        root.addWidget(container)

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(18, 14, 18, 16)
        vbox.setSpacing(12)

        header = DraggableHeader(self)
        header.setObjectName("dialogHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogCloseBtn")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.animated_close)
        h_layout.addWidget(QLabel("환경 설정", objectName="dialogTitle"))
        h_layout.addStretch()
        h_layout.addWidget(btn_close)
        vbox.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(FxTab(self), "영상 효과")
        self.tabs.addTab(AtmosTab(self), "배경")
        self.tabs.addTab(BorderTab(self), "테두리")
        self.tabs.addTab(SubTab(self), "자막 스타일")
        self.tabs.addTab(EngineTab(self), "재생 엔진")
        vbox.addWidget(self.tabs)

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedWidth(80)
        btn_cancel.clicked.connect(self.animated_close)
        btn_apply = QPushButton("저장", objectName="accentBtn")
        btn_apply.setFixedWidth(90)
        btn_apply.clicked.connect(self.save)
        h_btn.addWidget(btn_cancel)
        h_btn.addWidget(btn_apply)
        vbox.addLayout(h_btn)

    def apply_subtitle_preset(self, name: str):
        presets = {
            "기본": {"size": 44, "color": "#FFFFFF", "outline_color": "#101010", "border_size": 4, "blur": 3, "pos": 94, "bold": True, "anim_style": "슬라이드 & 페이드", "fade_in_enabled": True, "shadow_enabled": True, "shadow_color": "#000000", "shadow_opacity": 0.75, "shadow_offset": 4, "shadow_blur": 4},
            "시인성": {"size": 40, "color": "#FFF4D8", "outline_color": "#17131B", "border_size": 3, "blur": 2, "pos": 92, "bold": False, "anim_style": "자연스러운 페이드", "fade_in_enabled": True, "shadow_enabled": True, "shadow_color": "#000000", "shadow_opacity": 0.85, "shadow_offset": 3, "shadow_blur": 2},
            "네온": {"size": 44, "color": "#D9F8FF", "outline_color": "#173CFF", "border_size": 4, "blur": 8, "pos": 94, "bold": True, "anim_style": "팝업 바운스", "fade_in_enabled": True, "shadow_enabled": True, "shadow_color": "#0A1240", "shadow_opacity": 0.90, "shadow_offset": 5, "shadow_blur": 6},
            "부드러운 자막": {"size": 40, "color": "#F1F5F9", "outline_color": "#242936", "border_size": 2, "blur": 2, "pos": 93, "bold": False, "anim_style": "슬라이드 & 페이드", "fade_in_enabled": True, "shadow_enabled": False, "shadow_color": "#000000", "shadow_opacity": 0.50, "shadow_offset": 2, "shadow_blur": 2},
        }
        p = presets.get(name)
        if p:
            for k, val in p.items():
                self.b.set_val(k, val)

    def save(self):
        self.b.save()
        self.engine_cfg["ambient_glow"] = True
        self.engine_cfg["border_radius"] = self.engine_cfg.get("window_radius", 12)
        self.sub_cfg["fps_subtitle"] = self.engine_cfg.get("fps_subtitle", 30)

        self.p.apply_settings(self.sub_cfg, self.engine_cfg)
        self.animated_close()