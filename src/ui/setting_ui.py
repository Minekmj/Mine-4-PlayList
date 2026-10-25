from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout,
    QPushButton, QSpinBox, QSlider, QCheckBox, QColorDialog,
    QFontComboBox, QLabel, QScrollArea, QFrame, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from src.ui.base import *


class ConfigBinder:
    def __init__(self, dialog: QWidget):
        self.dlg = dialog
        self.bindings: list[tuple[dict, str, callable]] = []
        self.setters: dict[str, callable] = {}

    def create_card(self) -> tuple[QFrame, QFormLayout]:
        card = QFrame()
        card.setObjectName("cardFrame")
        layout = QFormLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return card, layout

    def slider(self, form: QFormLayout, label: str, target: dict, key: str,
               v_min: int, v_max: int, scale: float = 1.0, fmt="{}%", default=0) -> QSlider:
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

        h = QHBoxLayout()
        h.addWidget(slider)
        h.addWidget(lbl)
        form.addRow(label, h)

        self.bindings.append((target, key, lambda: slider.value() * scale if scale != 1.0 else slider.value()))
        self.setters[key] = lambda v: slider.setValue(int(v / scale if scale != 1.0 else v))
        return slider

    def combo(self, form: QFormLayout, label: str, target: dict, key: str,
              items: list[str], default: str = "", val_map: dict = None, on_change=None) -> QComboBox:
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
        self.bindings.append((target, key, lambda: rev_map.get(cb.currentText(), cb.currentText()) if rev_map else cb.currentText()))
        self.setters[key] = lambda v: cb.setCurrentText(val_map.get(v, str(v)) if val_map else str(v))
        return cb

    def check(self, form: QFormLayout, text: str, target: dict, key: str, default: bool = False) -> QCheckBox:
        chk = QCheckBox(text)
        chk.setChecked(bool(target.get(key, default)))
        form.addRow(chk)
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

    def color_btn(self, target: dict, key: str, text: str = "색상 선택", default: str = "#FFFFFF", on_change=None) -> QPushButton:
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
                background-color: {color_hex}; color: {text_col};
                border: 1px solid rgba(0,0,0,0.15); border-radius: 6px;
                padding: 4px 10px; font-size: 11px; font-weight: 600;
            }}
            QPushButton:hover {{ border-color: #2563EB; }}
        """)

    def set_val(self, key: str, val):
        if key in self.setters:
            self.setters[key](val)

    def save(self):
        for target, key, getter in self.bindings:
            target[key] = getter()


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

    def _scroll_page(self, page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        page.setMinimumWidth(0)
        scroll.setWidget(page)
        return scroll

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
        self.tabs.addTab(self._scroll_page(self._build_fx_tab()), "영상 효과")
        self.tabs.addTab(self._scroll_page(self._build_atmos_tab()), "배경")
        self.tabs.addTab(self._scroll_page(self._build_border_tab()), "테두리")
        self.tabs.addTab(self._scroll_page(self._build_sub_tab()), "자막 스타일")
        self.tabs.addTab(self._scroll_page(self._build_engine_tab()), "재생 엔진")
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

    def _build_fx_tab(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(4, 8, 4, 8); l.setSpacing(10)
        b, e = self.b, self.engine_cfg

        c_amb, f = b.create_card()
        q_map = {35: "최소 (35%)", 50: "보통 (50%)", 85: "최대 (85%)", 100: "맥스 (100%)"}
        b.combo(f, "화면 화질 축소 비율", e, "ambient_quality_percent", list(q_map.values()), val_map=q_map, default=35)
        b.slider(f, "배경 밝기", e, "ambient_brightness", 30, 300, scale=0.01, default=1.65)
        b.slider(f, "암부 보정", e, "ambient_black_lift", 0, 50, scale=0.01, default=0.25)
        b.slider(f, "흐림 반경", e, "ambient_blur_radius", 4, 30, fmt="{} px", default=12)
        b.slider(f, "캡처 안쪽 여백", e, "ambient_crop_margin", 0, 25, default=5)
        l.addWidget(c_amb)

        c_crn, f = b.create_card()
        b.slider(f, "동영상 모서리 둥글기", e, "video_radius", 0, 48, fmt="{} px", default=8)
        b.slider(f, "창 모서리 둥글기", e, "window_radius", 0, 48, fmt="{} px", default=12)
        l.addWidget(c_crn)

        c_sh, f = b.create_card()
        b.check(f, "비디오 외곽 은은한 림라이트", e, "video_floating_rim", True)
        b.check(f, "드롭 섀도우 효과", e, "video_shadow_enabled", True)
        b.slider(f, "그림자 농도", e, "video_shadow_opacity", 5, 100, scale=0.01, default=0.25)
        b.slider(f, "그림자 번짐", e, "video_shadow_radius", 4, 60, fmt="{} px", default=28)
        b.slider(f, "대각선 거리", e, "video_shadow_offset", 0, 35, fmt="{} px", default=8)
        l.addWidget(c_sh)

        c_tint, f = b.create_card()
        b.check(f, "배경 앰비언트 컬러 틴트 추가", e, "ambient_tint_enabled", False)
        f.addRow("틴트 색상", b.color_btn(e, "ambient_tint_color", "틴트 색상", "#8FAACD"))
        b.slider(f, "틴트 농도", e, "ambient_tint_ratio", 5, 80, scale=0.01, default=0.20)
        l.addWidget(c_tint); l.addStretch()
        return w

    def _build_atmos_tab(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(4, 8, 4, 8); l.setSpacing(10)
        b, e = self.b, self.engine_cfg

        c_aurora, f = b.create_card()
        b.check(f, "오로라 애니메이션 배경 활성화", e, "aurora_enabled", True)
        b.combo(f, "오로라 유형", e, "aurora_style", ["오로라", "네온 파동", "없음"], "오로라")
        b.combo(f, "오로라 색상", e, "aurora_palette", ["청록", "벚꽃", "바다", "보라", "노을"], "청록")
        b.slider(f, "오로라 강도", e, "aurora_intensity", 0, 100, scale=0.01, default=0.55)
        l.addWidget(c_aurora)

        c_pt, f = b.create_card()
        b.check(f, "파티클 효과 활성화", e, "particle_enabled", True)
        b.combo(f, "파티클 종류", e, "particle_type",
                ["소프트 더스트", "사쿠라", "스타더스트", "보케 글로우", "라이트 레인", "하트", "페더", "음표", "크로스 스타", "기하학 큐브"],
                "소프트 더스트", val_map={"눈 / 먼지": "소프트 더스트", "벚꽃": "사쿠라", "별빛": "스타더스트", "빛망울": "보케 글로우", "비": "라이트 레인", "깃털": "페더", "반짝이": "크로스 스타", "네온 큐브": "기하학 큐브"})
        b.combo(f, "이동 방향", e, "particle_direction", ["아래로", "위로", "왼쪽 대각선", "오른쪽 대각선", "부유 / 흩날림"], "아래로")
        b.combo(f, "파티클 색상", e, "particle_palette",
                ["에메랄드 틸", "사쿠라 로즈", "딥 오션", "네뷸라 바이올렛", "선셋 앰버", "퓨어 화이트", "샴페인 골드", "사이버 네온", "소프트 핑크"],
                "에메랄드 틸", val_map={"청록": "에메랄드 틸", "벚꽃": "사쿠라 로즈", "바다": "딥 오션", "보라": "네뷸라 바이올렛", "노을": "선셋 앰버", "화이트": "퓨어 화이트", "골드": "샴페인 골드", "마법소녀": "소프트 핑크"})
        b.slider(f, "입자 밀도", e, "particle_density", 0, 100, scale=0.01, default=0.45)
        b.slider(f, "이동 속도", e, "particle_speed", 10, 300, scale=0.01, fmt=lambda v: f"{v/100:.1f}x", default=1.0)
        l.addWidget(c_pt); l.addStretch()
        return w

    def _build_border_tab(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(4, 8, 4, 8); l.setSpacing(10)
        b, e = self.b, self.engine_cfg

        c_b, f = b.create_card()
        b.check(f, "화면 테두리 오버레이 활성화", e, "border_enabled", True)
        b.combo(f, "프레임 스타일", e, "border_style", [
            "엣지 글로우", "미니멀 보더", "더블 라인", "테크니컬 브래킷",
            "인셋 프레임", "스튜디오 챔퍼", "도트 매트릭스", "사이버 그루브",
            "옵티컬 비네트", "시네마틱 레터 림", "코너 크로스", "게이머 네온", "없음"
        ], "엣지 글로우")

        self.row_b_cols = QWidget()
        row_l = QHBoxLayout(self.row_b_cols)
        row_l.setContentsMargins(0, 0, 0, 0); row_l.setSpacing(8)
        self.btn_col1 = b.color_btn(e, "border_color1", "1차 색상", e.get("border_color", "#38BDF8"))
        self.btn_col2 = b.color_btn(e, "border_color2", "2차 색상", "#818CF8")
        row_l.addWidget(self.btn_col1); row_l.addWidget(self.btn_col2)

        def on_cmode_change(m):
            vis = m in ["단색", "듀얼 그라디언트"]
            self.row_b_cols.setVisible(vis)
            self.btn_col1.setVisible(vis)
            self.btn_col2.setVisible(m == "듀얼 그라디언트")

        b.combo(f, "컬러 모드", e, "border_color_mode", ["단색", "듀얼 그라디언트", "스펙트럼"], "단색", on_change=on_cmode_change)
        f.addRow("지정 색상", self.row_b_cols)
        on_cmode_change(e.get("border_color_mode", "단색"))

        b.combo(f, "애니메이션 효과", e, "border_anim_mode", ["정적", "브리딩 펄스", "로테이팅 체이스", "네온 플리커"], "브리딩 펄스")
        b.slider(f, "펄스 호흡 깊이", e, "border_pulse_depth", 0, 80, scale=0.01, default=0.35)
        b.slider(f, "효과 속도", e, "border_anim_speed", 20, 300, scale=0.01, fmt=lambda v: f"{v/100:.1f}x", default=1.0)
        b.slider(f, "선 두께", e, "border_width", 1, 24, fmt="{} px", default=3)
        b.slider(f, "화면 여백", e, "border_margin", 0, 50, fmt=lambda v: "화면 밀착" if v == 0 else f"{v} px", default=0)
        b.slider(f, "글로우 번짐", e, "border_glow_spread", 0, 40, fmt="{} px", default=14)
        b.slider(f, "불투명도", e, "border_opacity", 10, 100, scale=0.01, default=0.75)
        l.addWidget(c_b); l.addStretch()
        return w

    def _build_sub_tab(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(4, 8, 4, 8); l.setSpacing(10)
        b, s = self.b, self.sub_cfg

        c_pre, f = b.create_card()
        cb_preset = QComboBox()
        cb_preset.addItems(["직접 설정", "기본", "시인성", "네온", "부드러운 자막"])
        cb_preset.currentTextChanged.connect(self.apply_subtitle_preset)
        f.addRow("스타일 프리셋", cb_preset)

        font_cb = QFontComboBox()
        font_cb.setCurrentFont(QFont(s.get("font", "sans-serif")))
        f.addRow("폰트 패밀리", font_cb)
        b.bindings.append((s, "font", lambda: font_cb.currentFont().family()))
        b.setters["font"] = lambda f_name: font_cb.setCurrentFont(QFont(f_name))

        b.check(f, "폰트 굵게 (Bold)", s, "bold", True)
        l.addWidget(c_pre)

        c_dt, f = b.create_card()
        b.spin(f, "글자 크기", s, "size", 18, 96, 44)
        f.addRow("텍스트 색상", b.color_btn(s, "color", "텍스트 색상", "#FFFFFF"))
        b.spin(f, "외곽선 두께", s, "border_size", 0, 10, 3)
        f.addRow("외곽선 색상", b.color_btn(s, "outline_color", "외곽선 색상", "#101010"))
        b.spin(f, "글로우 블러", s, "blur", 0, 20, 3)
        b.spin(f, "수직 위치 (%)", s, "pos", 30, 100, 94)
        b.slider(f, "줄바꿈 너비", s, "max_width_ratio", 50, 98, scale=0.01, default=0.88)
        l.addWidget(c_dt)

        c_sh, f = b.create_card()
        b.check(f, "텍스트 그림자 효과 활성화", s, "shadow_enabled", True)
        f.addRow("그림자 색상", b.color_btn(s, "shadow_color", "그림자 색상", "#000000"))
        b.slider(f, "그림자 농도", s, "shadow_opacity", 0, 100, scale=0.01, default=0.75)
        b.slider(f, "그림자 거리", s, "shadow_offset", 0, 20, fmt="{} px", default=4)
        b.slider(f, "그림자 번짐", s, "shadow_blur", 0, 15, fmt="{} px", default=4)
        l.addWidget(c_sh)

        c_an, f = b.create_card()
        b.combo(f, "적용 애니메이션", s, "anim_style", ["슬라이드 & 페이드", "자연스러운 페이드", "타자기", "팝업 바운스", "웨이브", "없음"], "슬라이드 & 페이드")
        b.combo(f, "나타나는 방향", s, "slide_direction", ["아래에서 위로", "위에서 아래로", "왼쪽에서", "오른쪽에서", "없음"], "아래에서 위로")
        b.slider(f, "이동 거리", s, "slide_distance", 4, 40, fmt="{} px", default=16)
        b.check(f, "자연스럽게 나타나기 (Fade-in)", s, "fade_in_enabled", True)
        b.slider(f, "페이드 시간", s, "fade_duration", 50, 600, fmt="{} ms", default=220)
        b.check(f, "글자 차례대로 나타나기 (타자기 효과)", s, "typewriter_enabled", False)
        b.slider(f, "타이핑 속도", s, "typewriter_speed", 10, 80, fmt="{} ms", default=28)
        l.addWidget(c_an); l.addStretch()
        return w

    def _build_engine_tab(self) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(4, 8, 4, 8); l.setSpacing(10)
        b, e = self.b, self.engine_cfg

        c_eng, f = b.create_card()
        b.check(f, "오디오 자동 볼륨 노멀라이제이션", e, "audio_norm", True)
        b.check(f, "하드웨어 GPU 가속 디코딩 (권장)", e, "hwdec", True)
        l.addWidget(c_eng)

        c_fps, f = b.create_card()
        b.slider(f, "이펙트 애니메이션 FPS", e, "fps_effect", 10, 60, fmt="{} fps", default=24)
        b.slider(f, "앰비언트 백라이트 FPS", e, "fps_ambient", 10, 60, fmt="{} fps", default=30)
        b.slider(f, "그림자 FPS", e, "fps_shadow", 5, 60, fmt="{} fps", default=24)
        b.slider(f, "자막 갱신 FPS", e, "fps_subtitle", 10, 60, fmt="{} fps", default=self.sub_cfg.get("fps_subtitle", 30))
        l.addWidget(c_fps); l.addStretch()
        return w

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