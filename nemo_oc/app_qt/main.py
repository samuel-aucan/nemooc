"""Punto de entrada de la nueva interfaz Qt."""

from __future__ import annotations

import os
import sys


_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services import user_admin_service
from app_qt.auth.login_dialog import run_login_dialog
from app_qt.bootstrap import SessionUser, bootstrap_qt_context
from app_qt.shell.main_window import MainWindow
from app_qt.theme.styles import build_app_stylesheet


def build_application() -> tuple[QApplication, MainWindow | None]:
    """Construye la app Qt lista para ejecutar."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("NemoOC")
    app.setOrganizationName("Nemo Chile")
    app.setStyle("Fusion")
    app.setStyleSheet(build_app_stylesheet())
    app.setQuitOnLastWindowClosed(True)

    # Respetar alto DPI y evitar comportamiento heredado del sistema cuando sea posible.
    app.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar, True)

    context = bootstrap_qt_context()
    skip_login = os.getenv("NEMOOC_QT_SKIP_LOGIN") == "1"
    if not skip_login:
        if not run_login_dialog(context):
            return app, None
    else:
        preview_user = user_admin_service.get_preview_autologin_user()
        if preview_user:
            display_name = preview_user.get("nombre_completo") or preview_user.get("username") or "Usuario"
            context.current_user = SessionUser(
                user_id=int(preview_user["id"]),
                username=str(preview_user["username"]),
                display_name=str(display_name),
                role=str(preview_user.get("rol") or "operador"),
            )
    window = MainWindow(context)
    return app, window


def main() -> int:
    app, window = build_application()
    if window is None:
        return 0
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
