"""Status bar ligera para la shell Qt."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar


class AppStatusBar(QStatusBar):
    """Barra de estado simple para la preview Qt."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)
        self._left = QLabel("Listo")
        self._right = QLabel("Fase 0 completandose")
        self.addWidget(self._left)
        self.addPermanentWidget(self._right)

    def set_left_text(self, text: str) -> None:
        self._left.setText(text)

    def set_right_text(self, text: str) -> None:
        self._right.setText(text)

