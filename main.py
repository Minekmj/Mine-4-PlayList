import os
import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["SCRIPT_DIR"] = script_dir

    app = QApplication(sys.argv)

    splash_img_path = os.path.join(script_dir, "src", "icon", "splash.png")
    splash = QSplashScreen(QPixmap(splash_img_path))
    splash.show()
    app.processEvents()

    qss_path = os.path.join(script_dir, "src", "qss", "main.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="UTF-8") as f:
            app.setStyleSheet(f.read())

    icon_path = os.path.join(script_dir, "src", "icon", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from src.main_window import EchoMediaPlayer
    player = EchoMediaPlayer()
    
    player.show()
    splash.finish(player)

    sys.exit(app.exec())