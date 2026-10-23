from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
from src.base import *

def top_bar(self):
    self.top_control_bar = QFrame(self)
    self.top_control_bar.setObjectName("topControlBar")

    top_bar_layout = QHBoxLayout(self.top_control_bar)
    top_bar_layout.setContentsMargins(12, 6, 12, 6)
    top_bar_layout.setSpacing(10)

    self.btn_win_min = QPushButton()
    self.btn_win_min.setObjectName("trafficBtn")
    self.btn_win_min.setStyleSheet("background-color: #F59E0B;")
    self.btn_win_min.setToolTip("최소화")
    self.btn_win_min.clicked.connect(self.showMinimized)

    self.btn_win_max = QPushButton()
    self.btn_win_max.setObjectName("trafficBtn")
    self.btn_win_max.setStyleSheet("background-color: #10B981;")
    self.btn_win_max.setToolTip("최대화 / 이전 크기")
    self.btn_win_max.clicked.connect(lambda: toggle_maximize_restore(self))

    self.btn_win_close = QPushButton()
    self.btn_win_close.setObjectName("trafficBtn")
    self.btn_win_close.setStyleSheet("background-color: #EF4444;")
    self.btn_win_close.setToolTip("닫기")
    self.btn_win_close.clicked.connect(self.close)

    top_bar_layout.addWidget(self.btn_win_min)
    top_bar_layout.addWidget(self.btn_win_max)
    top_bar_layout.addWidget(self.btn_win_close)

    self.top_control_bar.adjustSize()

    self._top_opacity = QGraphicsOpacityEffect(self.top_control_bar)
    self._top_opacity.setOpacity(0.0)
    self.top_control_bar.setGraphicsEffect(self._top_opacity)

    self._top_anim = QPropertyAnimation(self._top_opacity, b"opacity")
    self._top_anim.setDuration(140)
    self._top_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    self.top_bar_timer = QTimer(self)
    self.top_bar_timer.setSingleShot(True)
    self.top_bar_timer.setInterval(1500)
    self.top_bar_timer.timeout.connect(self._hide_top_bar)


def toggle_maximize_restore(self):
    if self.isMaximized():
        self.showNormal()
    else:
        self.showMaximized()
    QTimer.singleShot(60, lambda: self.core.reposition_subtitle() if self.core else None)