"""Sidebar principal de la shell Qt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from app.config import get_assets_dir
from app.repositories.oc_repository import get_stats
from app_qt.bootstrap import QtAppContext
from app_qt.theme.tokens import TOKENS


@dataclass(frozen=True)
class NavItem:
    key: str
    title: str
    description: str


class Sidebar(QFrame):
    """Barra lateral principal de navegacion."""

    page_requested = Signal(str)
    logout_requested = Signal()

    def __init__(self, context: QtAppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self.setObjectName("Sidebar")
        self.setFixedWidth(TOKENS["sidebar_width"])
        self._buttons: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        brand = QFrame()
        brand.setObjectName("SidebarSection")
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(14, 14, 14, 14)
        brand_layout.setSpacing(4)

        logo = QLabel()
        logo_path = get_assets_dir() / "mono.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            logo.setPixmap(pixmap.scaledToWidth(96, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignLeft)

        title = QLabel(self.context.app_name)
        title.setObjectName("BrandTitle")
        subtitle = QLabel("Migracion desktop a Qt en paralelo")
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)

        brand_layout.addWidget(logo)
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand)

        nav_wrap = QFrame()
        nav_wrap.setObjectName("SidebarSection")
        nav_layout = QVBoxLayout(nav_wrap)
        nav_layout.setContentsMargins(10, 10, 10, 10)
        nav_layout.setSpacing(6)

        nav_items = [
            NavItem("oc_list", "Ordenes de compra", "Bandeja y detalle"),
            NavItem("import", "Importaciones", "MP y privadas"),
            NavItem("stats", "Estadisticas", "Cobertura y revision"),
            NavItem("holdings", "Holdings", "Clientes y catalogos"),
            NavItem("users", "Usuarios", "Accesos y seguridad"),
            NavItem("config", "Configuracion", "Credenciales y ajustes"),
        ]

        for item in nav_items:
            btn = QPushButton(item.title)
            btn.setObjectName("NavButton")
            btn.setProperty("active", False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(TOKENS["nav_height"])
            btn.setToolTip(item.description)
            btn.clicked.connect(lambda _checked=False, key=item.key: self.page_requested.emit(key))
            nav_layout.addWidget(btn)
            self._buttons[item.key] = btn

        layout.addWidget(nav_wrap, 1)

        session = QFrame()
        session.setObjectName("SidebarSection")
        session_layout = QVBoxLayout(session)
        session_layout.setContentsMargins(12, 12, 12, 12)
        session_layout.setSpacing(4)

        session_eyebrow = QLabel("Sesion activa")
        session_eyebrow.setObjectName("SectionEyebrow")
        self._session_name = QLabel("-")
        self._session_name.setObjectName("BrandHero")
        self._session_meta = QLabel("-")
        self._session_meta.setObjectName("BrandSubtitle")
        self._session_meta.setWordWrap(True)
        self._btn_logout = QPushButton("Cerrar sesion")
        self._btn_logout.clicked.connect(self.logout_requested.emit)

        session_layout.addWidget(session_eyebrow)
        session_layout.addWidget(self._session_name)
        session_layout.addWidget(self._session_meta)
        session_layout.addWidget(self._btn_logout)
        layout.addWidget(session)

        status = QFrame()
        status.setObjectName("StatusCard")
        status_layout = QVBoxLayout(status)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(4)

        eyebrow = QLabel("Estado del sistema")
        eyebrow.setObjectName("SectionEyebrow")
        self._status_copy = QLabel()
        self._status_copy.setObjectName("BrandSubtitle")
        self._status_copy.setWordWrap(True)

        status_layout.addWidget(eyebrow)
        status_layout.addWidget(self._status_copy)
        layout.addWidget(status)

        footer = QLabel(f"Baseline {self.context.baseline_git}\nDesarrollado por Samuel Belmar")
        footer.setObjectName("BrandSubtitle")
        footer.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(footer)

        self.refresh_session()
        self.refresh_status()

    def _format_last_sync(self) -> str:
        last = self.context.config.last_sync
        if not last:
            return "sin registro"
        try:
            dt = datetime.fromisoformat(last)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return "sin registro"

    def _is_admin(self) -> bool:
        user = self.context.current_user
        return bool(user and user.is_admin)

    def refresh_session(self) -> None:
        user = self.context.current_user
        if user is None:
            self._session_name.setText("Sin sesion")
            self._session_meta.setText("La preview requiere acceso local antes de operar.")
            self._btn_logout.setVisible(False)
        else:
            self._session_name.setText(user.display_name)
            role_label = "Administrador" if user.is_admin else "Operador"
            self._session_meta.setText(f"{user.username} | {role_label}")
            self._btn_logout.setVisible(True)
        users_button = self._buttons.get("users")
        if users_button is not None:
            users_button.setVisible(self._is_admin())

    def refresh_status(self) -> None:
        stats = get_stats()
        last_sync = self._format_last_sync()
        self._status_copy.setText(
            f"Preview Qt preparada.\n"
            f"OCs locales: {stats['total']} | Sin homologar: {stats['sin_homolog']}\n"
            f"Ultima sync: {last_sync}"
        )

    def set_active(self, key: str) -> None:
        for item_key, button in self._buttons.items():
            button.setProperty("active", item_key == key)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()
