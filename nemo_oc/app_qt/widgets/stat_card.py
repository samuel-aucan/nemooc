"""Tarjeta de metrica simple para la shell Qt."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    """Card compacta para mostrar una metrica principal."""

    def __init__(self, title: str, value: str, subtitle: str, accent: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PageCard")
        if accent:
            self.setStyleSheet(
                f"QFrame#PageCard {{ border-left: 4px solid {accent}; }}"
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("SectionEyebrow")

        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("MetricCaption")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(subtitle_label)
