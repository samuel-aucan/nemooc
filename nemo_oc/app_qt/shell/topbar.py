"""Encabezado superior para cada pagina de la shell Qt."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class TopBar(QFrame):
    """Header contextual de la pagina actual."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)

        self.eyebrow = QLabel("Desktop Qt Preview")
        self.eyebrow.setObjectName("SectionEyebrow")
        self.title = QLabel("NemoOC")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("Shell principal de la migracion")
        self.subtitle.setObjectName("PageSubtitle")
        self.subtitle.setWordWrap(True)

        left.addWidget(self.eyebrow)
        left.addWidget(self.title)
        left.addWidget(self.subtitle)

        layout.addLayout(left, 1)

        right = QHBoxLayout()
        right.setSpacing(6)

        self.chip_phase = QLabel("Fase 2 cerrada")
        self.chip_phase.setObjectName("Chip")
        self.chip_mode = QLabel("Fase 9 pendiente")
        self.chip_mode.setObjectName("Chip")
        self.chip_guard = QLabel("Web intacta")
        self.chip_guard.setObjectName("Chip")

        right.addWidget(self.chip_phase)
        right.addWidget(self.chip_mode)
        right.addWidget(self.chip_guard)

        layout.addLayout(right)

    def set_page(self, title: str, subtitle: str, eyebrow: str = "Desktop Qt Preview") -> None:
        self.eyebrow.setText(eyebrow)
        self.title.setText(title)
        self.subtitle.setText(subtitle)

    def set_status_chips(self, phase_text: str, mode_text: str, guard_text: str = "Web intacta") -> None:
        self.chip_phase.setText(phase_text)
        self.chip_mode.setText(mode_text)
        self.chip_guard.setText(guard_text)
