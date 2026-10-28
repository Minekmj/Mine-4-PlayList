import os

from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QSpinBox, QSlider, QCheckBox, QColorDialog,
    QLabel, QScrollArea, QFrame, QComboBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor

os.environ["mine4play_back_tab"] = "영상 효과"

class TabList(QTabWidget):
    def __init__(self):
        super().__init__()
        self.tab_names = []
        
        self.currentChanged.connect(self._on_tab_changed)
        
    def add(self, tab, name: str):
        self.addTab(tab, name)
        self.tab_names.append(name)
        
    def _on_tab_changed(self, index):
        if 0 <= index < len(self.tab_names):
            os.environ["mine4play_back_tab"] = self.tab_names[index]

class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.v_scrollbar = self.verticalScrollBar()
        self._anim = QPropertyAnimation(self.v_scrollbar, b"value")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(220)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta != 0:
            if self._anim.state() == QPropertyAnimation.State.Running:
                current_target = self._anim.endValue()
            else:
                current_target = self.v_scrollbar.value()

            step = -int(delta * 1.2)
            target = current_target + step

            target = max(self.v_scrollbar.minimum(), min(self.v_scrollbar.maximum(), target))

            self._anim.stop()
            self._anim.setStartValue(self.v_scrollbar.value())
            self._anim.setEndValue(target)
            self._anim.start()
            event.accept()
        else:
            super().wheelEvent(event)

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

        slider.wheelEvent = lambda event: event.ignore()

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

        cb.wheelEvent = lambda event: event.ignore()

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
    
    def label(self, form: QFormLayout, text: str) -> QLabel:
        la = QLabel(text)
        la.setObjectName("pub")
        form.addRow("", la)
        return la
    
    def button(self, form: QFormLayout, text: str, label: str, callback) -> QPushButton:
        bt = QPushButton(text)
        bt.setStyleSheet("margin-left: 10px; margin-right: 10px;")
        bt.clicked.connect(callback)
        form.addRow(label, bt)
        return bt

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

        sp.wheelEvent = lambda event: event.ignore()

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

    def save(self):
        for target, key, getter in self.bindings:
            target[key] = getter()

class SettingsGroup(QFrame):
    def __init__(self, binder: ConfigBinder, title: str = "",
                 target: dict = None, check_key: str = None,
                 check_default: bool = False, parent_item: "SettingsGroup" = None, 
                 parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.b = binder
        self.parent_item = parent_item
        self.form = QFormLayout(self)
        self.form.setContentsMargins(14, 12, 14, 12)
        self.form.setSpacing(3)
        self.form.setLabelAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self.inner_fields: list[QWidget] = []
        self.child_groups: list["SettingsGroup"] = []
        self.chk_toggle: QCheckBox | None = None

        if self.parent_item is not None:
            self.parent_item.child_groups.append(self)

        if check_key is not None and target is not None:
            self.chk_toggle = self.b.check(
                self.form, title or "활성화", target, check_key,
                check_default, self._on_toggle
            )
            self.chk_toggle.setStyleSheet("font-weight: 700;")
        elif title:
            lbl = QLabel(title)
            lbl.setStyleSheet("font-weight: 700;")
            self.form.addRow(lbl)

        if self.parent_item is not None:
            self.setVisible(self.parent_item.is_active())

    def is_active(self) -> bool:
        my_active = (self.chk_toggle is None or self.chk_toggle.isChecked())
        if not my_active:
            return False
        if self.parent_item is not None:
            return self.parent_item.is_active()
        return True

    def update_visibility(self):
        if self.parent_item is not None:
            parent_active = self.parent_item.is_active()
            self.setVisible(parent_active)
            if not parent_active:
                return
            
        my_active = (self.chk_toggle is None or self.chk_toggle.isChecked())
        for field in self.inner_fields:
            field.setVisible(my_active)
            label = self.form.labelForField(field)
            if label:
                label.setVisible(my_active)

        for child in self.child_groups:
            child.update_visibility()

    def _register_field(self, field: QWidget):
        self.inner_fields.append(field)
        my_active = (self.chk_toggle is None or self.chk_toggle.isChecked())
        field.setVisible(my_active)
        label = self.form.labelForField(field)
        if label:
            label.setVisible(my_active)

    def _on_toggle(self, checked: bool = None):
        self.update_visibility()

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
    
    def label(self, text: str) -> QLabel:
        la = self.b.label(
            self.form, text
        )
        self._register_field(la)
        return la
    
    def button(self, label: str, text: str, callback) -> QLabel:
        bt = self.b.button(
            self.form, label, text, callback
        )
        self._register_field(bt)
        return bt

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

class BaseSettingsTab(SmoothScrollArea):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dlg = dialog
        self.b = dialog.b
        self.engine_cfg = dialog.engine_cfg
        self.sub_cfg = dialog.sub_cfg

        self.page = QWidget()
        self.page.setMinimumWidth(0)
        self.layout = QVBoxLayout(self.page)
        self.layout.setContentsMargins(6, 8, 10, 8)
        self.layout.setSpacing(10)
        self.setWidget(self.page)
        self.setup_ui()
        self.layout.addStretch()

    def setup_ui(self):
        pass

    def add_group(self, title: str = "", target: dict = None,
                  check_key: str = None,
                  check_default: bool = False,
                  parent_item: SettingsGroup=None) -> SettingsGroup:
        grp = SettingsGroup(
            binder=self.b, title=title, target=target,
            check_key=check_key, check_default=check_default, parent_item=parent_item,
            parent=self.page
        )
        self.layout.addWidget(grp)
        return grp