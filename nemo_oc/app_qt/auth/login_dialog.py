"""Dialogo de acceso local para la preview Qt."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services import user_admin_service
from app_qt.bootstrap import QtAppContext, SessionUser


class LoginDialog(QDialog):
    """Pantalla de acceso para la desktop Qt."""

    def __init__(self, context: QtAppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self._mode = "login"
        self.setWindowTitle("Acceso NemoOC")
        self.setModal(True)
        self.resize(470, 410)
        self.setMinimumSize(440, 380)
        self._build()
        self._set_mode("bootstrap" if user_admin_service.bootstrap_required() else "login")

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        shell = QFrame()
        shell.setObjectName("PageCard")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(16, 16, 16, 16)
        shell_layout.setSpacing(10)

        self.eyebrow = QLabel("Seguridad local")
        self.eyebrow.setObjectName("SectionEyebrow")
        self.title = QLabel("Acceso NemoOC")
        self.title.setObjectName("PageTitle")
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("PageSubtitle")
        self.subtitle.setWordWrap(True)

        shell_layout.addWidget(self.eyebrow)
        shell_layout.addWidget(self.title)
        shell_layout.addWidget(self.subtitle)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_login_page())
        self.stack.addWidget(self._build_bootstrap_page())
        self.stack.addWidget(self._build_reset_page())
        shell_layout.addWidget(self.stack, 1)

        self.message = QLabel("")
        self.message.setObjectName("PageSubtitle")
        self.message.setWordWrap(True)
        self.message.hide()
        shell_layout.addWidget(self.message)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        self.btn_show_login = QPushButton("Volver a login")
        self.btn_show_login.clicked.connect(lambda: self._set_mode("login"))
        self.btn_show_reset = QPushButton("Activar acceso")
        self.btn_show_reset.clicked.connect(lambda: self._set_mode("reset"))
        footer.addStretch(1)
        footer.addWidget(self.btn_show_login)
        footer.addWidget(self.btn_show_reset)
        shell_layout.addLayout(footer)

        root.addWidget(shell)

    def _build_login_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Usuario")
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Contraseña")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.returnPressed.connect(self._login)

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setObjectName("PrimaryButton")
        self.btn_login.clicked.connect(self._login)

        form.addWidget(self._field("Usuario", self.login_username), 0, 0)
        form.addWidget(self._field("Contraseña", self.login_password), 1, 0)
        form.addWidget(self.btn_login, 2, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form)
        return page

    def _build_bootstrap_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.bootstrap_name = QLineEdit()
        self.bootstrap_name.setPlaceholderText("Nombre visible")
        self.bootstrap_username = QLineEdit()
        self.bootstrap_username.setPlaceholderText("Usuario administrador")
        self.bootstrap_password = QLineEdit()
        self.bootstrap_password.setPlaceholderText("Mínimo 8 caracteres")
        self.bootstrap_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.bootstrap_password_confirm = QLineEdit()
        self.bootstrap_password_confirm.setPlaceholderText("Confirmar contraseña")
        self.bootstrap_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.bootstrap_password_confirm.returnPressed.connect(self._bootstrap_admin)

        self.btn_bootstrap = QPushButton("Crear administrador")
        self.btn_bootstrap.setObjectName("PrimaryButton")
        self.btn_bootstrap.clicked.connect(self._bootstrap_admin)

        form.addWidget(self._field("Nombre completo", self.bootstrap_name), 0, 0, 1, 2)
        form.addWidget(self._field("Usuario", self.bootstrap_username), 1, 0)
        form.addWidget(self._field("Contraseña", self.bootstrap_password), 1, 1)
        form.addWidget(self._field("Confirmar contraseña", self.bootstrap_password_confirm), 2, 0, 1, 2)
        form.addWidget(self.btn_bootstrap, 3, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form)
        return page

    def _build_reset_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.reset_username = QLineEdit()
        self.reset_username.setPlaceholderText("Usuario")
        self.reset_token = QLineEdit()
        self.reset_token.setPlaceholderText("Token temporal")
        self.reset_password = QLineEdit()
        self.reset_password.setPlaceholderText("Nueva contraseña")
        self.reset_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_password_confirm = QLineEdit()
        self.reset_password_confirm.setPlaceholderText("Confirmar nueva contraseña")
        self.reset_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_password_confirm.returnPressed.connect(self._complete_reset)

        self.btn_complete_reset = QPushButton("Activar acceso")
        self.btn_complete_reset.setObjectName("PrimaryButton")
        self.btn_complete_reset.clicked.connect(self._complete_reset)

        form.addWidget(self._field("Usuario", self.reset_username), 0, 0)
        form.addWidget(self._field("Token", self.reset_token), 0, 1)
        form.addWidget(self._field("Nueva contraseña", self.reset_password), 1, 0)
        form.addWidget(self._field("Confirmar contraseña", self.reset_password_confirm), 1, 1)
        form.addWidget(self.btn_complete_reset, 2, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form)
        return page

    def _field(self, label: str, widget: QWidget) -> QWidget:
        wrap = QFrame()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("SectionEyebrow")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return wrap

    def _set_message(self, text: str, error: bool = False) -> None:
        self.message.setText(text)
        self.message.setStyleSheet("color: #FCA5A5;" if error else "")
        self.message.setVisible(bool(text))

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._set_message("")
        if mode == "bootstrap":
            self.stack.setCurrentIndex(1)
            self.title.setText("Crear administrador inicial")
            self.subtitle.setText("Como aún no existe ningún usuario, esta desktop debe crear el primer administrador antes de abrir NemoOC.")
            self.btn_show_login.hide()
            self.btn_show_reset.hide()
            return
        if mode == "reset":
            self.stack.setCurrentIndex(2)
            self.title.setText("Activar acceso")
            self.subtitle.setText("Usa el token temporal entregado por un administrador para definir tu nueva contraseña.")
            self.btn_show_login.show()
            self.btn_show_reset.hide()
            return

        self.stack.setCurrentIndex(0)
        self.title.setText("Acceso NemoOC")
        self.subtitle.setText("Ingresa con tu usuario y contraseña local. Si tu acceso fue reiniciado, usa la activación por token.")
        self.btn_show_login.hide()
        self.btn_show_reset.show()

    def _start_session(self, user: dict) -> None:
        display_name = user.get("nombre_completo") or user.get("username") or "Usuario"
        self.context.current_user = SessionUser(
            user_id=int(user["id"]),
            username=str(user["username"]),
            display_name=str(display_name),
            role=str(user.get("rol") or "operador"),
        )
        self.accept()

    def _login(self) -> None:
        try:
            user = user_admin_service.authenticate_user(
                self.login_username.text(),
                self.login_password.text(),
            )
        except Exception as exc:
            self._set_message(str(exc), error=True)
            return
        self._start_session(user)

    def _bootstrap_admin(self) -> None:
        try:
            user_admin_service.create_user(
                self.bootstrap_username.text(),
                self.bootstrap_password.text(),
                self.bootstrap_password_confirm.text(),
                nombre_completo=self.bootstrap_name.text(),
                rol="admin",
            )
            user = user_admin_service.authenticate_user(
                self.bootstrap_username.text(),
                self.bootstrap_password.text(),
            )
        except Exception as exc:
            self._set_message(str(exc), error=True)
            return
        self._start_session(user)

    def _complete_reset(self) -> None:
        try:
            user_admin_service.complete_access_reset(
                self.reset_username.text(),
                self.reset_token.text(),
                self.reset_password.text(),
                self.reset_password_confirm.text(),
            )
            user = user_admin_service.authenticate_user(
                self.reset_username.text(),
                self.reset_password.text(),
            )
        except Exception as exc:
            self._set_message(str(exc), error=True)
            return
        self._start_session(user)


def run_login_dialog(context: QtAppContext, parent=None) -> bool:
    """Ejecuta el acceso local y deja la sesion en el contexto si fue exitoso."""
    dialog = LoginDialog(context, parent=parent)
    return dialog.exec() == int(QDialog.DialogCode.Accepted)
