import os
import sys
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QIcon, QPixmap

from src.tools.theme import get_theme

from src.main_logic.file import read_session_state

_data = read_session_state()
if _data is not {} and _data is not None:
    data = _data.get("engine_config", {})
    os.environ["mine4playlist_use_opengl"] = (str)(data.get("use_OpenGL", False))
    os.environ["mine4playlist_use_opengl_video"] = (str)(data.get("use_OpenGL_video", False))
      
# from src.global_py.global_def import set_target, load_translations
# set_target("ko")
# load_translations()

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["SCRIPT_DIR"] = script_dir

    app = QApplication(sys.argv)

    splash_img_path = os.path.join(script_dir, "src", "icon", "splash.png")
    splash = QSplashScreen(QPixmap(splash_img_path))
    splash.show()
    app.processEvents()

    qss_path = os.path.join(script_dir, "src", "qss", "main.qss")
    app.setStyleSheet(get_theme(qss_path))

    icon_path = os.path.join(script_dir, "src", "icon", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    from src.main_window import EchoMediaPlayer
    player = EchoMediaPlayer()
    
    player.show()
    splash.finish(player)

    sys.exit(app.exec())