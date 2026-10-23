from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt

from src.main_logic.file import save_session
from src.ui.icons import ModernIcon
from src.widgets.widgets import FloatingGlassPanel, PlaylistWidget
from src.widgets.front import PlaylistItemCard

from src.base import *

def playlist_panel(self):
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
    self.list_widget.model().rowsMoved.connect(lambda:on_list_rows_moved(self))
    self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
    self.list_widget.currentItemChanged.connect(lambda x,y:on_list_item_changed(self, x, y))
    right_vbox.addWidget(self.list_widget)

def on_list_rows_moved(self):
    new_list = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]
    cur_item = self.playlist[self.current_idx] if 0 <= self.current_idx < len(self.playlist) else None
    self.playlist = new_list
    if cur_item in self.playlist:
        self.current_idx = self.playlist.index(cur_item)
    self.refresh_playlist_view()
    save_session(self)
    
def on_list_item_changed(self, current, previous):
    if previous:
        prev_card = self.list_widget.itemWidget(previous)
        if isinstance(prev_card, PlaylistItemCard):
            prev_card.set_selected(False)
    if current:
        cur_card = self.list_widget.itemWidget(current)
        if isinstance(cur_card, PlaylistItemCard):
            cur_card.set_selected(True)