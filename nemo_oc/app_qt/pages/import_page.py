"""Modulo real de importaciones para la shell Qt."""

from __future__ import annotations

import queue
import threading
from collections import deque
from datetime import datetime

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import get_logs_dir, load_config, save_config
from app.services.mp_api_service import MercadoPublicoAPI
from app.services.sync_privado_service import start_sync_privado_thread
from app.services.sync_service import start_sync_thread
from app_qt.bootstrap import QtAppContext


class ImportPage(QWidget):
    page_title = "Importaciones"
    page_subtitle = (
        "Mercado Publico y OCs privadas en una shell desktop con progreso, "
        "bitacora y operaciones largas desacopladas de la interfaz."
    )
    page_eyebrow = "Modulo operativo"

    def __init__(self, context: QtAppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self._quick_buttons: dict[str, QPushButton] = {}
        self._active_quick: str | None = "7d"
        self._queue: queue.Queue | None = None
        self._busy_kind: str | None = None
        self._pending_success = False
        self._progress_total = 0
        self._recent_lines: deque[str] = deque(maxlen=120)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(160)
        self.poll_timer.timeout.connect(self._poll_queue)

        self._build()
        self._apply_quick_range("7d", 7)
        self.on_show()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_mp_card())
        root.addWidget(self._build_privado_card())
        root.addWidget(self._build_activity_card(), 1)

    def _build_mp_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Mercado Publico")
        title.setObjectName("CardTitle")
        subtitle = QLabel(
            "Consulta la API con el ticket actual, permite diagnostico rapido y "
            "sincroniza OCs segun el rango de fechas elegido."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.dateChanged.connect(self._clear_quick_range)

        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.dateChanged.connect(self._clear_quick_range)

        self.chk_cm = QCheckBox("Convenio Marco (CM)")
        self.chk_cm.setChecked(True)
        self.chk_otras = QCheckBox("Otras compras")
        self.chk_otras.setChecked(True)

        self.btn_test_api = QPushButton("Prueba rapida API")
        self.btn_test_api.clicked.connect(self._start_api_test)
        self.btn_sync_mp = QPushButton("Descargar OCs")
        self.btn_sync_mp.setObjectName("PrimaryButton")
        self.btn_sync_mp.clicked.connect(self._start_mp_sync)

        quick_wrap = QWidget()
        quick_row = QHBoxLayout(quick_wrap)
        quick_row.setContentsMargins(0, 0, 0, 0)
        quick_row.setSpacing(6)
        for key, label, days in [("today", "Hoy", 0), ("7d", "7 dias", 7), ("30d", "30 dias", 30), ("90d", "90 dias", 90)]:
            btn = QPushButton(label)
            btn.setCheckable(False)
            btn.setProperty("quickActive", key == self._active_quick)
            btn.clicked.connect(lambda _checked=False, d=days, k=key: self._apply_quick_range(k, d))
            quick_row.addWidget(btn)
            self._quick_buttons[key] = btn
        quick_row.addStretch(1)

        tipo_wrap = QWidget()
        tipo_row = QHBoxLayout(tipo_wrap)
        tipo_row.setContentsMargins(0, 0, 0, 0)
        tipo_row.setSpacing(10)
        tipo_row.addWidget(self.chk_cm)
        tipo_row.addWidget(self.chk_otras)
        tipo_row.addStretch(1)

        actions_wrap = QWidget()
        actions_row = QHBoxLayout(actions_wrap)
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)
        actions_row.addWidget(self.btn_test_api)
        actions_row.addWidget(self.btn_sync_mp)
        actions_row.addStretch(1)

        grid.addWidget(self._labeled_field("Fecha desde", self.date_desde), 0, 0)
        grid.addWidget(self._labeled_field("Fecha hasta", self.date_hasta), 0, 1)
        grid.addWidget(self._labeled_field("Rangos rapidos", quick_wrap), 0, 2, 1, 2)
        grid.addWidget(self._labeled_field("Tipos de OC", tipo_wrap), 1, 0, 1, 2)
        grid.addWidget(self._labeled_field("Acciones", actions_wrap), 1, 2, 1, 2)

        layout.addLayout(grid)

        self.test_banner = QLabel("Sin prueba reciente.")
        self.test_banner.setWordWrap(True)
        self._set_banner_state("info", "Sin prueba reciente.")
        layout.addWidget(self.test_banner)

        return card

    def _build_privado_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("OCs privadas")
        title.setObjectName("CardTitle")
        subtitle = QLabel(
            "Lee la casilla configurada, clasifica holdings por RUT y parser, y "
            "persiste PDFs privados sin depender de la web."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        self.btn_sync_privado = QPushButton("Sincronizar Gmail")
        self.btn_sync_privado.clicked.connect(self._start_privado_sync)

        info = QLabel(
            "Recomendado cuando ya existe reenvio automatico hacia la casilla "
            "de automatizacion y el holding esta configurado."
        )
        info.setObjectName("CardBody")
        info.setWordWrap(True)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(info, 1)
        row.addWidget(self.btn_sync_privado, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(row)
        return card

    def _build_activity_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Actividad y bitacora")
        title.setObjectName("CardTitle")
        self.status_chip = QLabel("Idle")
        self.status_chip.setObjectName("Chip")
        self.status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.status_chip)
        layout.addLayout(header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.lbl_progress = QLabel("Sin ejecucion en curso.")
        self.lbl_progress.setObjectName("PageSubtitle")

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_progress)

        log_header = QHBoxLayout()
        log_title = QLabel("Bitacora")
        log_title.setObjectName("SectionEyebrow")
        self.btn_clear_log = QPushButton("Limpiar")
        self.btn_clear_log.clicked.connect(self._clear_log)
        log_header.addWidget(log_title)
        log_header.addStretch(1)
        log_header.addWidget(self.btn_clear_log)
        layout.addLayout(log_header)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)

        return card

    def on_show(self) -> None:
        self.context.config = load_config()
        self._load_recent_logs()
        if not self._busy_kind:
            self._set_status_chip("Idle", "idle")
        self._set_busy_state(self._busy_kind is not None)

    def _apply_quick_range(self, key: str, days: int) -> None:
        today = QDate.currentDate()
        start = today.addDays(-days)
        self._active_quick = key

        self.date_desde.blockSignals(True)
        self.date_hasta.blockSignals(True)
        self.date_desde.setDate(start)
        self.date_hasta.setDate(today)
        self.date_desde.blockSignals(False)
        self.date_hasta.blockSignals(False)

        self._refresh_quick_buttons()

    def _clear_quick_range(self) -> None:
        self._active_quick = None
        self._refresh_quick_buttons()

    def _refresh_quick_buttons(self) -> None:
        for key, btn in self._quick_buttons.items():
            btn.setProperty("quickActive", key == self._active_quick)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

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

    def _set_banner_state(self, kind: str, message: str) -> None:
        styles = {
            "success": "border:1px solid #14532D; background:#052E1A; color:#BBF7D0; border-radius:10px; padding:8px 10px;",
            "error": "border:1px solid #7F1D1D; background:#3B0A0A; color:#FECACA; border-radius:10px; padding:8px 10px;",
            "info": "border:1px solid #22304A; background:#0F172A; color:#CBD5E1; border-radius:10px; padding:8px 10px;",
        }
        self.test_banner.setStyleSheet(styles.get(kind, styles["info"]))
        self.test_banner.setText(message)

    def _set_status_chip(self, text: str, kind: str = "idle") -> None:
        styles = {
            "idle": "background-color:#111827; border:1px solid #22304A; color:#94A3B8; border-radius:999px; padding:4px 10px;",
            "running": "background-color:#132C47; border:1px solid #24517A; color:#93C5FD; border-radius:999px; padding:4px 10px;",
            "success": "background-color:#103226; border:1px solid #1F6A4C; color:#6EE7B7; border-radius:999px; padding:4px 10px;",
            "error": "background-color:#421A1A; border:1px solid #7F1D1D; color:#FCA5A5; border-radius:999px; padding:4px 10px;",
        }
        self.status_chip.setText(text)
        self.status_chip.setStyleSheet(styles.get(kind, styles["idle"]))

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        self._recent_lines.append(line)
        self.log_box.setPlainText("\n".join(self._recent_lines))
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _clear_log(self) -> None:
        self._recent_lines.clear()
        self.log_box.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Bitacora limpiada.")
        if not self._busy_kind:
            self._set_status_chip("Idle", "idle")

    def _load_recent_logs(self) -> None:
        log_file = get_logs_dir() / "app.log"
        if not log_file.exists():
            if not self._recent_lines:
                self.log_box.setPlainText("Aun no existe bitacora en disco.")
            return

        try:
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:]
        except Exception:
            lines = []

        if not lines and not self._recent_lines:
            self.log_box.setPlainText("Bitacora disponible, pero sin eventos recientes.")
            return

        if lines and not self._busy_kind and not self._recent_lines:
            self._recent_lines = deque(lines, maxlen=120)
            self.log_box.setPlainText("\n".join(self._recent_lines))
            self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _set_busy_state(self, busy: bool) -> None:
        self.btn_sync_mp.setEnabled(not busy)
        self.btn_sync_privado.setEnabled(not busy)
        self.btn_test_api.setEnabled(not busy)
        self.chk_cm.setEnabled(not busy)
        self.chk_otras.setEnabled(not busy)
        self.date_desde.setEnabled(not busy)
        self.date_hasta.setEnabled(not busy)
        for btn in self._quick_buttons.values():
            btn.setEnabled(not busy)

    def _start_api_test(self) -> None:
        cfg = load_config()
        self.context.config = cfg
        if not cfg.api_ticket:
            QMessageBox.warning(self, "Sin ticket", "Configura el ticket API antes de hacer la prueba rapida.")
            return

        q: queue.Queue = queue.Queue()
        self._queue = q
        self._busy_kind = "test_api"
        self._pending_success = False
        self._set_busy_state(True)
        self._set_status_chip("Probando API", "running")
        self.lbl_progress.setText("Probando conectividad y ticket...")
        self.progress_bar.setValue(12)
        self._append_log("Iniciando prueba rapida de la API...")

        threading.Thread(target=self._run_api_test_worker, args=(cfg.api_ticket, cfg.codigo_empresa, q), daemon=True).start()
        self.poll_timer.start()

    @staticmethod
    def _run_api_test_worker(ticket: str, codigo_empresa: str, out: queue.Queue) -> None:
        api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=codigo_empresa)
        ok, message = api.probar_conexion_rapida()
        out.put({"type": "test_result", "ok": ok, "message": message})
        out.put({"type": "done_local"})

    def _start_mp_sync(self) -> None:
        cfg = load_config()
        self.context.config = cfg
        if not cfg.api_ticket:
            QMessageBox.warning(self, "Sin ticket", "Configura el ticket API antes de sincronizar.")
            return
        if not self.chk_cm.isChecked() and not self.chk_otras.isChecked():
            QMessageBox.warning(self, "Sin tipo", "Selecciona al menos un tipo de OC para sincronizar.")
            return

        fecha_desde = self.date_desde.date().toPython()
        fecha_hasta = self.date_hasta.date().toPython()
        self._queue = start_sync_thread(
            ticket=cfg.api_ticket,
            codigo_empresa=cfg.codigo_empresa,
            fecha_desde=datetime.combine(fecha_desde, datetime.min.time()),
            fecha_hasta=datetime.combine(fecha_hasta, datetime.min.time()),
            solo_cm=self.chk_cm.isChecked() and not self.chk_otras.isChecked(),
        )
        self._busy_kind = "mercado_publico"
        self._pending_success = False
        self._progress_total = 0
        self._set_busy_state(True)
        self._set_status_chip("Sincronizando MP", "running")
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Iniciando sincronizacion de Mercado Publico...")
        self._append_log("Solicitud de sincronizacion Mercado Publico enviada.")
        self.poll_timer.start()

    def _start_privado_sync(self) -> None:
        cfg = load_config()
        self.context.config = cfg
        if not cfg.smtp_user or not cfg.smtp_password:
            QMessageBox.warning(
                self,
                "Credenciales Gmail",
                "Configura el usuario y la clave de Gmail antes de sincronizar OCs privadas.",
            )
            return

        self._queue = start_sync_privado_thread(
            smtp_user=cfg.smtp_user,
            smtp_password=cfg.smtp_password,
            imap_server=cfg.imap_server,
            imap_port=cfg.imap_port,
            imap_folder=cfg.imap_folder,
            filter_subject=cfg.imap_filter_subject or "ORDEN DE COMPRA",
        )
        self._busy_kind = "privados"
        self._pending_success = False
        self._progress_total = 0
        self._set_busy_state(True)
        self._set_status_chip("Sincronizando Gmail", "running")
        self.progress_bar.setValue(0)
        self.lbl_progress.setText("Iniciando sincronizacion de OCs privadas...")
        self._append_log("Solicitud de sincronizacion privada enviada.")
        self.poll_timer.start()

    def _poll_queue(self) -> None:
        if not self._queue:
            self.poll_timer.stop()
            return

        try:
            while True:
                msg = self._queue.get_nowait()
                self._handle_queue_message(msg)
        except queue.Empty:
            pass

    def _handle_queue_message(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type == "log":
            self._append_log(msg.get("message", ""))
            return

        if msg_type == "progress":
            current = int(msg.get("current", 0))
            total = max(int(msg.get("total", 1)), 1)
            self._progress_total = total
            pct = max(0, min(100, round((current / total) * 100)))
            self.progress_bar.setValue(pct)
            unidad = "PDFs" if self._busy_kind == "privados" else "OCs"
            self.lbl_progress.setText(f"{current} / {total} {unidad} procesadas")
            return

        if msg_type == "test_result":
            ok = bool(msg.get("ok"))
            message = msg.get("message", "")
            self._pending_success = ok
            self._set_banner_state("success" if ok else "error", message)
            self._append_log(message)
            self.progress_bar.setValue(100 if ok else 0)
            self.lbl_progress.setText(message)
            return

        if msg_type == "done":
            message = msg.get("message", "Proceso completado.")
            self._pending_success = True
            self.progress_bar.setValue(100)
            self.lbl_progress.setText(message)
            self._append_log(message)
            self._finish_task(success=True)
            return

        if msg_type == "error":
            message = msg.get("message", "Se produjo un error.")
            self._pending_success = False
            self.progress_bar.setValue(0)
            self.lbl_progress.setText(message)
            self._append_log(f"ERROR: {message}")
            self._finish_task(success=False)
            return

        if msg_type == "done_local":
            self._finish_task(success=self._pending_success)

    def _finish_task(self, success: bool) -> None:
        self.poll_timer.stop()
        self._set_busy_state(False)

        if success:
            self._set_status_chip("Completado", "success")
            if self._busy_kind in {"mercado_publico", "privados"}:
                cfg = load_config()
                cfg.last_sync = datetime.now().isoformat()
                save_config(cfg)
                self.context.config = cfg
                sidebar = getattr(self.window(), "sidebar", None)
                if sidebar and hasattr(sidebar, "refresh_status"):
                    sidebar.refresh_status()
        else:
            self._set_status_chip("Con error", "error")

        self._busy_kind = None
        self._queue = None
