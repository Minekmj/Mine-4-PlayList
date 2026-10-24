from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRectF
from src.ui.icons import ModernIcon
from pyvda import AppView

hwnd = 0
class MiniTopBar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_win = parent
        self.setObjectName("topControlBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.btn_restore = QPushButton()
        self.btn_restore.setIcon(ModernIcon.create("expand", "#FFFFFF", 15))
        self.btn_restore.setFixedSize(22, 22)
        self.btn_restore.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.25); }"
        )
        self.btn_restore.setToolTip("원래 크기로 복원 (더블클릭 또는 P)")
        self.btn_restore.clicked.connect(lambda: exit_mini_mode(self.main_win))

        self.btn_close = QPushButton()
        self.btn_close.setIcon(ModernIcon.create("close", "#F87171", 13))
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.3); }"
        )
        self.btn_close.setToolTip("닫기")
        self.btn_close.clicked.connect(self.main_win.close)

        layout.addWidget(self.btn_restore)
        layout.addWidget(self.btn_close)
        self.adjustSize()

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        self._anim = QPropertyAnimation(self._opacity, b"opacity")
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(1500)
        self._inactivity_timer.timeout.connect(self.fast_hide)

    def on_top_activity(self):
        if self._opacity.opacity() < 0.95:
            self.show()
            self.raise_()
            self._anim.stop()
            self._anim.setStartValue(self._opacity.opacity())
            self._anim.setEndValue(1.0)
            self._anim.start()
        self._inactivity_timer.start(1500)

    def fast_hide(self):
        self._inactivity_timer.stop()
        if self._opacity.opacity() > 0.05:
            self._anim.stop()
            self._anim.setStartValue(self._opacity.opacity())
            self._anim.setEndValue(0.0)
            self._anim.start()


def toggle_mini_mode(main_win):
    if getattr(main_win, "is_mini_mode", False):
        exit_mini_mode(main_win)
    else:
        enter_mini_mode(main_win)

def enter_mini_mode(main_win):
    global hwnd
    if getattr(main_win, "is_mini_mode", False) or main_win.isFullScreen():
        return

    main_win.is_mini_mode = True

    main_win._pre_mini_geo = main_win.geometry()
    main_win._pre_mini_plist = getattr(main_win.ambient_container, "playlist_visible", True)

    if hasattr(main_win, "top_control_bar"):
        main_win.top_control_bar.hide()
    if hasattr(main_win, "dock_panel"):
        main_win.dock_panel.hide()

    if hasattr(main_win, "ambient_container"):
        main_win.ambient_container.is_mini_mode = True
        main_win.ambient_container.set_playlist_visibility(False)

    main_win.setMinimumSize(240, 140)
    main_win.setMaximumSize(1200, 800)
    main_win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    main_win.show()
    
    def apply_pin():
        try:
            hwnd = int(main_win.winId())
            AppView(hwnd=hwnd).pin()
        except Exception as e:
            print(f"가상 데스크톱 고정 실패: {e}")

    QTimer.singleShot(100, apply_pin) 

    target_w, target_h = 420, 250
    old = main_win._pre_mini_geo
    nx = old.x() + (old.width() - target_w) // 2
    ny = old.y() + (old.height() - target_h) // 2
    main_win.setGeometry(nx, ny, target_w, target_h)

    if not hasattr(main_win, "mini_top_bar") or main_win.mini_top_bar is None:
        main_win.mini_top_bar = MiniTopBar(main_win)
    main_win.mini_top_bar.show()
    main_win.mini_top_bar.raise_()
    reposition_mini_bar(main_win)

    main_win._mini_resize_edge = None
    main_win._drag_pos = None
    reset_all_cursors(main_win)

    main_win.ambient_container.update_sub_geometries()
    QTimer.singleShot(50, lambda: main_win.core.reposition_subtitle() if getattr(main_win, "core", None) else None)


def exit_mini_mode(main_win):
    global hwnd
    if not getattr(main_win, "is_mini_mode", False):
        return

    main_win.is_mini_mode = False

    if hasattr(main_win, "mini_top_bar") and main_win.mini_top_bar:
        main_win.mini_top_bar.fast_hide()
        
    try:
        hwnd = int(main_win.winId())
        AppView(hwnd=hwnd).unpin()
    except Exception as e:
        print(f"가상 데스크톱 언고정 실패: {e}")

    main_win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
    main_win.setMinimumSize(960, 600)
    main_win.setMaximumSize(16777215, 16777215)
    main_win.show()

    if hasattr(main_win, "_pre_mini_geo") and main_win._pre_mini_geo:
        main_win.setGeometry(main_win._pre_mini_geo)
    else:
        main_win.resize(1300, 820)

    if hasattr(main_win, "ambient_container"):
        main_win.ambient_container.is_mini_mode = False
        prev_plist = getattr(main_win, "_pre_mini_plist", True)
        main_win.ambient_container.set_playlist_visibility(prev_plist)

    if hasattr(main_win, "dock_panel"):
        main_win.dock_panel.show()

    reset_all_cursors(main_win)
    main_win.ambient_container.update_sub_geometries()
    QTimer.singleShot(50, lambda: main_win.core.reposition_subtitle() if getattr(main_win, "core", None) else None)


def reposition_mini_bar(main_win):
    if hasattr(main_win, "mini_top_bar") and main_win.mini_top_bar:
        bx = (main_win.width() - main_win.mini_top_bar.width()) // 2
        main_win.mini_top_bar.move(bx, 6)


def get_resize_edge(main_win, pos: QPoint):
    margin = 7
    w, h = main_win.width(), main_win.height()
    x, y = pos.x(), pos.y()

    if x < 0 or y < 0 or x > w or y > h:
        return None

    left = x <= margin
    right = x >= w - margin
    top = y <= margin
    bottom = y >= h - margin

    if top and left: return "top_left"
    if top and right: return "top_right"
    if bottom and left: return "bottom_left"
    if bottom and right: return "bottom_right"
    if left: return "left"
    if right: return "right"
    if top: return "top"
    if bottom: return "bottom"
    return None


def update_cursor_for_edge(main_win, edge):
    cursors = {
        "top_left": Qt.CursorShape.SizeFDiagCursor,
        "bottom_right": Qt.CursorShape.SizeFDiagCursor,
        "top_right": Qt.CursorShape.SizeBDiagCursor,
        "bottom_left": Qt.CursorShape.SizeBDiagCursor,
        "left": Qt.CursorShape.SizeHorCursor,
        "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor,
        "bottom": Qt.CursorShape.SizeVerCursor,
    }
    if edge in cursors:
        cur = cursors[edge]
        main_win.setCursor(cur)
        if hasattr(main_win, "ambient_container"):
            main_win.ambient_container.setCursor(cur)
    else:
        reset_all_cursors(main_win)


def reset_all_cursors(main_win):
    main_win.unsetCursor()
    if hasattr(main_win, "ambient_container"):
        main_win.ambient_container.unsetCursor()
    if hasattr(main_win, "video_frame"):
        main_win.video_frame.unsetCursor()
    core = getattr(main_win, "core", None)
    if core and hasattr(core, "view") and core.view:
        core.view.unsetCursor()
        if core.view.viewport():
            core.view.viewport().unsetCursor()


def is_in_play_click_zone(video_widget, local_pos: QPoint) -> bool:
    vw = video_widget.width()
    vh = video_widget.height()
    if vw <= 0 or vh <= 0:
        return False

    margin_x = vw * 0.10
    margin_y = vh * 0.10
    inner_rect = QRectF(margin_x, margin_y, vw - margin_x * 2, vh - margin_y * 2)

    return inner_rect.contains(local_pos.x(), local_pos.y())