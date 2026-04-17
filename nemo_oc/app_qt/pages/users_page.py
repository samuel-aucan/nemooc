"""Modulo de usuarios para la shell Qt."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services import user_admin_service

ROLE_OPTIONS = [("operador", "Operador"), ("admin", "Administrador")]


class UsersPage(QWidget):
    page_title = "Usuarios"
    page_subtitle = "Accesos, roles y reinicio de acceso con token temporal desde la nueva desktop."
    page_eyebrow = "Seguridad"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._users: list[dict] = []
        self._selected_user_id: int | None = None
        self._build()
        self.refresh()

    def on_show(self) -> None:
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_create_card())
        root.addWidget(self._build_management_card(), 1)

    def _build_create_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Crear usuario")
        title.setObjectName("CardTitle")
        subtitle = QLabel(
            "Solo los usuarios creados aquí podrán entrar a NemoOC. No existe registro público ni autoinscripción."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.create_username = QLineEdit()
        self.create_username.setPlaceholderText("mlopez")
        self.create_name = QLineEdit()
        self.create_name.setPlaceholderText("Manuel Lopez")
        self.create_password = QLineEdit()
        self.create_password.setPlaceholderText("Minimo 8 caracteres")
        self.create_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_password_confirm = QLineEdit()
        self.create_password_confirm.setPlaceholderText("Repite la contraseña")
        self.create_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_role = QComboBox()
        for value, label in ROLE_OPTIONS:
            self.create_role.addItem(label, value)

        self.btn_create = QPushButton("Crear usuario")
        self.btn_create.setObjectName("PrimaryButton")
        self.btn_create.clicked.connect(self._create_user)

        grid.addWidget(self._labeled_field("Usuario", self.create_username), 0, 0)
        grid.addWidget(self._labeled_field("Nombre completo", self.create_name), 0, 1)
        grid.addWidget(self._labeled_field("Rol", self.create_role), 0, 2)
        grid.addWidget(self._labeled_field("Contraseña", self.create_password), 1, 0)
        grid.addWidget(self._labeled_field("Confirmar contraseña", self.create_password_confirm), 1, 1)
        grid.addWidget(self.btn_create, 1, 2, 1, 1, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(grid)

        self.lbl_create_message = QLabel("")
        self.lbl_create_message.setObjectName("PageSubtitle")
        self.lbl_create_message.setVisible(False)
        layout.addWidget(self.lbl_create_message)
        return card

    def _build_management_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Usuarios existentes")
        title.setObjectName("CardTitle")
        self.lbl_users_meta = QLabel("Sin datos")
        self.lbl_users_meta.setObjectName("PageSubtitle")
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self.refresh)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.lbl_users_meta)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.splitter.addWidget(self._build_users_table_card())
        self.splitter.addWidget(self._build_editor_scroll())
        self.splitter.setSizes([460, 520])
        layout.addWidget(self.splitter, 1)
        return card

    def _build_users_table_card(self) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("PageCard")
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.users_table = QTableWidget(0, 5)
        self.users_table.setHorizontalHeaderLabels(["Usuario", "Nombre", "Rol", "Estado", "Ultimo acceso"])
        self._style_table(self.users_table)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.users_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.users_table.itemSelectionChanged.connect(self._handle_table_selection)
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.users_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.users_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.users_table, 1)
        return wrap

    def _build_editor_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Editor del usuario seleccionado")
        title.setObjectName("CardTitle")
        self.lbl_selected_user = QLabel("Selecciona un usuario")
        self.lbl_selected_user.setObjectName("PageSubtitle")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.lbl_selected_user)
        layout.addLayout(header)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)

        self.edit_username = QLineEdit()
        self.edit_username.setReadOnly(True)
        self.edit_name = QLineEdit()
        self.edit_role = QComboBox()
        for value, label in ROLE_OPTIONS:
            self.edit_role.addItem(label, value)
        self.chk_active = QCheckBox("Usuario activo")
        self.lbl_last_login = QLabel("-")
        self.lbl_last_login.setObjectName("CardBody")
        self.lbl_reset_state = QLabel("-")
        self.lbl_reset_state.setObjectName("CardBody")

        form.addWidget(self._labeled_field("Usuario", self.edit_username), 0, 0)
        form.addWidget(self._labeled_field("Nombre completo", self.edit_name), 0, 1)
        form.addWidget(self._labeled_field("Rol", self.edit_role), 1, 0)
        form.addWidget(self._labeled_field("Ultimo acceso", self.lbl_last_login), 1, 1)
        form.addWidget(self.chk_active, 2, 0)
        form.addWidget(self._labeled_field("Estado de acceso", self.lbl_reset_state), 2, 1)
        layout.addLayout(form)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        self.btn_save_user = QPushButton("Guardar cambios")
        self.btn_save_user.setObjectName("PrimaryButton")
        self.btn_save_user.clicked.connect(self._save_selected_user)
        self.btn_reset_access = QPushButton("Reiniciar acceso")
        self.btn_reset_access.clicked.connect(self._reset_selected_access)
        action_row.addWidget(self.btn_save_user)
        action_row.addWidget(self.btn_reset_access)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        password_card = QFrame()
        password_card.setObjectName("PageCard")
        password_layout = QGridLayout(password_card)
        password_layout.setContentsMargins(10, 10, 10, 10)
        password_layout.setHorizontalSpacing(8)
        password_layout.setVerticalSpacing(6)
        password_title = QLabel("Resetear contraseña directa")
        password_title.setObjectName("CardTitle")
        self.reset_password = QLineEdit()
        self.reset_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_password.setPlaceholderText("Nueva contraseña")
        self.reset_password_confirm = QLineEdit()
        self.reset_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.reset_password_confirm.setPlaceholderText("Confirmar nueva contraseña")
        self.btn_set_password = QPushButton("Guardar contraseña")
        self.btn_set_password.clicked.connect(self._set_password_for_selected)
        password_layout.addWidget(password_title, 0, 0, 1, 2)
        password_layout.addWidget(self._labeled_field("Nueva contraseña", self.reset_password), 1, 0)
        password_layout.addWidget(self._labeled_field("Confirmar", self.reset_password_confirm), 1, 1)
        password_layout.addWidget(self.btn_set_password, 2, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(password_card)

        token_card = QFrame()
        token_card.setObjectName("PageCard")
        token_layout = QVBoxLayout(token_card)
        token_layout.setContentsMargins(10, 10, 10, 10)
        token_layout.setSpacing(6)
        token_title = QLabel("Token temporal de activacion")
        token_title.setObjectName("CardTitle")
        self.txt_token = QTextEdit()
        self.txt_token.setReadOnly(True)
        self.txt_token.setFixedHeight(84)
        self.txt_token.setPlaceholderText("Cuando reinicies el acceso de un usuario, el token aparecerá aquí una sola vez.")
        token_action_row = QHBoxLayout()
        token_action_row.setContentsMargins(0, 0, 0, 0)
        token_action_row.setSpacing(6)
        self.btn_copy_token = QPushButton("Copiar token")
        self.btn_copy_token.clicked.connect(self._copy_token)
        token_action_row.addWidget(self.btn_copy_token)
        token_action_row.addStretch(1)
        token_layout.addWidget(token_title)
        token_layout.addWidget(self.txt_token)
        token_layout.addLayout(token_action_row)
        layout.addWidget(token_card)

        self.lbl_editor_message = QLabel("")
        self.lbl_editor_message.setObjectName("PageSubtitle")
        self.lbl_editor_message.setVisible(False)
        layout.addWidget(self.lbl_editor_message)

        layout.addStretch(1)
        self._set_editor_enabled(False)
        return card

    def _build_editor_scroll(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._build_editor_card())
        return scroll

    def refresh(self) -> None:
        previous = self._selected_user_id
        self._users = user_admin_service.list_users()
        total = len(self._users)
        active = sum(1 for user in self._users if user["activo"])
        admins = sum(1 for user in self._users if user["activo"] and user["rol"] == "admin")
        self.lbl_users_meta.setText(f"{total} usuario(s) | {active} activo(s) | {admins} admin(s)")
        self._populate_table(previous)

    def _populate_table(self, preferred_user_id: int | None = None) -> None:
        self.users_table.setRowCount(len(self._users))
        selected_row = -1
        for row_idx, user in enumerate(self._users):
            if preferred_user_id is not None and user["id"] == preferred_user_id:
                selected_row = row_idx
            values = [
                user["username"],
                user["nombre_completo"] or "-",
                "Administrador" if user["rol"] == "admin" else "Operador",
                "Activo" if user["activo"] else "Desactivado",
                self._fmt_datetime(user["last_login_at"]) if user["last_login_at"] else "Sin ingresos",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, user["id"])
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if col_idx == 3:
                    if user["activo"]:
                        item.setForeground(Qt.GlobalColor.green)
                    else:
                        item.setForeground(Qt.GlobalColor.red)
                self.users_table.setItem(row_idx, col_idx, item)

        if self._users:
            if selected_row < 0:
                selected_row = 0
            self.users_table.selectRow(selected_row)
            self._load_selected_user(self._users[selected_row]["id"])
        else:
            self._selected_user_id = None
            self._set_editor_enabled(False)
            self.lbl_selected_user.setText("Sin usuarios")

    def _handle_table_selection(self) -> None:
        row = self.users_table.currentRow()
        if row < 0 or row >= len(self._users):
            return
        user_id = self._users[row]["id"]
        self._load_selected_user(user_id)

    def _load_selected_user(self, user_id: int) -> None:
        user = next((item for item in self._users if item["id"] == user_id), None)
        if not user:
            self._set_editor_enabled(False)
            return

        self._selected_user_id = user_id
        self._set_editor_enabled(True)
        self.edit_username.setText(user["username"])
        self.edit_name.setText(user["nombre_completo"] or "")
        self._set_combo_value(self.edit_role, user["rol"])
        self.chk_active.setChecked(bool(user["activo"]))
        self.lbl_last_login.setText(self._fmt_datetime(user["last_login_at"]) if user["last_login_at"] else "Sin ingresos")
        self.lbl_reset_state.setText("Debe reactivar acceso" if user["must_reset_password"] else "Acceso normal")
        self.lbl_selected_user.setText(user["username"])
        self._set_message(self.lbl_editor_message, "")
        self.txt_token.clear()
        self.reset_password.clear()
        self.reset_password_confirm.clear()

    def _create_user(self) -> None:
        try:
            user_admin_service.create_user(
                self.create_username.text(),
                self.create_password.text(),
                self.create_password_confirm.text(),
                self.create_name.text(),
                self.create_role.currentData(),
            )
        except Exception as exc:
            self._set_message(self.lbl_create_message, str(exc), error=True)
            return

        self.create_username.clear()
        self.create_name.clear()
        self.create_password.clear()
        self.create_password_confirm.clear()
        self.create_role.setCurrentIndex(0)
        self._set_message(self.lbl_create_message, "Usuario creado correctamente.")
        self.refresh()

    def _save_selected_user(self) -> None:
        user_id = self._selected_user_id
        if not user_id:
            return
        try:
            updated = user_admin_service.update_user(
                user_id,
                self.edit_name.text(),
                self.edit_role.currentData(),
                self.chk_active.isChecked(),
            )
        except Exception as exc:
            self._set_message(self.lbl_editor_message, str(exc), error=True)
            return

        self._set_message(self.lbl_editor_message, "Usuario actualizado.")
        self.refresh()
        self._load_selected_user(updated["id"])

    def _set_password_for_selected(self) -> None:
        user_id = self._selected_user_id
        if not user_id:
            return
        try:
            user_admin_service.set_user_password(
                user_id,
                self.reset_password.text(),
                self.reset_password_confirm.text(),
            )
        except Exception as exc:
            self._set_message(self.lbl_editor_message, str(exc), error=True)
            return

        self.reset_password.clear()
        self.reset_password_confirm.clear()
        self._set_message(self.lbl_editor_message, "Contraseña actualizada.")
        self.refresh()

    def _reset_selected_access(self) -> None:
        user_id = self._selected_user_id
        if not user_id:
            return
        try:
            token = user_admin_service.initiate_access_reset(user_id)
        except Exception as exc:
            self._set_message(self.lbl_editor_message, str(exc), error=True)
            return

        self.txt_token.setPlainText(
            f"Token: {token['reset_token']}\nVence: {self._fmt_datetime(token['expires_at'])}\n\n"
            "Entrega este token de forma segura. El usuario lo usará en la activación de acceso."
        )
        self._set_message(self.lbl_editor_message, "Acceso reiniciado. El token temporal se muestra una sola vez aquí.")
        self.refresh()

    def _copy_token(self) -> None:
        text = self.txt_token.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Usuarios", "No hay un token temporal visible para copiar.")
            return
        QGuiApplication.clipboard().setText(text)
        self._set_message(self.lbl_editor_message, "Token copiado al portapapeles.")

    def _set_editor_enabled(self, enabled: bool) -> None:
        for widget in [
            self.edit_username,
            self.edit_name,
            self.edit_role,
            self.chk_active,
            self.btn_save_user,
            self.btn_reset_access,
            self.reset_password,
            self.reset_password_confirm,
            self.btn_set_password,
            self.btn_copy_token,
            self.txt_token,
        ]:
            widget.setEnabled(enabled)

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                return

    @staticmethod
    def _set_message(label: QLabel, text: str, error: bool = False) -> None:
        if not text:
            label.clear()
            label.setVisible(False)
            label.setStyleSheet("")
            return
        label.setText(text)
        label.setVisible(True)
        color = "#FCA5A5" if error else "#86EFAC"
        label.setStyleSheet(f"color: {color}; font-size: 12px;")

    @staticmethod
    def _labeled_field(title: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("SectionEyebrow")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrap

    @staticmethod
    def _style_table(table: QTableWidget) -> None:
        table.setAlternatingRowColors(False)
        table.setShowGrid(True)
        table.setGridStyle(Qt.PenStyle.SolidLine)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setFixedHeight(28)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #22304A;
                border-radius: 8px;
                background-color: #0F172A;
                selection-background-color: #19304D;
                selection-color: #F8FBFF;
                gridline-color: #1D2940;
                alternate-background-color: #111C2C;
            }
            QTableWidget::item {
                padding: 3px 6px;
                border-bottom: 1px solid #182235;
            }
            QHeaderView::section {
                background-color: #162033;
                color: #B8C8DD;
                border: none;
                border-right: 1px solid #22304A;
                border-bottom: 1px solid #2A3A57;
                padding: 4px 6px;
                font-size: 10px;
                font-weight: 700;
            }
            """
        )

    @staticmethod
    def _fmt_datetime(value: str) -> str:
        if not value:
            return ""
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(value)
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return value
