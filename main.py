import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = script_dir + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.main_window import EchoMediaPlayer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    app.setStyleSheet(open(os.path.join(script_dir, "src", "qss", "main.qss"), "r", encoding="UTF-8").read())
    
    icon_path = os.path.join(script_dir, "src", "icon", "icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    player = EchoMediaPlayer()
    player.show()
    sys.exit(app.exec())