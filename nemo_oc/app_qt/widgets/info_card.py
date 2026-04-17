"""Tarjeta de informacion para textos y listas cortas."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class InfoCard(QFrame):
    """Tarjeta textual simple."""

    def __init__(self, title: str, body: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("PageCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")

        body_label = QLabel(body)
        body_label.setObjectName("CardBody")
        body_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(body_label)
        layout.addStretch(1)
