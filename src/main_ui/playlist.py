from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QAbstractItemView
from PyQt6.QtCore import Qt, QObject, QEvent, QPropertyAnimation, QEasingCurve

from src.main_logic.file import save_session
from src.ui.icons import ModernIcon
from src.widgets.widgets import FloatingGlassPanel, PlaylistWidget
from src.widgets.front import PlaylistItemCard
from src.base import *

class SmoothScrollFilter(QObject):
    def __init__(self, target: QAbstractItemView, parent=None):
        super().__init__(parent)
        self.target = target
        self.v_scrollbar = target.verticalScrollBar()
        
        self.anim = QPropertyAnimation(self.v_scrollbar, b"value")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(250)

    def eventFilter(self, obj, event):
        try:
            if obj == self.target.viewport() and event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                if delta != 0:
                    scroll_step = 100
                    direction = -1 if delta > 0 else 1
                    
                    current_target = (
                        self.anim.endValue() if self.anim.state() == QPropertyAnimation.State.Running 
                        else self.v_scrollbar.value()
                    )
                    
                    new_value = current_target + (direction * scroll_step)
                    new_value = max(self.v_scrollbar.minimum(), min(new_value, self.v_scrollbar.maximum()))
                    
                    self.anim.stop()
                    self.anim.setStartValue(self.v_scrollbar.value())
                    self.anim.setEndValue(new_value)
                    self.anim.start()
                    return True
                    
            return super().eventFilter(obj, event)
        except:
            pass
    
def playlist_panel(self):
    self.right_box = QFrame()
    self.right_box.setObjectName("right_ppanel")
    
    self.right_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    self.right_box.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
            
    right_vbox = QVBoxLayout(self.right_box)
    right_vbox.setContentsMargins(6, 6, 6, 6)
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
    self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    self.list_widget.setVerticalScrollMode(self.list_widget.ScrollMode.ScrollPerPixel)
    self.smooth_scroll = SmoothScrollFilter(self.list_widget)
    self.list_widget.viewport().installEventFilter(self.smooth_scroll)
    self.list_widget.setSpacing(5)
    self.list_widget.files_dropped.connect(self.handle_dropped_files)
    self.list_widget.model().rowsMoved.connect(lambda: on_list_rows_moved(self))
    self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
    
    self.currect_item = None
    self.list_widget.currentItemChanged.connect(lambda x, y: on_list_item_changed(self, x, y))
    right_vbox.addWidget(self.list_widget)
    
    self.list_set = lambda i: set_list_by_index(self, i)
    
def set_list_by_index(self, idx):
    prev_item = self.list_widget.currentItem()
    cur_item = self.list_widget.item(idx)
    
    self.list_widget.setCurrentRow(idx)
    
    on_list_item_changed(self, cur_item, prev_item, True)

def on_list_rows_moved(self):
    new_list = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]
    cur_item = self.playlist[self.current_idx] if 0 <= self.current_idx < len(self.playlist) else None
    self.playlist = new_list
    if cur_item in self.playlist:
        self.current_idx = self.playlist.index(cur_item)
    self.refresh_playlist_view()
    save_session(self)
    
def on_list_item_changed(self, current, previous, back=False):
    if previous and (back or self.currect_item != previous):
        prev_card = self.list_widget.itemWidget(previous)
        if isinstance(prev_card, PlaylistItemCard):
            prev_card.set_selected(False)
        
        if back and self.currect_item:
            prev_cur_card = self.list_widget.itemWidget(self.currect_item)
            if isinstance(prev_cur_card, PlaylistItemCard):
                prev_cur_card.set_selected(False)
            
    if current:
        cur_card = self.list_widget.itemWidget(current)
        if isinstance(cur_card, PlaylistItemCard):
            cur_card.set_selected(True)
            if back:
                self.currect_item = current