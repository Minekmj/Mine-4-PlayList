from PyQt6.QtWidgets import QWidget

class ContainerLayoutManager:
    def __init__(self):
        self.video_aspect = 16.0 / 9.0
        self.playlist_visible = True
        self.is_mini_mode = False

    @staticmethod
    def set_widget_geometry(widget: QWidget, x: int, y: int, width: int, height: int):
        geometry = (int(x), int(y), max(0, int(width)), max(0, int(height)))
        if tuple(widget.geometry().getRect()) != geometry:
            widget.setGeometry(*geometry)

    def update_geometries(self, container_w: int, container_h: int, video_w: QWidget, dock_w: QWidget, list_w: QWidget) -> bool:
        if not video_w or not dock_w or not list_w:
            return False

        W, H = container_w, container_h
        old_video_rect = tuple(video_w.geometry().getRect())

        if self.is_mini_mode:
            pad = 12
            avail_w = max(40, W - pad * 2)
            avail_h = max(40, H - pad * 2)
            if avail_w / max(1.0, avail_h) > self.video_aspect:
                target_h = int(avail_h)
                target_w = int(round(target_h * self.video_aspect))
            else:
                target_w = int(avail_w)
                target_h = int(round(target_w / self.video_aspect))
            vx = (W - target_w) // 2
            vy = (H - target_h) // 2
            self.set_widget_geometry(video_w, vx, vy, target_w, target_h)
            if not video_w.isVisible():
                video_w.show()
            if dock_w.isVisible():
                dock_w.hide()
            if list_w.isVisible():
                list_w.hide()
        else:
            pad = 16
            plist_w = 330 if self.playlist_visible else 0
            if self.playlist_visible:
                self.set_widget_geometry(list_w, W - plist_w - pad, pad, plist_w, max(0, H - 2 * pad))

            avail_w = max(100, W - (plist_w + pad * 2 if self.playlist_visible else pad * 2) - 100)
            avail_h = max(100, H - 220)
            if avail_w / max(1.0, avail_h) > self.video_aspect:
                target_h = int(avail_h)
                target_w = int(round(target_h * self.video_aspect))
            else:
                target_w = int(avail_w)
                target_h = int(round(target_w / self.video_aspect))

            view_center_x = (W - (plist_w + pad if self.playlist_visible else 0)) // 2
            view_center_y = (H - 50) // 2
            vx = view_center_x - target_w // 2
            vy = view_center_y - target_h // 2

            self.set_widget_geometry(video_w, vx, vy, target_w, target_h)
            if not video_w.isVisible():
                video_w.show()
                
            dock_w_val = min(880, max(520, target_w + 40))
            dock_h_val = 76
            self.set_widget_geometry(dock_w, view_center_x - dock_w_val // 2, H - dock_h_val - pad, dock_w_val, dock_h_val)

        return tuple(video_w.geometry().getRect()) != old_video_rect

    @staticmethod
    def restore_child_stacking(video_w: QWidget, dock_w: QWidget, list_w: QWidget, playlist_visible: bool):
        if not video_w or not dock_w or not list_w:
            return
        video_w.raise_()
        if dock_w.isVisible():
            dock_w.raise_()
        if playlist_visible and list_w.isVisible():
            list_w.raise_()