"""Ventana principal de la nueva shell Qt."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from app.config import get_assets_dir
from app_qt.auth.login_dialog import run_login_dialog
from app_qt.bootstrap import QtAppContext
from app_qt.pages.config_page import ConfigPage
from app_qt.pages.holdings_page import HoldingsPage
from app_qt.pages.import_page import ImportPage
from app_qt.pages.oc_list_page import OcListPage
from app_qt.pages.stats_page import StatsPage
from app_qt.pages.users_page import UsersPage
from app_qt.shell.sidebar import Sidebar
from app_qt.shell.status_bar import AppStatusBar
from app_qt.shell.topbar import TopBar


class MainWindow(QMainWindow):
    """Shell principal de la preview Qt."""

    def __init__(self, context: QtAppContext) -> None:
        super().__init__()
        self.context = context
        self._pages: dict[str, QWidget] = {}
        self._current_key = "oc_list"
        self._build()

    def _build(self) -> None:
        self.setWindowTitle(self.context.window_title)
        self.resize(1320, 820)
        self.setMinimumSize(1040, 640)
        icon_path = get_assets_dir() / "nemo_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        root = QFrame()
        root.setObjectName("AppShell")
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(self.context)
        self.sidebar.page_requested.connect(self._show_page)
        self.sidebar.logout_requested.connect(self._handle_logout)
        root_layout.addWidget(self.sidebar, 0)

        self.content_surface = QFrame()
        self.content_surface.setObjectName("ContentSurface")
        self.content_surface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(self.content_surface)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(0)

        self.topbar = TopBar()
        self.topbar.setVisible(False)
        content_layout.addWidget(self.topbar, 0)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(self.content_surface, 1)

        self._build_pages()

        status_bar = AppStatusBar(self)
        status_bar.set_left_text("Preview Qt inicializada")
        status_bar.set_right_text("Sin tocar la web ni la UI actual")
        self.setStatusBar(status_bar)

        self._show_page(self._current_key)

    def _build_pages(self) -> None:
        self._pages = {
            "oc_list": OcListPage(),
            "import": ImportPage(self.context),
            "stats": StatsPage(),
            "holdings": HoldingsPage(self.context),
            "users": UsersPage(),
            "config": ConfigPage(self.context),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

    def _show_page(self, key: str) -> None:
        if key == "users" and not (self.context.current_user and self.context.current_user.is_admin):
            key = "oc_list"
        if key not in self._pages:
            return
        self._current_key = key
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(key)
        self.sidebar.refresh_session()
        self.sidebar.refresh_status()
        title = getattr(page, "page_title", "NemoOC")
        subtitle = getattr(page, "page_subtitle", "")
        eyebrow = getattr(page, "page_eyebrow", "Desktop Qt Preview")
        on_show = getattr(page, "on_show", None)
        if callable(on_show):
            on_show()
        self.topbar.set_page(title, subtitle, eyebrow)
        self.topbar.set_status_chips("Fase 2 cerrada", "Fase 9 pendiente", "Web intacta")
        status_bar = self.statusBar()
        if isinstance(status_bar, AppStatusBar):
            status_bar.set_left_text(f"Modulo activo: {title}")
            status_bar.set_right_text("Migracion Qt en curso")

    def _handle_logout(self) -> None:
        self.context.current_user = None
        if not run_login_dialog(self.context, self):
            self.close()
            return
        if self._current_key == "users" and not (self.context.current_user and self.context.current_user.is_admin):
            self._current_key = "oc_list"
        self._show_page(self._current_key)
