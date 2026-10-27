import os
import sys
from PyQt6.QtWidgets import QFileDialog, QMenu, QListWidgetItem
from PyQt6.QtCore import Qt, QSize, QPoint
from src.widgets.widgets import PlaylistItemCard
from src.main_logic.file import save_session
from src.main_logic.media import collect_media_files

def refresh_playlist_view(self):
    self.list_widget.blockSignals(True)
    self.list_widget.clear()

    for idx, path in enumerate(self.playlist):
        title = os.path.splitext(os.path.basename(path))[0]
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 44))
        item.setData(Qt.ItemDataRole.UserRole, path)

        card = PlaylistItemCard(
            item=item,
            title=f"{idx + 1:02d}.  {title}",
            on_play_callback=self.on_item_double_click
        )
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, card)

    self.list_widget.blockSignals(False)
    self.lbl_list_count.setText(f"({len(self.playlist)})")
    self.highlight_playing_row()

    if hasattr(self, 'core') and self.core:
        self.core.preload_playlist_gains(self.playlist)

def highlight_playing_row(self):
    if 0 <= self.current_idx < len(self.playlist):
        cur = self.playlist[self.current_idx]
        for i in range(self.list_widget.count()):
            it = self.list_widget.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == cur:
                if hasattr(self, 'list_set'):
                    self.list_set(i)
                break

def handle_dropped_files(self, paths):
    added = collect_media_files(paths)
    if added:
        start_first = len(self.playlist) == 0
        for item in added:
            if item not in self.playlist:
                self.playlist.append(item)
        self.refresh_playlist_view()
        save_session(self)
        if start_first:
            self.play_index(0)

def open_media_files(self):
    files, _ = QFileDialog.getOpenFileNames(
        self, "파일 선택", "",
        "Media Files (*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.flac *.wav)"
    )
    if files:
        handle_dropped_files(self, files)

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
            save_session(self)