import os
from PyQt6.QtWidgets import QWidget, QFrame
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve

qss_path = os.path.join(os.environ["SCRIPT_DIR"], "src", "qss", "dialog.qss")
_QSS = open(qss_path, "r", encoding="UTF-8").read()

def Get_qss():
    return _QSS

class DraggableHeader(QFrame):
    def __init__(self, target_widget, parent=None):
        super().__init__(parent)
        self.target_widget = target_widget
        self._drag_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.target_widget.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.target_widget.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()


class AnimatedDialogBase(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(160)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        self.setWindowOpacity(0.0)
        super().showEvent(event)
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def animated_close(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self.close)
        self._fade_anim.start()