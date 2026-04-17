"""Pagina real de configuracion para la shell Qt."""

from __future__ import annotations

import os
import queue
import threading
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    AppConfig,
    get_catalogs_dir,
    get_config_dir,
    get_data_dir,
    get_default_cartera_path,
    get_default_correos_path,
    get_default_homo_path,
    get_default_licitaciones_path,
    get_default_maestra_path,
    get_default_redsalud_homo_path,
    load_config,
    save_config,
)
from app.repositories.cartera_repo import count_cartera
from app.repositories.homologacion_repo import count_homologacion
from app.services.cartera_service import get_cartera_service
from app.services.email_service import get_email_service
from app.services.homologacion_service import get_homologacion_service
from app.services.licitaciones_service import get_licitaciones_service
from app.services.maestra_service import get_maestra_service
from app.services.mp_api_service import MercadoPublicoAPI
from app.services.redsalud_homo_service import get_redsalud_homo_service
from app_qt.bootstrap import QtAppContext

TaskWorker = Callable[[], dict[str, Any]]
TaskCallback = Callable[[dict[str, Any]], None]


class ConfigPage(QWidget):
    page_title = "Configuracion"
    page_subtitle = (
        "Centraliza credenciales, sincronizacion, correo y catalogos dentro "
        "de la nueva shell Qt."
    )
    page_eyebrow = "Modulo administrativo"

    def __init__(self, context: QtAppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self._catalog_rows: dict[str, dict[str, Any]] = {}
        self._summary_labels: dict[str, QLabel] = {}
        self._action_buttons: list[QPushButton] = []
        self._queue: queue.Queue | None = None
        self._task_callback: TaskCallback | None = None
        self._busy = False

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(120)
        self.poll_timer.timeout.connect(self._poll_queue)

        self._build()
        self.on_show()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 6, 0)
        self.content_layout.setSpacing(10)

        self.content_layout.addWidget(self._build_overview_card())
        self.content_layout.addWidget(self._build_api_card())
        self.content_layout.addWidget(self._build_correo_card())
        self.content_layout.addWidget(self._build_imap_card())
        self.content_layout.addWidget(self._build_catalogs_card())
        self.content_layout.addWidget(self._build_actions_card())
        self.content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _card(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card

    def _labeled_field(self, title: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("SectionEyebrow")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrap

    def _build_overview_card(self) -> QWidget:
        card = self._card(
            "Estado de configuracion",
            "Desde aqui puedes dejar listo el entorno local: API, Gmail, correo y catalogos.",
        )
        layout = card.layout()

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)

        for idx, (key, label) in enumerate(
            [("cm", "CM"), ("sap", "SAP"), ("cartera", "Cartera"), ("redsalud", "RedSalud"), ("licit", "Licit.")]
        ):
            wrap = QFrame()
            wrap.setObjectName("PageCard")
            wrap.setStyleSheet("QFrame#PageCard { background-color: #111827; }")
            inner = QVBoxLayout(wrap)
            inner.setContentsMargins(10, 8, 10, 8)
            eyebrow = QLabel(label)
            eyebrow.setObjectName("SectionEyebrow")
            value = QLabel("0")
            value.setObjectName("MetricValue")
            value.setStyleSheet("font-size: 18px;")
            inner.addWidget(eyebrow)
            inner.addWidget(value)
            grid.addWidget(wrap, 0, idx)
            self._summary_labels[key] = value

        self.notice_label = QLabel("Sin cambios recientes.")
        self.notice_label.setWordWrap(True)
        layout.addLayout(grid)
        layout.addWidget(self.notice_label)
        self._set_notice("info", "Sin cambios recientes.")
        return card

    def _build_api_card(self) -> QWidget:
        card = self._card("Mercado Publico", "Ticket, empresa y diagnostico rapido de la API.")
        layout = card.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.entry_ticket = QLineEdit()
        self.entry_ticket.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_empresa = QLineEdit()
        self.entry_rut_proveedor = QLineEdit()
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["dark", "light", "system"])
        self.btn_test_api = QPushButton("Prueba rapida API")
        self.btn_test_api.clicked.connect(self._start_api_test)
        self._action_buttons.append(self.btn_test_api)

        grid.addWidget(self._labeled_field("Ticket API", self.entry_ticket), 0, 0, 1, 2)
        grid.addWidget(self._labeled_field("Codigo empresa", self.entry_empresa), 0, 2)
        grid.addWidget(self._labeled_field("RUT proveedor", self.entry_rut_proveedor), 0, 3)
        grid.addWidget(self._labeled_field("Tema", self.combo_theme), 1, 0)
        grid.addWidget(self._labeled_field("Accion", self.btn_test_api), 1, 1)
        layout.addLayout(grid)
        return card

    def _build_correo_card(self) -> QWidget:
        card = self._card(
            "Correo y notificaciones",
            "El mismo usuario Gmail sirve para notificaciones SMTP y lectura IMAP de OCs privadas.",
        )
        layout = card.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.chk_smtp_enabled = QCheckBox("Activar notificaciones por email")
        self.entry_smtp_host = QLineEdit()
        self.entry_smtp_port = QSpinBox()
        self.entry_smtp_port.setRange(1, 65535)
        self.entry_smtp_port.setValue(587)
        self.entry_smtp_user = QLineEdit()
        self.entry_smtp_pass = QLineEdit()
        self.entry_smtp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry_test_email = QLineEdit()
        self.btn_test_email = QPushButton("Probar envio")
        self.btn_test_email.clicked.connect(self._start_email_test)
        self._action_buttons.append(self.btn_test_email)

        grid.addWidget(self.chk_smtp_enabled, 0, 0, 1, 2)
        grid.addWidget(self._labeled_field("Servidor SMTP", self.entry_smtp_host), 1, 0)
        grid.addWidget(self._labeled_field("Puerto", self.entry_smtp_port), 1, 1)
        grid.addWidget(self._labeled_field("Usuario / correo", self.entry_smtp_user), 2, 0, 1, 2)
        grid.addWidget(self._labeled_field("Contrasena", self.entry_smtp_pass), 3, 0, 1, 2)
        grid.addWidget(self._labeled_field("Correo de prueba", self.entry_test_email), 4, 0)
        grid.addWidget(self._labeled_field("Accion", self.btn_test_email), 4, 1)
        layout.addLayout(grid)
        return card

    def _build_imap_card(self) -> QWidget:
        card = self._card(
            "Gmail / IMAP y automatizacion",
            "Define desde donde se leen los correos privados y cada cuanto se sincroniza automaticamente.",
        )
        layout = card.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.entry_imap_server = QLineEdit()
        self.entry_imap_port = QSpinBox()
        self.entry_imap_port.setRange(1, 65535)
        self.entry_imap_port.setValue(993)
        self.entry_imap_folder = QLineEdit()
        self.entry_imap_filter = QLineEdit()
        self.chk_auto_sync = QCheckBox("Activar sincronizacion automatica")
        self.spin_auto_days = QSpinBox()
        self.spin_auto_days.setRange(1, 90)
        self.spin_auto_days.setValue(7)
        self.spin_auto_interval = QSpinBox()
        self.spin_auto_interval.setRange(1, 180)
        self.spin_auto_interval.setValue(15)

        grid.addWidget(self._labeled_field("Servidor IMAP", self.entry_imap_server), 0, 0)
        grid.addWidget(self._labeled_field("Puerto", self.entry_imap_port), 0, 1)
        grid.addWidget(self._labeled_field("Carpeta", self.entry_imap_folder), 0, 2)
        grid.addWidget(self._labeled_field("Filtro asunto", self.entry_imap_filter), 1, 0, 1, 2)
        grid.addWidget(self.chk_auto_sync, 1, 2)
        grid.addWidget(self._labeled_field("Dias de ventana", self.spin_auto_days), 2, 0)
        grid.addWidget(self._labeled_field("Intervalo (min)", self.spin_auto_interval), 2, 1)
        layout.addLayout(grid)
        return card

    def _build_catalogs_card(self) -> QWidget:
        card = self._card(
            "Catalogos y cargas",
            "Permite cambiar rutas y recargar catalogos locales desde Excel sin salir de la nueva UI.",
        )
        layout = card.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        specs = [
            ("homologacion_path", "Convenio Marco", self._browse_homo, self._import_homo),
            ("maestra_path", "Maestra materiales", self._browse_maestra, self._import_maestra),
            ("cartera_path", "Cartera clientes", self._browse_cartera, self._import_cartera),
            ("correos_path", "Correos vendedores", self._browse_correos, self._import_correos),
            ("redsalud_homo_path", "Homo RedSalud", self._browse_redsalud, self._import_redsalud),
            ("licitaciones_path", "Licitaciones", self._browse_licitaciones, self._import_licitaciones),
        ]

        for row, (key, label, browse_handler, import_handler) in enumerate(specs):
            label_widget = QLabel(label)
            label_widget.setObjectName("SectionEyebrow")
            entry = QLineEdit()
            browse = QPushButton("...")
            browse.setFixedWidth(30)
            browse.clicked.connect(browse_handler)
            action = QPushButton("Actualizar")
            action.clicked.connect(import_handler)
            self._action_buttons.append(action)
            status = QLabel("Sin ruta")
            status.setObjectName("CardBody")
            grid.addWidget(label_widget, row, 0)
            grid.addWidget(entry, row, 1)
            grid.addWidget(browse, row, 2)
            grid.addWidget(action, row, 3)
            grid.addWidget(status, row, 4)
            self._catalog_rows[key] = {"entry": entry, "action": action, "status": status, "label": label}

        layout.addLayout(grid)
        return card

    def _build_actions_card(self) -> QWidget:
        card = self._card(
            "Acciones generales",
            "Guarda la configuracion actual, abre carpetas clave y mantiene una bitacora corta de trabajo.",
        )
        layout = card.layout()

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_save = QPushButton("Guardar configuracion")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(lambda _checked=False: self._save_config_from_form(True))
        self._action_buttons.append(self.btn_save)
        self.btn_open_catalogs = QPushButton("Abrir catalogos")
        self.btn_open_catalogs.clicked.connect(lambda: self._open_path(get_catalogs_dir()))
        self.btn_open_data = QPushButton("Abrir datos")
        self.btn_open_data.clicked.connect(lambda: self._open_path(get_data_dir()))
        self.btn_open_config = QPushButton("Abrir config")
        self.btn_open_config.clicked.connect(lambda: self._open_path(get_config_dir()))
        actions.addWidget(self.btn_save)
        actions.addWidget(self.btn_open_catalogs)
        actions.addWidget(self.btn_open_data)
        actions.addWidget(self.btn_open_config)
        actions.addStretch(1)

        self.task_status = QLabel("Sin tarea activa.")
        self.task_status.setObjectName("PageSubtitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(140)

        layout.addLayout(actions)
        layout.addWidget(self.progress)
        layout.addWidget(self.task_status)
        layout.addWidget(self.log_box)
        return card

    def _set_notice(self, kind: str, message: str) -> None:
        styles = {
            "info": "border:1px solid #22304A; background:#0F172A; color:#CBD5E1; border-radius:10px; padding:8px 10px;",
            "success": "border:1px solid #14532D; background:#052E1A; color:#BBF7D0; border-radius:10px; padding:8px 10px;",
            "error": "border:1px solid #7F1D1D; background:#3B0A0A; color:#FECACA; border-radius:10px; padding:8px 10px;",
        }
        self.notice_label.setStyleSheet(styles.get(kind, styles["info"]))
        self.notice_label.setText(message)

    def _append_log(self, message: str) -> None:
        self.log_box.append(message)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _clear_log(self) -> None:
        self.log_box.clear()
        self.progress.setValue(0)
        self.task_status.setText("Bitacora limpiada.")

    def on_show(self) -> None:
        self.context.config = load_config()
        cfg = self.context.config

        self.entry_ticket.setText(cfg.api_ticket)
        self.entry_empresa.setText(cfg.codigo_empresa or "227926")
        self.entry_rut_proveedor.setText(cfg.rut_proveedor or "76.215.260-6")
        self.combo_theme.setCurrentText(cfg.theme or "dark")

        self.chk_smtp_enabled.setChecked(bool(cfg.smtp_enabled))
        self.entry_smtp_host.setText(cfg.smtp_host or "smtp.office365.com")
        self.entry_smtp_port.setValue(int(cfg.smtp_port or 587))
        self.entry_smtp_user.setText(cfg.smtp_user or "")
        self.entry_smtp_pass.setText(cfg.smtp_password or "")
        self.entry_test_email.setText(cfg.smtp_user or "")

        self.entry_imap_server.setText(cfg.imap_server or "imap.gmail.com")
        self.entry_imap_port.setValue(int(cfg.imap_port or 993))
        self.entry_imap_folder.setText(cfg.imap_folder or "INBOX")
        self.entry_imap_filter.setText(cfg.imap_filter_subject or "ORDEN DE COMPRA")
        self.chk_auto_sync.setChecked(bool(cfg.auto_sync))
        self.spin_auto_days.setValue(int(cfg.auto_sync_days or 7))
        self.spin_auto_interval.setValue(int(cfg.auto_sync_interval or 15))

        defaults = {
            "homologacion_path": str(get_default_homo_path()),
            "maestra_path": str(get_default_maestra_path()),
            "cartera_path": str(get_default_cartera_path()),
            "correos_path": str(get_default_correos_path()),
            "redsalud_homo_path": str(get_default_redsalud_homo_path()),
            "licitaciones_path": str(get_default_licitaciones_path()),
        }
        for key, row in self._catalog_rows.items():
            value = getattr(cfg, key, "") or defaults[key]
            row["entry"].setText(value)
            self._update_path_status(key)

        self._refresh_summary()
        if not self._busy:
            self.task_status.setText("Configuracion cargada desde disco.")

    def _refresh_summary(self) -> None:
        homo = count_homologacion()
        cartera = count_cartera()
        redsalud = get_redsalud_homo_service().count()
        licit = get_licitaciones_service().count()

        self._summary_labels["cm"].setText(str(homo["cm"]))
        self._summary_labels["sap"].setText(str(homo["sap"]))
        self._summary_labels["cartera"].setText(str(cartera))
        self._summary_labels["redsalud"].setText(str(redsalud))
        self._summary_labels["licit"].setText(str(licit))

    def _update_path_status(self, key: str) -> None:
        row = self._catalog_rows[key]
        raw = row["entry"].text().strip()
        exists = bool(raw) and Path(raw).exists()
        row["status"].setText("Disponible" if exists else "Pendiente")
        row["status"].setStyleSheet("color:#6EE7B7;" if exists else "color:#FCA5A5;")

    def _open_path(self, path: Path) -> None:
        try:
            os.startfile(str(path))
        except Exception as exc:
            QMessageBox.warning(self, "Abrir carpeta", f"No se pudo abrir la ruta:\n{path}\n\n{exc}")

    def _save_config_from_form(self, show_message: bool = True) -> AppConfig | None:
        try:
            cfg = load_config()
            cfg.api_ticket = self.entry_ticket.text().strip()
            cfg.codigo_empresa = self.entry_empresa.text().strip() or "227926"
            cfg.rut_proveedor = self.entry_rut_proveedor.text().strip() or "76.215.260-6"
            cfg.theme = self.combo_theme.currentText()

            cfg.smtp_enabled = self.chk_smtp_enabled.isChecked()
            cfg.smtp_host = self.entry_smtp_host.text().strip() or "smtp.office365.com"
            cfg.smtp_port = int(self.entry_smtp_port.value())
            cfg.smtp_user = self.entry_smtp_user.text().strip()
            cfg.smtp_password = self.entry_smtp_pass.text()

            cfg.imap_server = self.entry_imap_server.text().strip() or "imap.gmail.com"
            cfg.imap_port = int(self.entry_imap_port.value())
            cfg.imap_folder = self.entry_imap_folder.text().strip() or "INBOX"
            cfg.imap_filter_subject = self.entry_imap_filter.text().strip() or "ORDEN DE COMPRA"
            cfg.auto_sync = self.chk_auto_sync.isChecked()
            cfg.auto_sync_days = int(self.spin_auto_days.value())
            cfg.auto_sync_interval = int(self.spin_auto_interval.value())

            for key, row in self._catalog_rows.items():
                setattr(cfg, key, row["entry"].text().strip())

            save_config(cfg)
            self.context.config = cfg
            for key in self._catalog_rows:
                self._update_path_status(key)

            self._set_notice("success", "Configuracion guardada correctamente.")
            self._append_log("Configuracion guardada.")
            if show_message:
                QMessageBox.information(self, "Configuracion", "Configuracion guardada correctamente.")
            return cfg
        except Exception as exc:
            self._set_notice("error", f"No se pudo guardar la configuracion: {exc}")
            QMessageBox.critical(self, "Configuracion", f"No se pudo guardar la configuracion.\n\n{exc}")
            return None

    def _start_task(
        self,
        trigger: QPushButton,
        worker: TaskWorker,
        callback: TaskCallback,
        start_message: str,
    ) -> None:
        if self._busy:
            QMessageBox.information(self, "Tarea en curso", "Espera a que termine la operacion actual.")
            return

        self._busy = True
        self._queue = queue.Queue()
        self._task_callback = callback
        self.progress.setRange(0, 0)
        self.task_status.setText(start_message)
        self._append_log(start_message)

        for btn in self._action_buttons:
            btn.setEnabled(False)
        trigger.setText("Procesando...")

        def _runner() -> None:
            try:
                result = worker()
            except Exception as exc:
                result = {"ok": False, "message": str(exc)}
            self._queue.put(result)

        threading.Thread(target=_runner, daemon=True).start()
        self.poll_timer.start()

    def _poll_queue(self) -> None:
        if not self._queue:
            self.poll_timer.stop()
            return

        try:
            result = self._queue.get_nowait()
        except queue.Empty:
            return

        self.poll_timer.stop()
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if result.get("ok") else 0)
        self._busy = False
        for btn in self._action_buttons:
            btn.setEnabled(True)
        self.btn_test_api.setText("Prueba rapida API")
        self.btn_test_email.setText("Probar envio")
        for row in self._catalog_rows.values():
            row["action"].setText("Actualizar")

        callback = self._task_callback
        self._task_callback = None
        self._queue = None
        if callback:
            callback(result)

    def _finish_task(self, result: dict[str, Any], title: str) -> None:
        ok = bool(result.get("ok"))
        message = str(result.get("message", "Operacion finalizada."))
        self.task_status.setText(message)
        self._append_log(message)
        self._set_notice("success" if ok else "error", message)
        box = QMessageBox.information if ok else QMessageBox.warning
        box(self, title, message)

    def _start_api_test(self) -> None:
        cfg = self._save_config_from_form(show_message=False)
        if not cfg:
            return
        if not cfg.api_ticket:
            QMessageBox.warning(self, "Sin ticket", "Configura el ticket API antes de hacer la prueba.")
            return

        def worker() -> dict[str, Any]:
            ok, message = MercadoPublicoAPI(ticket=cfg.api_ticket, codigo_empresa=cfg.codigo_empresa).probar_conexion_rapida()
            return {"ok": ok, "message": message}

        self._start_task(
            self.btn_test_api,
            worker,
            lambda result: self._finish_task(result, "Prueba API"),
            "Probando conectividad con Mercado Publico...",
        )

    def _start_email_test(self) -> None:
        cfg = self._save_config_from_form(show_message=False)
        if not cfg:
            return
        if not cfg.smtp_user:
            QMessageBox.warning(self, "Correo", "Configura el usuario SMTP antes de probar el envio.")
            return
        destino = self.entry_test_email.text().strip() or cfg.smtp_user

        def worker() -> dict[str, Any]:
            ok, message = get_email_service().enviar_prueba(cfg, to_email=destino)
            return {"ok": ok, "message": message}

        self._start_task(
            self.btn_test_email,
            worker,
            lambda result: self._finish_task(result, "Correo"),
            f"Enviando correo de prueba a {destino}...",
        )

    def _run_catalog_import(self, key: str, title: str, worker: TaskWorker) -> None:
        cfg = self._save_config_from_form(show_message=False)
        if not cfg:
            return
        path = self._catalog_rows[key]["entry"].text().strip()
        if not path:
            QMessageBox.warning(self, title, "Configura una ruta antes de actualizar este catalogo.")
            return

        action = self._catalog_rows[key]["action"]
        action.setText("Procesando...")

        def callback(result: dict[str, Any]) -> None:
            self._update_path_status(key)
            self._refresh_summary()
            self._finish_task(result, title)

        self._start_task(action, worker, callback, f"Actualizando {title}...")

    def _import_homo(self) -> None:
        path = self._catalog_rows["homologacion_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            count, errors = get_homologacion_service().cargar_homologacion_excel(path)
            msg = f"Convenio Marco actualizado: {count} registros."
            if errors:
                msg += "\n" + "\n".join(errors[:4])
            return {"ok": count > 0, "message": msg}

        self._run_catalog_import("homologacion_path", "Convenio Marco", worker)

    def _import_maestra(self) -> None:
        path = self._catalog_rows["maestra_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            count, errors = get_homologacion_service().cargar_maestra_sap(path)
            get_maestra_service().reload()
            msg = f"Maestra SAP actualizada: {count} registros."
            if errors:
                msg += "\n" + "\n".join(errors[:4])
            return {"ok": count > 0, "message": msg}

        self._run_catalog_import("maestra_path", "Maestra SAP", worker)

    def _import_cartera(self) -> None:
        path = self._catalog_rows["cartera_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            count, errors = get_cartera_service().cargar_cartera_excel(path)
            msg = f"Cartera actualizada: {count} registros."
            if errors:
                msg += "\n" + "\n".join(errors[:4])
            return {"ok": count > 0, "message": msg}

        self._run_catalog_import("cartera_path", "Cartera", worker)

    def _import_correos(self) -> None:
        path = self._catalog_rows["correos_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            ok, message = get_email_service().cargar_correos(path)
            return {"ok": ok, "message": message}

        self._run_catalog_import("correos_path", "Correos vendedores", worker)

    def _import_redsalud(self) -> None:
        path = self._catalog_rows["redsalud_homo_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            count, errors = get_redsalud_homo_service().cargar_excel(path)
            msg = f"Homologacion RedSalud actualizada: {count} registros."
            if errors:
                msg += "\n" + "\n".join(errors[:4])
            return {"ok": count > 0, "message": msg}

        self._run_catalog_import("redsalud_homo_path", "Homo RedSalud", worker)

    def _import_licitaciones(self) -> None:
        path = self._catalog_rows["licitaciones_path"]["entry"].text().strip()

        def worker() -> dict[str, Any]:
            count, errors = get_licitaciones_service().importar_lic(path)
            msg = f"Licitaciones actualizadas: {count} referencias."
            if errors:
                msg += "\n" + "\n".join(errors[:4])
            return {"ok": count > 0, "message": msg}

        self._run_catalog_import("licitaciones_path", "Licitaciones", worker)

    def _browse_path(self, key: str, title: str) -> None:
        current = self._catalog_rows[key]["entry"].text().strip() or str(get_catalogs_dir())
        selected, _ = QFileDialog.getOpenFileName(
            self,
            title,
            current,
            "Excel (*.xlsx *.xlsm *.csv);;Todos (*.*)",
        )
        if selected:
            self._catalog_rows[key]["entry"].setText(selected)
            self._update_path_status(key)

    def _browse_homo(self) -> None:
        self._browse_path("homologacion_path", "Seleccionar homologacion")

    def _browse_maestra(self) -> None:
        self._browse_path("maestra_path", "Seleccionar maestra")

    def _browse_cartera(self) -> None:
        self._browse_path("cartera_path", "Seleccionar cartera")

    def _browse_correos(self) -> None:
        self._browse_path("correos_path", "Seleccionar correos")

    def _browse_redsalud(self) -> None:
        self._browse_path("redsalud_homo_path", "Seleccionar homologacion RedSalud")

    def _browse_licitaciones(self) -> None:
        self._browse_path("licitaciones_path", "Seleccionar licitaciones")
