import os
from PyQt6.QtWidgets import (
    QSlider, QLabel, QListWidget, QAbstractItemView, QFrame, 
    QToolTip, QWidget, QSizePolicy, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import (
    QDragEnterEvent, QDropEvent
)

class PlaylistItemCard(QWidget):
    OFFSET_DEFAULT = 32
    OFFSET_EXPANDED = 0

    def __init__(self, item, title: str, on_play_callback, parent=None):
        super().__init__(parent)
        self.item = item
        self.on_play_callback = on_play_callback

        self._offset = self.OFFSET_DEFAULT
        self._is_selected = False
        self._is_hovered = False

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(self._offset, 2, 2, 2)
        self.main_layout.setSpacing(0)

        self.inner_card = QFrame()
        self.inner_card.setObjectName("innerPlaylistCard")
        card_layout = QHBoxLayout(self.inner_card)
        card_layout.setContentsMargins(14, 6, 12, 6)
        card_layout.setSpacing(10)

        self.lbl_title = ElidedLabel(title)
        self.lbl_title.setObjectName("card_title")
        card_layout.addWidget(self.lbl_title)

        self.main_layout.addWidget(self.inner_card)

        self.anim = QPropertyAnimation(self, b"offset", self)
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuart)

        self.update_card_style()

    def get_offset(self):
        return self._offset

    def set_offset(self, val: int):
        self._offset = val
        self.main_layout.setContentsMargins(val, 2, 2, 2)
        self.lbl_title.update_elide()

    offset = pyqtProperty(int, get_offset, set_offset)

    def animate_to(self, target: int):
        if self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()
        self.anim.setStartValue(self._offset)
        self.anim.setEndValue(target)
        self.anim.start()

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self.update_card_style()
        self.animate_to(self.OFFSET_EXPANDED if (self._is_selected or self._is_hovered) else self.OFFSET_DEFAULT)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self.update_card_style()
        self.animate_to(self.OFFSET_EXPANDED)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self.update_card_style()
        if not self._is_selected:
            self.animate_to(self.OFFSET_DEFAULT)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            lw = self.item.listWidget()
            if lw:
                lw.setCurrentItem(self.item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_play_callback:
            self.on_play_callback(self.item)
        super().mouseDoubleClickEvent(event)

    def update_card_style(self):
        if self._is_selected:
            self.inner_card.setProperty("state", "selected")
        elif self._is_hovered:
            self.inner_card.setProperty("state", "hover")
        else:
            self.inner_card.setProperty("state", "normal")
        self.inner_card.style().unpolish(self.inner_card)
        self.inner_card.style().polish(self.inner_card)
        
class PlaylistWidget(QListWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if os.path.exists(url.toLocalFile())]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def set_full_text(self, text: str):
        self._full_text = text
        self.update_elide()

    def update_elide(self):
        metrics = self.fontMetrics()
        avail_w = max(10, self.width() - 4)
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, avail_w)
        super().setText(elided)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elide()
        
class FloatingGlassPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

class FluidSeekSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.total_seconds = 0.0
        self._hover_progress = 0.0

        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, val: float):
        self._hover_progress = val
        self.update()

    hoverProgress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def set_duration(self, seconds: float):
        self.total_seconds = max(0.0, seconds)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.pixel_pos_to_val(event.position().x())
            self.setValue(val)
            self.sliderMoved.emit(val)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.total_seconds > 0:
            pct = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
            target_sec = int(pct * self.total_seconds)
            time_str = f"{target_sec // 60:02d}:{target_sec % 60:02d}"
            QToolTip.showText(event.globalPosition().toPoint(), time_str, self)
        super().mouseMoveEvent(event)

    def pixel_pos_to_val(self, x):
        ratio = max(0.0, min(1.0, x / max(1, self.width())))
        return int(self.minimum() + ratio * (self.maximum() - self.minimum()))

class FloatingOSD(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, text: str, duration_ms: int = 1500):
        self.setText(text)
        self.adjustSize()
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = 30
            self.move(x, y)
        self.show()
        self.raise_()
        self.timer.start(duration_ms)