import os
import shutil
import threading
import urllib.request
import zipfile

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QEventLoop

from src.ui.base import *
from src.global_py.global_def import global_text

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

class FFmpegWorkerSignals(QObject):
    status = pyqtSignal(str)
    progress = pyqtSignal(int, float, float)
    finished = pyqtSignal(bool, str)


class FFmpegInstallerDialog(AnimatedDialogBase):
    def __init__(self, parent, target_dir: str):
        super().__init__(parent)
        self.p = parent
        self.target_dir = target_dir
        self.destination_ffmpeg = os.path.join(target_dir, "ffmpeg.exe")
        self.zip_path = os.path.join(target_dir, "ffmpeg-download.tmp.zip")
        self.success = False
        self._cancelled = False
        self._loop = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(440)
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

        container = QFrame()
        container.setObjectName("dialogContainer")
        root_layout.addWidget(container)

        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(18, 14, 18, 16)
        vbox.setSpacing(12)

        header = DraggableHeader(self)
        header.setObjectName("dialogHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(8)

        lbl_head = QLabel(global_text("FFmpeg 다운로드 및 설치"))
        lbl_head.setObjectName("dialogTitle")
        h_layout.addWidget(lbl_head)
        h_layout.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("dialogCloseBtn")
        btn_close.setFixedSize(26, 26)
        btn_close.clicked.connect(self.cancel_install)
        h_layout.addWidget(btn_close)

        vbox.addWidget(header)

        card = QFrame()
        card.setObjectName("cardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(8)

        self.status_lbl = QLabel(global_text("다운로드를 준비하는 중입니다..."))
        self.status_lbl.setStyleSheet("color: #FFF; font-size: 12px; font-weight: 600;")
        c_layout.addWidget(self.status_lbl)

        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setFixedHeight(8)
        c_layout.addWidget(self.prog_bar)

        self.detail_lbl = QLabel("0% (0.0 MB / 0.0 MB)")
        self.detail_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.detail_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        c_layout.addWidget(self.detail_lbl)

        vbox.addWidget(card)

        h_btn = QHBoxLayout()
        h_btn.addStretch()
        self.btn_cancel = QPushButton(global_text("취소"))
        self.btn_cancel.clicked.connect(self.cancel_install)
        h_btn.addWidget(self.btn_cancel)
        vbox.addLayout(h_btn)

    def exec_install(self) -> bool:
        self.signals = FFmpegWorkerSignals()
        self.signals.status.connect(self.status_lbl.setText)
        self.signals.progress.connect(self.on_progress)
        self.signals.finished.connect(self.on_finished)

        threading.Thread(target=self._run_install, daemon=True).start()
        self.show()

        self._loop = QEventLoop()
        self._loop.exec()
        return self.success

    def on_progress(self, percent: int, down_mb: float, total_mb: float):
        self.prog_bar.setValue(percent)
        self.detail_lbl.setText(f"{percent}% ({down_mb:.1f} MB / {total_mb:.1f} MB)")

    def cancel_install(self):
        ret = QMessageBox.question(
            self,
            global_text("설치 취소"),
            global_text("설치를 중단하시겠습니까?\nFFmpeg이 없으면 유튜브 다운로드가 불가능합니다."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if ret == QMessageBox.StandardButton.Yes:
            self._cancelled = True
            self.status_lbl.setText(global_text("설치 취소 중..."))
            self.btn_cancel.setEnabled(False)
            self._finish_and_close(False)

    def _finish_and_close(self, success: bool):
        self.success = success
        if self._loop and self._loop.isRunning():
            self._loop.quit()
        self.animated_close()

    def on_finished(self, success: bool, msg: str):
        if success:
            self.prog_bar.setValue(100)
            self.status_lbl.setText(global_text("설치 완료! 준비되었습니다."))
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(700, lambda: self._finish_and_close(True))
        else:
            if not self._cancelled:
                QMessageBox.critical(self, global_text("설치 오류"), f"{global_text('FFmpeg 다운로드 중 오류가 발생했습니다')}:\n{msg}")
            self._finish_and_close(False)

    def _run_install(self):
        try:
            self.signals.status.emit(global_text("FFmpeg 다운로드 중... 잠시 기다려주세요."))
            os.makedirs(self.target_dir, exist_ok=True)

            req = urllib.request.Request(
                FFMPEG_URL,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req) as resp, open(self.zip_path, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 64

                while True:
                    if self._cancelled:
                        return
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        down_mb = downloaded / (1024 * 1024)
                        tot_mb = total_size / (1024 * 1024)
                        self.signals.progress.emit(pct, down_mb, tot_mb)

            if self._cancelled:
                return

            self.signals.status.emit(global_text("압축 해제 및 ffmpeg.exe 배치 중..."))
            extracted = False
            with zipfile.ZipFile(self.zip_path, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.replace("\\", "/").endswith("bin/ffmpeg.exe"):
                        with zip_ref.open(file_info) as source, open(self.destination_ffmpeg, "wb") as target:
                            shutil.copyfileobj(source, target)
                        extracted = True
                        break

            if not extracted:
                raise RuntimeError(global_text("압축 파일 내에서 bin/ffmpeg.exe를 찾지 못했습니다."))

            self.signals.finished.emit(True, "")

        except Exception as e:
            self.signals.finished.emit(False, str(e))
        finally:
            if os.path.exists(self.zip_path):
                try:
                    os.remove(self.zip_path)
                except Exception:
                    pass


def ensure_ffmpeg(parent, target_dir: str) -> bool:
    
    ffmpeg_exe = os.path.join(target_dir, "ffmpeg.exe")

    if os.path.exists(ffmpeg_exe) or shutil.which("ffmpeg"):
        if os.path.exists(ffmpeg_exe) and target_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = target_dir + os.pathsep + os.environ.get("PATH", "")
        return True

    confirm = QMessageBox.question(
        parent,
        global_text("FFmpeg 설치 안내"),
        global_text("유튜브 동영상 다운로드 및 병합에 필요한 필수 구성 요소(FFmpeg)가 없습니다.\n\n지금 자동으로 다운로드하여 설치하시겠습니까?"),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )

    if confirm != QMessageBox.StandardButton.Yes:
        QMessageBox.warning(
            parent,
            global_text("경고: FFmpeg 미설치"),
            global_text("FFmpeg 설치가 취소되었습니다.\nFFmpeg 없이는 동영상을 다운로드할 수 없습니다.")
        )
        return False

    installer = FFmpegInstallerDialog(parent, target_dir)
    success = installer.exec_install()
    if success:
        os.environ["PATH"] = target_dir + os.pathsep + os.environ.get("PATH", "")
    return success