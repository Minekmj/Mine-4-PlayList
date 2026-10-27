import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygonF

from src.effect.logic.border import ScreenBorderSystem, register_border
from src.effect.logic.border_anime import get_animation

@register_border("네온")
def draw_neon(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    anim = get_animation(sys.anim_mode)
    pulse_spread = anim.get_glow_spread_offset(sys)
    spread = float(max(4.0, sys.glow_spread + pulse_spread))
    path = sys._get_base_rounded_path(w, h)

    p.setBrush(Qt.BrushStyle.NoBrush)
    steps = 8
    base_w = float(sys.width)
    for i in range(steps, 0, -1):
        ratio = i / float(steps)
        cur_w = base_w + spread * ratio * 2.2
        glow_a = max(0, min(255, int(alpha * math.exp(-3.0 * (ratio ** 2)) * 0.42)))
        if glow_a > 0:
            p.setPen(sys._create_styled_pen(w, h, cur_w, glow_a))
            p.drawPath(path)

    p.setPen(sys._create_styled_pen(w, h, base_w, alpha))
    p.drawPath(path)


@register_border("기본")
def draw_minimal(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    path = sys._get_base_rounded_path(w, h)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(sys._create_styled_pen(w, h, float(sys.width), alpha))
    p.drawPath(path)


@register_border("이중선")
def draw_double_line(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(sys.margin)
    r = float(sys.radius)
    p.setBrush(Qt.BrushStyle.NoBrush)

    p.setPen(sys._create_styled_pen(w, h, float(sys.width), alpha))
    p.drawPath(sys._get_base_rounded_path(w, h))

    offset = max(4.0, float(sys.width) + 2.0)
    m2 = m + offset
    r2 = max(0.0, r - offset)
    if w - m2 * 2 > 10 and h - m2 * 2 > 10:
        p2 = QPainterPath()
        if r2 > 0.5:
            p2.addRoundedRect(QRectF(m2, m2, w - m2 * 2, h - m2 * 2), r2, r2)
        else:
            p2.addRect(QRectF(m2, m2, w - m2 * 2, h - m2 * 2))
        p.setPen(sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.5)))))
        p.drawPath(p2)


@register_border("브래킷")
def draw_technical_bracket(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    thick = float(sys.width)
    half_w = thick * 0.5
    m_inner = float(sys.margin) + half_w + 3.0
    r_inner = max(0.0, float(sys.radius) - half_w - 3.0)
    arm = min(72.0, max(24.0, min(w, h) * 0.08))
    p.setBrush(Qt.BrushStyle.NoBrush)

    sub_pen = sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.25))))
    sub_pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(sub_pen)
    p_inner = QPainterPath()
    if r_inner > 0.5:
        p_inner.addRoundedRect(QRectF(m_inner, m_inner, float(w) - m_inner * 2.0, float(h) - m_inner * 2.0), r_inner, r_inner)
    else:
        p_inner.addRect(QRectF(m_inner, m_inner, float(w) - m_inner * 2.0, float(h) - m_inner * 2.0))
    p.drawPath(p_inner)

    pen = sys._create_styled_pen(w, h, thick, alpha)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    for b_path in sys._create_curved_corner_brackets(w, h, sys.margin, sys.radius, arm):
        p.drawPath(b_path)

    accent_sz = max(4.0, thick + 2.0)
    half_acc = accent_sz * 0.5
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(sys._create_brush_gradient(w, h, alpha))

    x_l = float(sys.margin) + half_w
    y_t = float(sys.margin) + half_w
    x_r = float(w) - x_l
    y_b = float(h) - y_t
    r_c = max(0.0, float(sys.radius) - half_w) if sys.radius > 0.5 else 0.0
    diag_off = r_c * 0.2929 if r_c > 0.5 else 0.0

    corners = [
        QPointF(x_l + diag_off, y_t + diag_off),
        QPointF(x_r - diag_off, y_t + diag_off),
        QPointF(x_r - diag_off, y_b - diag_off),
        QPointF(x_l + diag_off, y_b - diag_off)
    ]
    for pt in corners:
        p.drawRect(QRectF(pt.x() - half_acc, pt.y() - half_acc, accent_sz, accent_sz))

    cx, cy = float(w) * 0.5, float(h) * 0.5
    top_y = float(sys.margin) + half_w
    bot_y = float(h) - top_y
    p.setPen(sys._create_styled_pen(w, h, 1.0, alpha))
    p.drawLine(QPointF(cx - 24, top_y), QPointF(cx + 24, top_y))
    p.drawLine(QPointF(cx, top_y - 3), QPointF(cx, top_y + 3))
    p.drawLine(QPointF(cx - 24, bot_y), QPointF(cx + 24, bot_y))
    p.drawLine(QPointF(cx, bot_y - 3), QPointF(cx, bot_y + 3))


@register_border("액자")
def draw_inset_frame(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(max(6, sys.margin))
    r = float(max(0, sys.radius))
    path = sys._get_base_rounded_path(w, h)

    shadow_c = QColor(0, 0, 0, max(0, min(255, int(alpha * 0.55))))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(shadow_c, float(sys.width + 3), Qt.PenStyle.SolidLine))
    p.save()
    p.translate(0, 2.5)
    p.drawPath(path)
    p.restore()

    pen = sys._create_styled_pen(w, h, float(sys.width), alpha)
    p.setPen(pen)
    p.drawPath(path)

    hi_pen = sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.45))))
    p.setPen(hi_pen)
    inner_r = max(0.0, r - 2.0)
    p_hi = QPainterPath()
    if inner_r > 0.5:
        p_hi.addRoundedRect(QRectF(m + 2.0, m + 2.0, w - (m + 2.0) * 2, h - (m + 2.0) * 2), inner_r, inner_r)
    else:
        p_hi.addRect(QRectF(m + 2.0, m + 2.0, w - (m + 2.0) * 2, h - (m + 2.0) * 2))
    p.drawPath(p_hi)


@register_border("모따기")
def draw_studio_chamfer(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(sys.margin) + float(sys.width) * 0.5
    c = max(8.0, float(sys.radius) if sys.radius > 0 else 16.0)

    poly = QPolygonF([
        QPointF(m + c, m), QPointF(w - m - c, m),
        QPointF(w - m, m + c), QPointF(w - m, h - m - c),
        QPointF(w - m - c, h - m), QPointF(m + c, h - m),
        QPointF(m, h - m - c), QPointF(m, m + c),
    ])

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(sys._create_styled_pen(w, h, float(sys.width), alpha))
    p.drawPolygon(poly)

    m2 = m + 4.0
    c2 = max(4.0, c - 3.0)
    poly_inner = QPolygonF([
        QPointF(m2 + c2, m2), QPointF(w - m2 - c2, m2),
        QPointF(w - m2, m2 + c2), QPointF(w - m2, h - m2 - c2),
        QPointF(w - m2 - c2, h - m2), QPointF(m2 + c2, h - m2),
        QPointF(m2, h - m2 - c2), QPointF(m2, m2 + c2),
    ])
    p.setPen(sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.35)))))
    p.drawPolygon(poly_inner)


@register_border("도트")
def draw_dot_matrix(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    half_w = float(sys.width) * 0.5
    m = float(sys.margin) + half_w + 2.0
    r_c = max(0.0, float(sys.radius) - half_w - 2.0) if sys.radius > 0.5 else 0.0
    dot_sz = max(2.0, float(sys.width) * 0.8)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(sys._create_brush_gradient(w, h, alpha))

    step = 18.0
    if r_c <= 1.0:
        avail_w = max(10.0, float(w) - m * 2.0)
        avail_h = max(10.0, float(h) - m * 2.0)
        count_x = max(2, int(round(avail_w / step)))
        count_y = max(2, int(round(avail_h / step)))
        step_x = avail_w / count_x
        step_y = avail_h / count_y

        for i in range(count_x + 1):
            x = m + i * step_x
            p.drawRect(QRectF(x - dot_sz * 0.5, m - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(x - dot_sz * 0.5, float(h) - m - dot_sz * 0.5, dot_sz, dot_sz))
        for j in range(1, count_y):
            y = m + j * step_y
            p.drawRect(QRectF(m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
            p.drawRect(QRectF(float(w) - m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
        return

    straight_w = max(0.0, (float(w) - m * 2.0) - r_c * 2.0)
    straight_h = max(0.0, (float(h) - m * 2.0) - r_c * 2.0)
    count_sx = max(1, int(round(straight_w / step)))
    count_sy = max(1, int(round(straight_h / step)))
    step_sx = straight_w / count_sx if count_sx > 0 else 0
    step_sy = straight_h / count_sy if count_sy > 0 else 0

    for i in range(count_sx + 1):
        x = m + r_c + i * step_sx
        p.drawRect(QRectF(x - dot_sz * 0.5, m - dot_sz * 0.5, dot_sz, dot_sz))
        p.drawRect(QRectF(x - dot_sz * 0.5, float(h) - m - dot_sz * 0.5, dot_sz, dot_sz))

    for j in range(count_sy + 1):
        y = m + r_c + j * step_sy
        p.drawRect(QRectF(m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))
        p.drawRect(QRectF(float(w) - m - dot_sz * 0.5, y - dot_sz * 0.5, dot_sz, dot_sz))

    arc_len = (math.pi * 0.5) * r_c
    arc_dots = max(1, int(round(arc_len / step)))
    for k in range(1, arc_dots):
        theta = (math.pi * 0.5) * (k / float(arc_dots))
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        p.drawRect(QRectF((m + r_c - r_c * sin_t) - dot_sz * 0.5, (m + r_c - r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
        p.drawRect(QRectF((float(w) - m - r_c + r_c * sin_t) - dot_sz * 0.5, (m + r_c - r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
        p.drawRect(QRectF((float(w) - m - r_c + r_c * sin_t) - dot_sz * 0.5, (float(h) - m - r_c + r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))
        p.drawRect(QRectF((m + r_c - r_c * sin_t) - dot_sz * 0.5, (float(h) - m - r_c + r_c * cos_t) - dot_sz * 0.5, dot_sz, dot_sz))


@register_border("분할선")
def draw_cyber_groove(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(sys.margin) + 2.0
    r = float(sys.radius)
    pen = sys._create_styled_pen(w, h, float(sys.width), alpha)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    gap = 40.0
    cx, cy = w * 0.5, h * 0.5

    p_tl = QPainterPath()
    p_tl.moveTo(cx - gap, m)
    if r > 0.5:
        p_tl.lineTo(m + r, m)
        p_tl.arcTo(m, m, 2 * r, 2 * r, 90, 90)
    else:
        p_tl.lineTo(m, m)
    p_tl.lineTo(m, cy - gap)
    p.drawPath(p_tl)

    p_tr = QPainterPath()
    p_tr.moveTo(cx + gap, m)
    if r > 0.5:
        p_tr.lineTo(w - m - r, m)
        p_tr.arcTo(w - m - 2 * r, m, 2 * r, 2 * r, 90, -90)
    else:
        p_tr.lineTo(w - m, m)
    p_tr.lineTo(w - m, cy - gap)
    p.drawPath(p_tr)

    p_br = QPainterPath()
    p_br.moveTo(w - m, cy + gap)
    if r > 0.5:
        p_br.lineTo(w - m, h - m - r)
        p_br.arcTo(w - m - 2 * r, h - m - 2 * r, 2 * r, 2 * r, 0, -90)
    else:
        p_br.lineTo(w - m, h - m)
    p_br.lineTo(cx + gap, h - m)
    p.drawPath(p_br)

    p_bl = QPainterPath()
    p_bl.moveTo(cx - gap, h - m)
    if r > 0.5:
        p_bl.lineTo(m + r, h - m)
        p_bl.arcTo(m, h - m - 2 * r, 2 * r, 2 * r, 270, -90)
    else:
        p_bl.lineTo(m, h - m)
    p_bl.lineTo(m, cy + gap)
    p.drawPath(p_bl)

    sub_pen = sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.4))))
    p.setPen(sub_pen)
    p.drawLine(QPointF(cx - gap * 0.6, m), QPointF(cx + gap * 0.6, m))
    p.drawLine(QPointF(cx - gap * 0.6, h - m), QPointF(cx + gap * 0.6, h - m))
    p.drawLine(QPointF(m, cy - gap * 0.6), QPointF(m, cy + gap * 0.6))
    p.drawLine(QPointF(w - m, cy - gap * 0.6), QPointF(w - m, cy + gap * 0.6))


@register_border("비네트")
def draw_optical_vignette(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(sys.margin)
    path = sys._get_base_rounded_path(w, h)

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(sys._create_styled_pen(w, h, float(sys.width), alpha))
    p.drawPath(path)

    p.save()
    p.setClipPath(path)
    inner_rect = QRectF(m + 4.0, m + 4.0, w - (m + 4.0) * 2, h - (m + 4.0) * 2)
    p.fillRect(inner_rect, sys._scanline_brush)
    p.restore()


@register_border("상하 바")
def draw_cinematic_rim(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    m = float(sys.margin)
    bar_h = max(3.0, float(sys.width) * 1.5)

    p.save()
    p.setClipPath(sys._get_base_rounded_path(w, h))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(sys._create_brush_gradient(w, h, alpha))
    p.drawRect(QRectF(m, m, w - m * 2, bar_h))
    p.drawRect(QRectF(m, h - m - bar_h, w - m * 2, bar_h))
    p.restore()

    sub_pen = sys._create_styled_pen(w, h, 1.0, max(0, min(255, int(alpha * 0.25))))
    p.setPen(sub_pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(m, m + bar_h), QPointF(m, h - m - bar_h))
    p.drawLine(QPointF(w - m, m + bar_h), QPointF(w - m, h - m - bar_h))


@register_border("십자")
def draw_corner_cross(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    thick = float(sys.width)
    half_w = thick * 0.5
    x_l = float(sys.margin) + half_w
    y_t = float(sys.margin) + half_w
    x_r = float(w) - x_l
    y_b = float(h) - y_t
    r_c = max(0.0, float(sys.radius) - half_w) if sys.radius > 0.5 else 0.0

    p.setPen(sys._create_styled_pen(w, h, thick, alpha))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(sys._get_base_rounded_path(w, h))

    cs = 14.0
    diag_off = r_c * 0.2929 if r_c > 0.5 else 0.0
    corners = [
        (x_l + diag_off, y_t + diag_off),
        (x_r - diag_off, y_t + diag_off),
        (x_r - diag_off, y_b - diag_off),
        (x_l + diag_off, y_b - diag_off)
    ]
    p.setPen(sys._create_styled_pen(w, h, 1.5, alpha))
    for cx, cy in corners:
        p.drawLine(QPointF(cx - cs * 0.5, cy), QPointF(cx + cs * 0.5, cy))
        p.drawLine(QPointF(cx, cy - cs * 0.5), QPointF(cx, cy + cs * 0.5))


@register_border("강조 네온")
def draw_gamer_neon(sys: ScreenBorderSystem, p: QPainter, w: int, h: int, alpha: int):
    path = sys._get_base_rounded_path(w, h)
    p.setBrush(Qt.BrushStyle.NoBrush)

    steps = 5
    base_w = float(sys.width)
    for i in range(steps, 0, -1):
        ratio = i / float(steps)
        gw = base_w + (base_w * 2.2) * ratio
        ga = max(0, min(255, int(alpha * 0.28 * math.exp(-2.2 * (ratio ** 2)))))
        if ga > 0:
            p.setPen(sys._create_styled_pen(w, h, gw, ga))
            p.drawPath(path)

    p.setPen(sys._create_styled_pen(w, h, base_w, alpha))
    p.drawPath(path)

    corner_len = min(40.0, max(14.0, min(w, h) * 0.05))
    accent_pen = QPen(QColor(255, 255, 255, alpha), float(sys.width + 1.2))
    accent_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    accent_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(accent_pen)

    for b_path in sys._create_curved_corner_brackets(w, h, sys.margin, sys.radius, corner_len):
        p.drawPath(b_path)

    half_w = float(sys.width) * 0.5
    x_l = float(sys.margin) + half_w
    y_t = float(sys.margin) + half_w
    x_r = float(w) - x_l
    y_b = float(h) - y_t
    max_r = min((x_r - x_l) / 2.0, (y_b - y_t) / 2.0)
    r_c = max(0.0, min(float(sys.radius) - half_w, max_r)) if sys.radius > 0.5 else 0.0

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, min(255, int(alpha * 1.1))))
    pip_sz = float(sys.width + 2.0)
    half_pip = pip_sz * 0.5

    pips = [
        QPointF(x_l + r_c + corner_len, y_t), QPointF(x_l, y_t + r_c + corner_len),
        QPointF(x_r - r_c - corner_len, y_t), QPointF(x_r, y_t + r_c + corner_len),
        QPointF(x_r - r_c - corner_len, y_b), QPointF(x_r, y_b - r_c - corner_len),
        QPointF(x_l + r_c + corner_len, y_b), QPointF(x_l, y_b - r_c - corner_len)
    ]
    for pt in pips:
        p.drawEllipse(QRectF(pt.x() - half_pip, pt.y() - half_pip, pip_sz, pip_sz))