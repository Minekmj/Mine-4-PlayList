from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QPen, QBrush, QColor


class ModernIcon:
    @staticmethod
    def create(name: str, color: str = "#E2E8F0", size: int = 24) -> QIcon:
        pixmap = QIcon()
        img = QPixmap(size, size)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        s = size / 24.0

        if name == "play":
            path = QPainterPath()
            path.moveTo(8 * s, 5 * s)
            path.lineTo(19 * s, 12 * s)
            path.lineTo(8 * s, 19 * s)
            path.closeSubpath()
            p.setBrush(QBrush(QColor(color)))
            p.drawPath(path)

        elif name == "pause":
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(QRectF(6 * s, 5 * s, 3.5 * s, 14 * s), 1.5, 1.5)
            p.drawRoundedRect(QRectF(14.5 * s, 5 * s, 3.5 * s, 14 * s), 1.5, 1.5)

        elif name == "prev":
            path = QPainterPath()
            path.moveTo(18 * s, 6 * s)
            path.lineTo(9 * s, 12 * s)
            path.lineTo(18 * s, 18 * s)
            path.closeSubpath()
            p.setBrush(QBrush(QColor(color)))
            p.drawPath(path)
            p.drawRoundedRect(QRectF(6 * s, 6 * s, 2 * s, 12 * s), 1, 1)

        elif name == "next":
            path = QPainterPath()
            path.moveTo(6 * s, 6 * s)
            path.lineTo(15 * s, 12 * s)
            path.lineTo(6 * s, 18 * s)
            path.closeSubpath()
            p.setBrush(QBrush(QColor(color)))
            p.drawPath(path)
            p.drawRoundedRect(QRectF(16 * s, 6 * s, 2 * s, 12 * s), 1, 1)

        elif name == "volume":
            path = QPainterPath()
            path.moveTo(4 * s, 9 * s)
            path.lineTo(8 * s, 9 * s)
            path.lineTo(13 * s, 5 * s)
            path.lineTo(13 * s, 19 * s)
            path.lineTo(8 * s, 15 * s)
            path.lineTo(4 * s, 15 * s)
            path.closeSubpath()
            p.setBrush(QBrush(QColor(color)))
            p.drawPath(path)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(14 * s, 8 * s, 5 * s, 8 * s), -60 * 16, 120 * 16)

        elif name == "mute":
            path = QPainterPath()
            path.moveTo(4 * s, 9 * s)
            path.lineTo(8 * s, 9 * s)
            path.lineTo(13 * s, 5 * s)
            path.lineTo(13 * s, 19 * s)
            path.lineTo(8 * s, 15 * s)
            path.lineTo(4 * s, 15 * s)
            path.closeSubpath()
            p.setBrush(QBrush(QColor(color)))
            p.drawPath(path)
            p.drawLine(int(16 * s), int(9 * s), int(21 * s), int(15 * s))
            p.drawLine(int(21 * s), int(9 * s), int(16 * s), int(15 * s))

        elif name == "fullscreen":
            p.drawPolyline([QPoint(int(5 * s), int(9 * s)), QPoint(int(5 * s), int(5 * s)), QPoint(int(9 * s), int(5 * s))])
            p.drawPolyline([QPoint(int(15 * s), int(5 * s)), QPoint(int(19 * s), int(5 * s)), QPoint(int(19 * s), int(9 * s))])
            p.drawPolyline([QPoint(int(5 * s), int(15 * s)), QPoint(int(5 * s), int(19 * s)), QPoint(int(9 * s), int(19 * s))])
            p.drawPolyline([QPoint(int(15 * s), int(19 * s)), QPoint(int(19 * s), int(19 * s)), QPoint(int(19 * s), int(15 * s))])

        elif name == "restore":
            p.drawRect(QRectF(7 * s, 7 * s, 10 * s, 10 * s))

        elif name == "playlist":
            p.drawLine(int(4 * s), int(7 * s), int(20 * s), int(7 * s))
            p.drawLine(int(4 * s), int(12 * s), int(20 * s), int(12 * s))
            p.drawLine(int(4 * s), int(17 * s), int(14 * s), int(17 * s))

        elif name == "gear":
            p.drawEllipse(QRectF(8 * s, 8 * s, 8 * s, 8 * s))
            p.drawEllipse(QRectF(5 * s, 5 * s, 14 * s, 14 * s))

        elif name == "folder":
            path = QPainterPath()
            path.moveTo(3 * s, 6 * s)
            path.lineTo(9 * s, 6 * s)
            path.lineTo(11 * s, 8 * s)
            path.lineTo(21 * s, 8 * s)
            path.lineTo(21 * s, 19 * s)
            path.lineTo(3 * s, 19 * s)
            path.closeSubpath()
            p.drawPath(path)

        elif name == "url":
            p.drawEllipse(QRectF(4 * s, 4 * s, 16 * s, 16 * s))
            p.drawEllipse(QRectF(8 * s, 4 * s, 8 * s, 16 * s))
            p.drawLine(int(4 * s), int(12 * s), int(20 * s), int(12 * s))

        elif name == "subtitle":
            p.drawRoundedRect(QRectF(3.5 * s, 5.5 * s, 17 * s, 13 * s), 2.5, 2.5)
            p.drawLine(int(7 * s), int(10 * s), int(13 * s), int(10 * s))
            p.drawLine(int(7 * s), int(14 * s), int(17 * s), int(14 * s))

        elif name == "subtitle_off":
            p.drawRoundedRect(QRectF(3.5 * s, 5.5 * s, 17 * s, 13 * s), 2.5, 2.5)
            p.drawLine(int(7 * s), int(10 * s), int(13 * s), int(10 * s))
            p.drawLine(int(7 * s), int(14 * s), int(17 * s), int(14 * s))
            pen_slash = QPen(QColor("#EF4444"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen_slash)
            p.drawLine(int(4 * s), int(4 * s), int(20 * s), int(20 * s))

        p.end()
        pixmap.addPixmap(img)
        return pixmap