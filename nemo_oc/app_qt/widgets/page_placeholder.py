"""Placeholder visual enriquecido para paginas aun no implementadas."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout

from app_qt.widgets.info_card import InfoCard


class PagePlaceholder(QFrame):
    """Tarjeta simple para indicar el estado de una pagina."""

    page_title = "Modulo"
    page_subtitle = "Pendiente de implementacion"
    page_eyebrow = "Desktop Qt Preview"

    def __init__(
        self,
        title: str,
        description: str,
        status: str,
        next_steps: str = "",
        reference: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.page_title = title
        self.page_subtitle = description
        self.page_eyebrow = "Desktop Qt Preview"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        hero = QFrame()
        hero.setObjectName("PageCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(14, 14, 14, 14)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("Desktop Qt preview")
        eyebrow.setObjectName("SectionEyebrow")

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")

        desc_label = QLabel(description)
        desc_label.setObjectName("CardBody")
        desc_label.setWordWrap(True)

        status_label = QLabel(status)
        status_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #10B5D8;")

        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title_label)
        hero_layout.addWidget(desc_label)
        hero_layout.addSpacing(6)
        hero_layout.addWidget(status_label)
        layout.addWidget(hero)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        next_steps_text = next_steps or "La implementacion detallada quedo planificada en el roadmap oficial de migracion."
        reference_text = reference or "La referencia funcional y visual sigue estando en la version web, sin tocarla."

        grid.addWidget(InfoCard("Siguiente foco", next_steps_text), 0, 0)
        grid.addWidget(InfoCard("Referencia", reference_text), 0, 1)

        grid_wrap = QFrame()
        grid_wrap.setLayout(grid)
        layout.addWidget(grid_wrap)
        layout.addStretch(1)
