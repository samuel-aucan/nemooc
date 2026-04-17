"""Delegado para pintar estados compactos tipo badge dentro de tablas Qt."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem


class BadgeDelegate(QStyledItemDelegate):
    """Dibuja un badge redondeado dentro de una celda de tabla."""

    def __init__(self, palette: dict[str, tuple[str, str]], align: Qt.AlignmentFlag | None = None, parent=None) -> None:
        super().__init__(parent)
        self._palette = {key.casefold(): value for key, value in palette.items()}
        self._align = align or (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        text = (index.data(Qt.ItemDataRole.DisplayRole) or "").strip()
        key = text.casefold()
        colors = self._palette.get(key)
        if not text or not colors:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        style = opt.widget.style() if opt.widget else None
        opt.text = ""
        if style:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        bg = QColor(colors[0])
        fg = QColor(colors[1])

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        metrics = painter.fontMetrics()
        content = metrics.elidedText(text, Qt.TextElideMode.ElideRight, max(44, opt.rect.width() - 18))
        text_width = metrics.horizontalAdvance(content)
        badge_width = min(opt.rect.width() - 8, max(42, text_width + 16))
        badge_height = min(20, max(16, opt.rect.height() - 8))

        x = opt.rect.left() + 4
        if self._align & Qt.AlignmentFlag.AlignHCenter:
            x = opt.rect.left() + (opt.rect.width() - badge_width) // 2
        elif self._align & Qt.AlignmentFlag.AlignRight:
            x = opt.rect.right() - badge_width - 4
        y = opt.rect.top() + (opt.rect.height() - badge_height) // 2

        badge_rect = QRect(QPoint(x, y), QSize(badge_width, badge_height))
        painter.setPen(QPen(bg.lighter(130), 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(badge_rect, badge_height / 2, badge_height / 2)

        painter.setPen(fg)
        painter.drawText(badge_rect, int(Qt.AlignmentFlag.AlignCenter), content)
        painter.restore()
