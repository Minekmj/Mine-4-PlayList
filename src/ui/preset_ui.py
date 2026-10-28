from PyQt6.QtWidgets import (
    QMenu, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QLineEdit, QScrollArea, QGridLayout, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from src.main_logic.file import save_session
from src.ui.ffmpeg_ui import AnimatedDialogBase, DraggableHeader, Get_qss

class PresetCard(QFrame):
    def __init__(self, name: str, count: int, is_current: bool, on_select, on_rename=None, on_delete=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.on_select = on_select
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(175)
        self.setObjectName("presetGridCardActive" if is_current else "presetGridCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        lbl_name = QLabel(name)
        lbl_name.setObjectName("presetCardTitle")
        lbl_name.setWordWrap(True)
        top_layout.addWidget(lbl_name, 1)

        if on_rename:
            btn_edit = QPushButton("")
            btn_edit.setObjectName("presetCardActionBtn")
            btn_edit.setFixedSize(22, 22)
            btn_edit.setToolTip("이름 수정")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.clicked.connect(lambda: on_rename(name))
            top_layout.addWidget(btn_edit, 0, Qt.AlignmentFlag.AlignTop)

        if on_delete:
            btn_del = QPushButton("✕")
            btn_del.setObjectName("presetCardDeleteBtn")
            btn_del.setFixedSize(22, 22)
            btn_del.setToolTip("삭제")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.clicked.connect(lambda: on_delete(name))
            top_layout.addWidget(btn_del, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top_layout)

        line_deco = QFrame()
        line_deco.setObjectName("presetCardDecoLine")
        line_deco.setFixedHeight(1)
        layout.addWidget(line_deco)

        layout.addStretch()

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        lbl_count = QLabel(f"{count}곡 수록")
        lbl_count.setObjectName("presetCardCount")
        bottom_layout.addWidget(lbl_count)
        bottom_layout.addStretch()

        if is_current:
            lbl_badge = QLabel("선택됨")
            lbl_badge.setObjectName("presetCardBadge")
            bottom_layout.addWidget(lbl_badge)

        layout.addLayout(bottom_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QPushButton):
                super().mousePressEvent(event)
                return
            self.on_select(self.name)
        super().mousePressEvent(event)
        
class AddPresetCard(QFrame):
    def __init__(self, on_add_current, on_add_empty, parent=None):
        super().__init__(parent)
        self.on_add_current = on_add_current
        self.on_add_empty = on_add_empty
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(175)
        self.setObjectName("presetAddCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        lbl_plus = QLabel("+")
        lbl_plus.setObjectName("presetAddCardIcon")
        lbl_plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_plus)

        lbl_text = QLabel("새 프리셋 추가")
        lbl_text.setObjectName("presetAddCardText")
        lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            menu = QMenu(self)
            act_current = menu.addAction("현재 재생목록으로 추가")
            act_empty = menu.addAction("새로 생성 (빈 재생목록)")
            action = menu.exec(self.mapToGlobal(event.position().toPoint()))
            if action == act_current:
                self.on_add_current()
            elif action == act_empty:
                self.on_add_empty()
        super().mousePressEvent(event)
        
class PlaylistPresetDialog(AnimatedDialogBase):
    def __init__(self, parent):
        super().__init__(parent)
        self.p = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(500, 600)
        self.setStyleSheet(Get_qss())

        self.init_ui()
        self._center_to_parent()

    def _center_to_parent(self):
        if self.p:
            p_geo = self.p.geometry()
            x = p_geo.x() + (p_geo.width() - self.width()) // 2
            y = p_geo.y() + (p_geo.height() - self.height()) // 2
            self.move(max(20, x), max(20, y))

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("dialogContainer")
        root.addWidget(container)

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(18, 14, 18, 16)
        vbox.setSpacing(10)

        header = DraggableHeader(self)
        header.setObjectName("dialogHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("PLAYLIST 프리셋")
        lbl_title.setObjectName("dialogTitle")
        h_layout.addWidget(lbl_title)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogCloseBtn")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.animated_close)
        h_layout.addWidget(btn_close)
        vbox.addWidget(header)

        search_box = QFrame()
        search_box.setObjectName("cardFrame")
        sb_layout = QHBoxLayout(search_box)
        sb_layout.setContentsMargins(10, 8, 10, 8)
        sb_layout.setSpacing(8)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("프리셋 이름 검색...")
        self.inp_search.textChanged.connect(self.refresh_cards)
        sb_layout.addWidget(self.inp_search)
        vbox.addWidget(search_box)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.card_container = QWidget()
        self.grid_layout = QGridLayout(self.card_container)
        self.grid_layout.setContentsMargins(2, 4, 2, 8)
        self.grid_layout.setSpacing(12)
        self.scroll_area.setWidget(self.card_container)
        vbox.addWidget(self.scroll_area, 1)

        self.refresh_cards()

    def refresh_cards(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        presets = getattr(self.p, "playlist_preset", {})
        if "기본" not in presets:
            presets["기본"] = list(self.p.playlist)
            self.p.playlist_preset = presets

        cur_preset = getattr(self.p, "current_playlist_preset", "기본")
        query = self.inp_search.text().strip().lower()

        filtered_keys = [k for k in presets.keys() if not query or query in k.lower()]

        item_idx = 0
        for name in filtered_keys:
            row = item_idx // 2
            col = item_idx % 2
            count = len(presets.get(name, []))
            is_cur = (name == cur_preset)
            del_cb = (lambda n: self.delete_preset(n)) if name != "기본" else None
            ren_cb = (lambda n: self.rename_preset(n)) if name != "기본" else None

            card = PresetCard(
                name=name,
                count=count,
                is_current=is_cur,
                on_select=self.select_preset,
                on_rename=ren_cb,
                on_delete=del_cb
            )
            self.grid_layout.addWidget(card, row, col)
            item_idx += 1

        if not query:
            row = item_idx // 2
            col = item_idx % 2
            add_card = AddPresetCard(
                on_add_current=self.add_current_as_preset,
                on_add_empty=self.add_empty_preset
            )
            self.grid_layout.addWidget(add_card, row, col)

    def add_current_as_preset(self):
        name, ok = QInputDialog.getText(self, "프리셋 추가", "현재 목록을 저장할 프리셋 이름:")
        if not ok or not name.strip():
            return
        name = name.strip()

        if name in self.p.playlist_preset:
            res = QMessageBox.question(
                self, "덮어쓰기", f"'{name}' 프리셋이 이미 존재합니다. 덮어쓰시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if res != QMessageBox.StandardButton.Yes:
                return

        self.p.playlist_preset[name] = list(self.p.playlist)
        self.select_preset(name)
        
    def add_empty_preset(self):
        name, ok = QInputDialog.getText(self, "새 프리셋 생성", "새로 생성할 프리셋 이름:")
        if not ok or not name.strip():
            return
        name = name.strip()

        if name in self.p.playlist_preset:
            QMessageBox.warning(self, "경고", f"'{name}' 프리셋이 이미 존재합니다.")
            return

        self.p.playlist_preset[name] = []
        self.select_preset(name)
        
    def rename_preset(self, old_name: str):
        if old_name == "기본":
            QMessageBox.warning(self, "경고", "'기본' 프리셋의 이름은 변경할 수 없습니다.")
            return

        new_name, ok = QInputDialog.getText(self, "프리셋 이름 수정", "새로운 이름을 입력하세요:", text=old_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        if new_name == old_name:
            return

        if new_name in self.p.playlist_preset:
            QMessageBox.warning(self, "경고", f"'{new_name}' 이름의 프리셋이 이미 존재합니다.")
            return

        self.p.playlist_preset[new_name] = self.p.playlist_preset.pop(old_name)
        if getattr(self.p, "current_playlist_preset", "") == old_name:
            self.p.current_playlist_preset = new_name

        save_session(self.p)
        self.refresh_cards()

    def select_preset(self, name: str):
        if name not in self.p.playlist_preset:
            return
        self.p.playlist = list(self.p.playlist_preset[name])
        self.p.current_playlist_preset = name
        self.p.current_idx = 0 if self.p.playlist else -1
        self.p.refresh_playlist_view()
        save_session(self.p)
        self.refresh_cards()

    def delete_preset(self, name: str):
        if name == "기본":
            return
        res = QMessageBox.question(
            self, "프리셋 삭제", f"'{name}' 프리셋을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res != QMessageBox.StandardButton.Yes:
            return

        if name in self.p.playlist_preset:
            del self.p.playlist_preset[name]
            if getattr(self.p, "current_playlist_preset", "") == name:
                self.p.current_playlist_preset = "기본"
                self.p.playlist = list(self.p.playlist_preset.get("기본", []))
                self.p.current_idx = 0 if self.p.playlist else -1
                self.p.refresh_playlist_view()

            save_session(self.p)
            self.refresh_cards()