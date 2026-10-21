import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["SCRIPT_DIR"] = script_dir
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from src.main_window import EchoMediaPlayer

if __name__ == "__main__":
    app = QApplication(sys.argv)

    qss_path = os.path.join(script_dir, "src", "qss", "main.qss")
    if os.path.exists(qss_path):
        app.setStyleSheet(open(qss_path, "r", encoding="UTF-8").read())

    icon_path = os.path.join(script_dir, "src", "icon", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    player = EchoMediaPlayer()
    player.show()
    sys.exit(app.exec())