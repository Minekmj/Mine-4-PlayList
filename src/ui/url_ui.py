import os
import threading
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QFrame
)
from PyQt6.QtCore import Qt

from src.download.downloader import run_youtube_download, DownloadSignals
from src.ui.ffmpeg_ui import (
    ensure_ffmpeg, 
    AnimatedDialogBase, DraggableHeader, Get_qss
)

class UrlDialog(AnimatedDialogBase):
    def __init__(self, parent, default_dir: str):
        super().__init__(parent)
        self.p = parent
        self.default_dir = default_dir
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(460)

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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setObjectName("dialogContainer")
        root_layout.addWidget(self.container)

        vbox = QVBoxLayout(self.container)
        vbox.setContentsMargins(18, 14, 18, 16)
        vbox.setSpacing(12)

        header = DraggableHeader(self)
        header.setObjectName("dialogHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        lbl_head = QLabel("동영상 URL 가져오기")
        lbl_head.setObjectName("dialogTitle")
        h_layout.addWidget(lbl_head)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogCloseBtn")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.animated_close)
        h_layout.addWidget(btn_close)

        vbox.addWidget(header)

        card = QFrame()
        card.setObjectName("cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(10)

        lbl_desc = QLabel("YouTube 링크를 입력하세요:")
        lbl_desc.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500;")
        c_layout.addWidget(lbl_desc)

        self.inp = QLineEdit()
        self.inp.setPlaceholderText("https://...")
        c_layout.addWidget(self.inp)

        self.status = QLabel("다운로드 대기 중")
        self.status.setStyleSheet("color: #64748B; font-size: 11px;")
        c_layout.addWidget(self.status)

        vbox.addWidget(card)

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.animated_close)

        self.btn_run = QPushButton("다운로드 시작")
        self.btn_run.setObjectName("accentBtn")
        self.btn_run.clicked.connect(self.start_download)

        h_btn.addWidget(btn_cancel)
        h_btn.addWidget(self.btn_run)
        vbox.addLayout(h_btn)

    def start_download(self):
        url = self.inp.text().strip()
        if not url:
            return

        ffmpeg_dir = os.environ.get("SCRIPT_DIR", self.default_dir)
        if not ensure_ffmpeg(self, ffmpeg_dir):
            self.status.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600;")
            self.status.setText("FFmpeg 구성 요소가 없어 다운로드를 시작할 수 없습니다.")
            return

        self.btn_run.setEnabled(False)
        self.inp.setEnabled(False)
        self.status.setStyleSheet("color: #2563EB; font-size: 11px; font-weight: 600;")
        self.status.setText("영상 정보를 분석하는 중...")

        signals = DownloadSignals()
        signals.status.connect(self.status.setText)
        signals.finished.connect(self.on_finished)
        signals.error.connect(self.on_error)

        threading.Thread(
            target=run_youtube_download,
            args=(url, self.default_dir, signals),
            daemon=True
        ).start()

    def on_finished(self, filepath: str):
        self.p.handle_dropped_files([filepath])
        self.p.osd.show_message("다운로드 완료!")
        self.animated_close()

    def on_error(self, err: str):
        self.status.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 600;")
        self.status.setText(f"오류: {err}")
        self.btn_run.setEnabled(True)
        self.inp.setEnabled(True)