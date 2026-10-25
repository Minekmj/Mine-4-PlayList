import os
import sys
import threading

script_dir = os.path.dirname(os.path.abspath(__file__))
os.environ["SCRIPT_DIR"] = script_dir

import tkinter as tk

loaded_modules = {}


def load_pyqt_and_app():
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
    from src.main_window import EchoMediaPlayer

    loaded_modules["QApplication"] = QApplication
    loaded_modules["QIcon"] = QIcon
    loaded_modules["EchoMediaPlayer"] = EchoMediaPlayer


def check_module_loaded(splash_root):
    if "EchoMediaPlayer" in loaded_modules:
        splash_root.destroy()
    else:
        splash_root.after(50, lambda: check_module_loaded(splash_root))


def show_splash():
    root = tk.Tk()
    root.overrideredirect(True)

    width, height = 400, 100
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.configure(bg="#1e1e1e")

    splash_img_path = os.path.join(script_dir, "src", "icon", "splash.png")
    
    img = tk.PhotoImage(file=splash_img_path)
    label = tk.Label(root, image=img, borderwidth=0)
    label.image = img
    label.pack(expand=True, fill="both")
        
    thread = threading.Thread(target=load_pyqt_and_app, daemon=True)
    thread.start()

    root.after(50, lambda: check_module_loaded(root))
    root.mainloop()


if __name__ == "__main__":
    show_splash()

    QApplication = loaded_modules["QApplication"]
    QIcon = loaded_modules["QIcon"]
    EchoMediaPlayer = loaded_modules["EchoMediaPlayer"]

    app = QApplication(sys.argv)

    qss_path = os.path.join(script_dir, "src", "qss", "main.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="UTF-8") as f:
            app.setStyleSheet(f.read())

    icon_path = os.path.join(script_dir, "src", "icon", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    player = EchoMediaPlayer()
    player.show()

    sys.exit(app.exec())