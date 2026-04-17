"""Modulo de estadisticas y revision experta para la shell Qt."""

from __future__ import annotations

import queue
import threading
from datetime import date, timedelta
from typing import Any

from PySide6.QtCore import QDate, QTimer, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services import review_service

QUEUE_LIMIT = 220
QUEUE_MODE_LABELS = {
    "pendientes": "Pendientes",
    "con_sugerencia": "Con sugerencia",
    "sin_sugerencia": "Sin sugerencia",
    "manuales": "Revisadas",
    "todos": "Todos",
}


class MetricTile(QFrame):
    """Card compacta para mostrar una metrica y permitir filtros rapidos."""

    clicked = Signal(str)

    def __init__(
        self,
        title: str,
        value: str,
        helper: str,
        accent: str,
        filter_mode: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._filter_mode = filter_mode
        self.setObjectName("PageCard")
        self.setStyleSheet(
            f"""
            QFrame#PageCard {{
                border-left: 4px solid {accent};
            }}
            """
        )
        if filter_mode:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("SectionEyebrow")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")

        self.helper_label = QLabel(helper)
        self.helper_label.setObjectName("MetricCaption")
        self.helper_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.helper_label)
        layout.addStretch(1)

    def set_content(self, value: str, helper: str | None = None) -> None:
        self.value_label.setText(value)
        if helper is not None:
            self.helper_label.setText(helper)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._filter_mode:
            self.clicked.emit(self._filter_mode)
            event.accept()
            return
        super().mousePressEvent(event)


class StatsPage(QWidget):
    page_title = "Estadisticas y revision"
    page_subtitle = "Cobertura automatica, cola experta y correccion inline sin salir de la pantalla."
    page_eyebrow = "Mesa experta"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._summary: dict[str, Any] = {}
        self._raw_queue: list[dict[str, Any]] = []
        self._filtered_queue: list[dict[str, Any]] = []
        self._selected_key: tuple[str, int] | None = None
        self._session_resolved = 0
        self._active_quick: str | None = "7d"
        self._queue_mode = "pendientes"
        self._load_queue: queue.Queue | None = None
        self._busy = False
        self._quick_buttons: dict[str, QPushButton] = {}
        self._mode_buttons: dict[str, QPushButton] = {}
        self._metric_tiles: dict[str, MetricTile] = {}
        self._strip_values: dict[str, QLabel] = {}

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(180)
        self.poll_timer.timeout.connect(self._poll_loader)

        self._build()
        self._apply_quick_range("7d", 7, auto_refresh=False)

    def on_show(self) -> None:
        if not self._summary and not self._busy:
            self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_summary_card())
        root.addWidget(self._build_queue_card(), 1)

    def _build_summary_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Ventana analizada")
        title.setObjectName("CardTitle")
        self.summary_status_chip = QLabel("Cargando...")
        self.summary_status_chip.setObjectName("Chip")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.summary_status_chip)
        layout.addLayout(header)

        controls = QGridLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setHorizontalSpacing(8)
        controls.setVerticalSpacing(6)

        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDisplayFormat("yyyy-MM-dd")
        self.date_desde.dateChanged.connect(self._clear_quick_range)

        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDisplayFormat("yyyy-MM-dd")
        self.date_hasta.dateChanged.connect(self._clear_quick_range)

        quick_wrap = QWidget()
        quick_row = QHBoxLayout(quick_wrap)
        quick_row.setContentsMargins(0, 0, 0, 0)
        quick_row.setSpacing(6)
        for key, label, days in [("hoy", "Hoy", 0), ("7d", "7 dias", 7), ("30d", "30 dias", 30)]:
            btn = QPushButton(label)
            btn.setProperty("quickActive", key == self._active_quick)
            btn.clicked.connect(lambda _checked=False, k=key, d=days: self._apply_quick_range(k, d))
            quick_row.addWidget(btn)
            self._quick_buttons[key] = btn
        quick_row.addStretch(1)

        actions_wrap = QWidget()
        actions_row = QHBoxLayout(actions_wrap)
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)
        self.btn_refresh = QPushButton("Actualizar cola")
        self.btn_refresh.setObjectName("PrimaryButton")
        self.btn_refresh.clicked.connect(self.refresh)
        actions_row.addWidget(self.btn_refresh)
        actions_row.addStretch(1)

        controls.addWidget(self._labeled_field("Fecha desde", self.date_desde), 0, 0)
        controls.addWidget(self._labeled_field("Fecha hasta", self.date_hasta), 0, 1)
        controls.addWidget(self._labeled_field("Rangos rapidos", quick_wrap), 0, 2)
        controls.addWidget(self._labeled_field("Acciones", actions_wrap), 0, 3)
        layout.addLayout(controls)

        metrics = QGridLayout()
        metrics.setContentsMargins(0, 0, 0, 0)
        metrics.setHorizontalSpacing(8)
        metrics.setVerticalSpacing(8)

        card_specs = [
            ("total_ocs", "Total OCs", "0", "Cabeceras analizadas en el rango.", "#10B5D8", None),
            ("cobertura", "Cobertura lineas", "0%", "Lineas ya resueltas o sugeridas.", "#10B981", None),
            (
                "con_sugerencia",
                "Pendientes con sugerencia",
                "0",
                "Clic para filtrar la cola.",
                "#60A5FA",
                "con_sugerencia",
            ),
            (
                "sin_sugerencia",
                "Pendientes sin sugerencia",
                "0",
                "Clic para ver lo que requiere trabajo manual.",
                "#F59E0B",
                "sin_sugerencia",
            ),
        ]
        for idx, (key, title_text, value, helper, accent, filter_mode) in enumerate(card_specs):
            tile = MetricTile(title_text, value, helper, accent, filter_mode)
            if filter_mode:
                tile.clicked.connect(self._set_queue_mode)
            self._metric_tiles[key] = tile
            metrics.addWidget(tile, 0, idx)
        layout.addLayout(metrics)

        strips = QGridLayout()
        strips.setContentsMargins(0, 0, 0, 0)
        strips.setHorizontalSpacing(8)
        strips.setVerticalSpacing(8)
        strip_specs = [
            ("monto", "Monto cubierto", "0", "Mismo rango de fechas."),
            ("pendientes", "Lineas pendientes", "0", "Trabajo por cerrar."),
            ("manuales", "Revisadas manualmente", "0", "Asignadas por un experto."),
            ("sesion", "Resueltas esta sesion", "0", "Acumulado local de la jornada."),
        ]
        for idx, (key, title_text, value, helper) in enumerate(strip_specs):
            strip = self._build_strip(title_text, value, helper)
            self._strip_values[key] = strip.findChild(QLabel, "StripValue")  # type: ignore[assignment]
            strips.addWidget(strip, 0, idx)
        layout.addLayout(strips)

        return card

    def _build_queue_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Cola de sugerencias y correcciones")
        title.setObjectName("CardTitle")
        self.lbl_queue_meta = QLabel("Sin datos")
        self.lbl_queue_meta.setObjectName("PageSubtitle")
        self.session_chip = QLabel("0 resueltas esta sesion")
        self.session_chip.setObjectName("Chip")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.lbl_queue_meta)
        header.addWidget(self.session_chip)
        layout.addLayout(header)

        filters = QGridLayout()
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setHorizontalSpacing(8)
        filters.setVerticalSpacing(6)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por OC, comprador, itemcode o descripcion...")
        self.search_input.textChanged.connect(self._apply_filters)

        mode_wrap = QWidget()
        mode_row = QHBoxLayout(mode_wrap)
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(6)
        for mode, label in QUEUE_MODE_LABELS.items():
            btn = QPushButton(label)
            btn.setProperty("quickActive", mode == self._queue_mode)
            btn.clicked.connect(lambda _checked=False, m=mode: self._set_queue_mode(m))
            mode_row.addWidget(btn)
            self._mode_buttons[mode] = btn
        mode_row.addStretch(1)

        filters.addWidget(self._labeled_field("Busqueda", self.search_input), 0, 0, 1, 2)
        filters.addWidget(self._labeled_field("Vista", mode_wrap), 0, 2, 1, 2)
        layout.addLayout(filters)

        self.banner = QLabel("")
        self.banner.setVisible(False)
        self.banner.setWordWrap(True)
        layout.addWidget(self.banner)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)
        self.splitter.addWidget(self._build_queue_table_card())
        self.splitter.addWidget(self._build_detail_panel())
        self.splitter.setSizes([320, 360])
        layout.addWidget(self.splitter, 1)

        return card

    def _build_queue_table_card(self) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("PageCard")
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.queue_table = QTableWidget(0, 7)
        self.queue_table.setHorizontalHeaderLabels(
            ["OC", "Comprador", "Detalle linea", "Sugerencia / asignacion", "Estado", "Total", "Accion"]
        )
        self._style_table(self.queue_table, row_height=30)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_table.itemSelectionChanged.connect(self._handle_queue_selection)
        widths = [128, 154, 210, 180, 102, 92, 88]
        for idx, width in enumerate(widths):
            self.queue_table.setColumnWidth(idx, width)
        layout.addWidget(self.queue_table, 1)
        return wrap

    def _build_detail_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("PageCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Revision activa")
        title.setObjectName("CardTitle")
        self.lbl_selected_meta = QLabel("Selecciona una linea para revisar.")
        self.lbl_selected_meta.setObjectName("PageSubtitle")
        self.btn_clear = QPushButton("Limpiar asignacion")
        self.btn_clear.clicked.connect(self._clear_selected_assignment)
        self.btn_clear.setEnabled(False)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.lbl_selected_meta)
        header.addWidget(self.btn_clear)
        layout.addLayout(header)

        context_frame = QFrame()
        context_frame.setObjectName("PageCard")
        context_layout = QGridLayout(context_frame)
        context_layout.setContentsMargins(10, 10, 10, 10)
        context_layout.setHorizontalSpacing(12)
        context_layout.setVerticalSpacing(6)

        self.ctx_labels: dict[str, QLabel] = {}
        for idx, (key, label_text) in enumerate(
            [
                ("oc", "OC"),
                ("organismo", "Comprador"),
                ("detalle", "Detalle"),
                ("estado", "Estado interno"),
                ("rut", "RUT"),
                ("cantidad", "Cantidad"),
                ("total", "Total"),
                ("asignacion", "Asignacion actual"),
            ]
        ):
            label = QLabel(label_text)
            label.setObjectName("SectionEyebrow")
            value = QLabel("-")
            value.setObjectName("CardBody")
            value.setWordWrap(True)
            row = idx // 4
            col = (idx % 4) * 2
            context_layout.addWidget(label, row * 2, col, 1, 1)
            context_layout.addWidget(value, row * 2 + 1, col, 1, 1)
            self.ctx_labels[key] = value
        layout.addWidget(context_frame)

        lower = QGridLayout()
        lower.setContentsMargins(0, 0, 0, 0)
        lower.setHorizontalSpacing(8)
        lower.setVerticalSpacing(8)
        lower.addWidget(self._build_suggestions_card(), 0, 0)
        lower.addWidget(self._build_manual_card(), 0, 1)
        lower.setColumnStretch(0, 3)
        lower.setColumnStretch(1, 2)
        layout.addLayout(lower, 1)

        return panel

    def _build_suggestions_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Sugerencias del motor")
        title.setObjectName("CardTitle")
        self.lbl_suggestions_meta = QLabel("Sin linea seleccionada.")
        self.lbl_suggestions_meta.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(self.lbl_suggestions_meta)

        self.suggestions_table = QTableWidget(0, 5)
        self.suggestions_table.setHorizontalHeaderLabels(["Confianza", "ItemCode SAP", "Descripcion", "Uso", "Accion"])
        self._style_table(self.suggestions_table, row_height=28)
        self.suggestions_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.suggestions_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        widths = [76, 104, 220, 64, 78]
        for idx, width in enumerate(widths):
            self.suggestions_table.setColumnWidth(idx, width)
        layout.addWidget(self.suggestions_table, 1)
        return card

    def _build_manual_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Correccion manual desde maestra")
        title.setObjectName("CardTitle")
        self.lbl_manual_meta = QLabel("Busca itemcode o descripcion y asigna solo resultados verificados.")
        self.lbl_manual_meta.setObjectName("PageSubtitle")
        self.lbl_manual_meta.setWordWrap(True)

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(6)
        self.manual_search_input = QLineEdit()
        self.manual_search_input.setPlaceholderText("Buscar en la maestra SAP...")
        self.manual_search_input.returnPressed.connect(self._run_manual_search)
        self.btn_manual_search = QPushButton("Buscar")
        self.btn_manual_search.clicked.connect(self._run_manual_search)
        search_row.addWidget(self.manual_search_input, 1)
        search_row.addWidget(self.btn_manual_search)

        self.search_results_table = QTableWidget(0, 3)
        self.search_results_table.setHorizontalHeaderLabels(["ItemCode SAP", "Descripcion", "Accion"])
        self._style_table(self.search_results_table, row_height=28)
        self.search_results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.search_results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.search_results_table.itemDoubleClicked.connect(self._handle_search_result_double_click)
        widths = [110, 220, 78]
        for idx, width in enumerate(widths):
            self.search_results_table.setColumnWidth(idx, width)

        self.lbl_search_results = QLabel("Sin busqueda reciente.")
        self.lbl_search_results.setObjectName("PageSubtitle")

        layout.addWidget(title)
        layout.addWidget(self.lbl_manual_meta)
        layout.addLayout(search_row)
        layout.addWidget(self.lbl_search_results)
        layout.addWidget(self.search_results_table, 1)
        return card

    def refresh(self) -> None:
        if self._busy:
            return

        self._busy = True
        self.btn_refresh.setEnabled(False)
        self.summary_status_chip.setText("Cargando cola...")
        self.lbl_queue_meta.setText("Actualizando...")
        self._set_banner(None, "")

        fecha_desde = self._date_to_iso(self.date_desde.date())
        fecha_hasta = self._date_to_iso(self.date_hasta.date())

        self._load_queue = queue.Queue()
        self.poll_timer.start()
        threading.Thread(
            target=self._load_worker,
            args=(fecha_desde, fecha_hasta, QUEUE_LIMIT, self._load_queue),
            daemon=True,
        ).start()

    def _load_worker(self, fecha_desde: str, fecha_hasta: str, limit: int, out: queue.Queue) -> None:
        try:
            payload = review_service.get_analytics_data(fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=limit)
        except Exception as exc:  # pragma: no cover - defensivo
            out.put(("error", str(exc)))
            return
        out.put(("data", payload))

    def _poll_loader(self) -> None:
        if not self._load_queue:
            return
        try:
            kind, payload = self._load_queue.get_nowait()
        except queue.Empty:
            return

        self.poll_timer.stop()
        self._busy = False
        self.btn_refresh.setEnabled(True)
        self._load_queue = None

        if kind == "error":
            self.summary_status_chip.setText("Error")
            self.lbl_queue_meta.setText("No se pudo actualizar la cola.")
            QMessageBox.critical(self, "Estadisticas", f"No se pudo cargar la revision experta.\n\n{payload}")
            return

        self._summary = dict(payload["summary"])
        self._raw_queue = list(payload["queue"])
        self.summary_status_chip.setText("Actualizado")
        self._refresh_summary()
        self._apply_filters()

    def _refresh_summary(self) -> None:
        summary = self._summary
        if not summary:
            return

        self._metric_tiles["total_ocs"].set_content(
            self._fmt_int(summary.get("total_ocs", 0)),
            f"{self._fmt_int(summary.get('total_lineas', 0))} lineas en total.",
        )
        self._metric_tiles["cobertura"].set_content(
            f"{summary.get('cobertura_lineas_pct', 0):.1f}%",
            f"{self._fmt_int(summary.get('lineas_resueltas', 0))} resueltas de {self._fmt_int(summary.get('total_lineas', 0))}.",
        )
        self._metric_tiles["con_sugerencia"].set_content(
            self._fmt_int(summary.get("pendientes_con_sugerencia", 0)),
            "Clic para filtrar la cola.",
        )
        self._metric_tiles["sin_sugerencia"].set_content(
            self._fmt_int(summary.get("pendientes_sin_sugerencia", 0)),
            "Trabajo manual puro o revision fina.",
        )

        self._strip_values["monto"].setText(self._fmt_money(summary.get("monto_resuelto", 0)))
        self._strip_values["pendientes"].setText(self._fmt_int(summary.get("lineas_pendientes", 0)))
        self._strip_values["manuales"].setText(self._fmt_int(summary.get("lineas_manuales", 0)))
        self._strip_values["sesion"].setText(self._fmt_int(self._session_resolved))
        self.session_chip.setText(f"{self._fmt_int(self._session_resolved)} resueltas esta sesion")

    def _apply_filters(self) -> None:
        normalized = self.search_input.text().strip().lower()
        filtered: list[dict[str, Any]] = []
        for item in self._raw_queue:
            is_pending = self._is_pending(item)
            if self._queue_mode == "pendientes" and not is_pending:
                continue
            if self._queue_mode == "con_sugerencia" and (not is_pending or not item.get("sugerencia_principal")):
                continue
            if self._queue_mode == "manuales" and item.get("estado_homologacion") != "manual":
                continue
            if self._queue_mode == "sin_sugerencia" and (not is_pending or item.get("sugerencia_principal")):
                continue

            if normalized:
                haystack = " ".join(
                    [
                        str(item.get("codigo_oc", "")),
                        str(item.get("nombre_organismo", "")),
                        str(item.get("cliente_sap_sugerido", "")),
                        str(item.get("cartera", "")),
                        str(item.get("itemcode_sap", "") or ""),
                        str(item.get("descripcion_sap", "") or ""),
                        str(item.get("producto", "")),
                        str(item.get("especificacion_comprador", "")),
                    ]
                ).lower()
                if normalized not in haystack:
                    continue
            filtered.append(item)

        self._filtered_queue = filtered
        self._populate_queue_table()

        total_cola = int(self._summary.get("total_cola_sin_limite", 0) or 0)
        if len(self._raw_queue) >= QUEUE_LIMIT and total_cola > len(self._raw_queue):
            self._set_banner(
                "warning",
                f"Mostrando {self._fmt_int(len(self._raw_queue))} de {self._fmt_int(total_cola)} lineas en cola. "
                "Ajusta el rango de fechas para trabajar el resto.",
            )
        else:
            self._set_banner(None, "")

        self._refresh_mode_buttons()
        self.lbl_queue_meta.setText(
            f"{self._fmt_int(len(self._filtered_queue))} visible(s) | {QUEUE_MODE_LABELS.get(self._queue_mode, 'Todos')}"
        )

    def _populate_queue_table(self) -> None:
        current_key = self._selected_key
        self.queue_table.setRowCount(len(self._filtered_queue))
        for row_idx, item in enumerate(self._filtered_queue):
            key = self._item_key(item)
            date_text = self._fmt_date(item.get("fecha_envio"))
            code_item = QTableWidgetItem(f"{item.get('codigo_oc', '')} · #{item.get('correlativo', 0)}")
            code_item.setData(Qt.ItemDataRole.UserRole, key)
            code_item.setToolTip(
                "\n".join(
                    filter(
                        None,
                        [
                            f"Fecha: {date_text}" if date_text else "",
                            f"Tipo: {item.get('tipo_oc', '')}",
                            f"Cliente SAP: {item.get('cliente_sap_sugerido', '')}",
                        ],
                    )
                )
            )

            buyer_text = item.get("nombre_organismo", "") or "-"
            if item.get("cartera"):
                buyer_text = f"{buyer_text} · {item['cartera']}"
            buyer_item = QTableWidgetItem(buyer_text)
            buyer_item.setToolTip(
                "\n".join(
                    filter(
                        None,
                        [
                            item.get("nombre_organismo", "") or "",
                            f"Cliente SAP: {item.get('cliente_sap_sugerido', '')}" if item.get("cliente_sap_sugerido") else "",
                            f"Cartera: {item.get('cartera', '')}" if item.get("cartera") else "",
                        ],
                    )
                )
            )

            detail_text = (item.get("especificacion_comprador") or item.get("producto") or "-").replace("\r", " ").replace(
                "\n", " "
            )
            detail_item = QTableWidgetItem(detail_text)
            detail_item.setToolTip(
                "\n\n".join(filter(None, [item.get("especificacion_comprador", ""), item.get("producto", "")]))
            )

            suggestion_item = QTableWidgetItem(self._queue_suggestion_text(item))
            suggestion_item.setToolTip(self._queue_suggestion_tooltip(item))

            state_item = QTableWidgetItem(self._queue_state_text(item))
            total_item = QTableWidgetItem(self._fmt_money(item.get("total", 0)))
            total_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            for col, table_item in enumerate([code_item, buyer_item, detail_item, suggestion_item, state_item, total_item]):
                table_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                if col == 4:
                    self._apply_state_colors(table_item, item)
                self.queue_table.setItem(row_idx, col, table_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)
            suggestion = item.get("sugerencia_principal")
            if self._is_pending(item) and suggestion:
                btn_accept = QPushButton("Aceptar")
                btn_accept.setObjectName("PrimaryButton")
                btn_accept.setToolTip(
                    f"Acepta {suggestion.get('itemcode_sap', '')} con {round(float(suggestion.get('score', 0)) * 100)}%."
                )
                btn_accept.clicked.connect(
                    lambda _checked=False, row_key=key, sug=dict(suggestion): self._accept_row_suggestion(row_key, sug)
                )
                action_layout.addWidget(btn_accept)
            else:
                placeholder = QLabel("—")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                placeholder.setObjectName("PageSubtitle")
                action_layout.addWidget(placeholder)
            action_layout.addStretch(1)
            self.queue_table.setCellWidget(row_idx, 6, action_widget)

        self._restore_queue_selection(current_key)
        self.queue_table.resizeRowsToContents()

    def _restore_queue_selection(self, current_key: tuple[str, int] | None) -> None:
        if not self._filtered_queue:
            self._selected_key = None
            self._clear_detail_panel()
            self.queue_table.clearSelection()
            return

        visible_keys = {self._item_key(row) for row in self._filtered_queue}
        target_key = current_key if current_key in visible_keys else self._item_key(self._filtered_queue[0])
        for idx, item in enumerate(self._filtered_queue):
            if self._item_key(item) == target_key:
                self.queue_table.selectRow(idx)
                self._selected_key = target_key
                self._load_detail_from_item(item)
                return

    def _handle_queue_selection(self) -> None:
        row = self.queue_table.currentRow()
        if row < 0 or row >= len(self._filtered_queue):
            self._clear_detail_panel()
            return
        item = self._filtered_queue[row]
        self._selected_key = self._item_key(item)
        self._load_detail_from_item(item)

    def _load_detail_from_item(self, item: dict[str, Any]) -> None:
        self.lbl_selected_meta.setText(f"{item.get('codigo_oc', '')} · linea {item.get('correlativo', 0)}")
        self.ctx_labels["oc"].setText(f"{item.get('codigo_oc', '')} · {self._fmt_date(item.get('fecha_envio'))}")
        self.ctx_labels["organismo"].setText(item.get("nombre_organismo", "") or "-")
        detail_text = (item.get("especificacion_comprador") or item.get("producto") or "-").replace("\r", " ").replace(
            "\n", " "
        )
        self.ctx_labels["detalle"].setText(detail_text)
        self.ctx_labels["detalle"].setToolTip(
            "\n\n".join(filter(None, [item.get("especificacion_comprador", ""), item.get("producto", "")]))
        )
        self.ctx_labels["estado"].setText(
            " / ".join(filter(None, [item.get("estado_interno", "") or "", self._queue_state_text(item)])) or "-"
        )
        self.ctx_labels["rut"].setText(item.get("rut_unidad", "") or "-")
        self.ctx_labels["cantidad"].setText(self._fmt_number(item.get("cantidad", 0)))
        self.ctx_labels["total"].setText(self._fmt_money(item.get("total", 0)))
        self.ctx_labels["asignacion"].setText(self._queue_suggestion_text(item))
        self.btn_clear.setEnabled(bool(item.get("itemcode_sap")))

        self._load_suggestions(item)

    def _load_suggestions(self, item: dict[str, Any]) -> None:
        suggestions = review_service.get_line_suggestions(item["codigo_oc"], item["correlativo"], max_results=5)
        self.lbl_suggestions_meta.setText(
            f"{self._fmt_int(len(suggestions))} sugerencia(s) disponibles para la linea activa."
        )
        self.suggestions_table.setRowCount(len(suggestions))
        for row_idx, suggestion in enumerate(suggestions):
            stars = int(suggestion.get("estrellas", 1) or 1)
            stars_text = "★" * max(1, stars) + "☆" * max(0, 5 - stars)
            confidence_item = QTableWidgetItem(stars_text)
            confidence_item.setToolTip(f"{round(float(suggestion.get('score', 0)) * 100)}% de confianza")
            itemcode_item = QTableWidgetItem(suggestion.get("itemcode_sap", ""))
            desc_item = QTableWidgetItem(suggestion.get("descripcion_sap", ""))
            desc_item.setToolTip(
                "\n".join(
                    filter(
                        None,
                        [
                            suggestion.get("descripcion_sap", ""),
                            f"Match historico: {suggestion.get('descripcion_match', '')}" if suggestion.get("descripcion_match") else "",
                        ],
                    )
                )
            )
            uso_item = QTableWidgetItem(self._fmt_int(suggestion.get("frecuencia", 0)))

            for col, table_item in enumerate([confidence_item, itemcode_item, desc_item, uso_item]):
                table_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.suggestions_table.setItem(row_idx, col, table_item)

            btn = QPushButton("Aceptar")
            btn.setObjectName("PrimaryButton")
            btn.clicked.connect(
                lambda _checked=False, sug=dict(suggestion): self._assign_selected_item(
                    sug["itemcode_sap"],
                    sug.get("descripcion_sap", ""),
                    "sugerencia",
                )
            )
            self.suggestions_table.setCellWidget(row_idx, 4, btn)

    def _run_manual_search(self) -> None:
        query = self.manual_search_input.text().strip()
        if not query:
            self.lbl_search_results.setText("Escribe algo para buscar en la maestra.")
            self.search_results_table.setRowCount(0)
            return

        results = review_service.search_maestra_items(query, limit=15)
        self.lbl_search_results.setText(f"{self._fmt_int(len(results))} resultado(s) verificados.")
        self.search_results_table.setRowCount(len(results))
        for row_idx, result in enumerate(results):
            itemcode = result.get("itemcode_sap", "")
            desc = result.get("descripcion_sap", "")
            itemcode_item = QTableWidgetItem(itemcode)
            desc_item = QTableWidgetItem(desc)
            desc_item.setToolTip(desc)
            itemcode_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            desc_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.search_results_table.setItem(row_idx, 0, itemcode_item)
            self.search_results_table.setItem(row_idx, 1, desc_item)
            btn = QPushButton("Asignar")
            btn.clicked.connect(
                lambda _checked=False, code=itemcode, description=desc: self._assign_selected_item(
                    code,
                    description,
                    "manual",
                )
            )
            self.search_results_table.setCellWidget(row_idx, 2, btn)

    def _handle_search_result_double_click(self, item: QTableWidgetItem) -> None:
        row = item.row()
        code_item = self.search_results_table.item(row, 0)
        desc_item = self.search_results_table.item(row, 1)
        if not code_item or not desc_item:
            return
        self._assign_selected_item(code_item.text(), desc_item.text(), "manual")

    def _accept_row_suggestion(self, row_key: tuple[str, int], suggestion: dict[str, Any]) -> None:
        row = self._find_row(row_key)
        if not row:
            return
        self._selected_key = row_key
        self._assign_item(row, suggestion["itemcode_sap"], suggestion.get("descripcion_sap", ""), "sugerencia")

    def _assign_selected_item(self, itemcode: str, descripcion: str, origen: str) -> None:
        row = self._current_selected_row()
        if not row:
            QMessageBox.information(self, "Estadisticas", "Selecciona una linea antes de asignar.")
            return
        self._assign_item(row, itemcode, descripcion, origen)

    def _assign_item(self, row: dict[str, Any], itemcode: str, descripcion: str, origen: str) -> None:
        try:
            review_service.assign_itemcode(
                row["codigo_oc"],
                int(row["correlativo"]),
                itemcode,
                descripcion,
                origen=origen,
            )
        except Exception as exc:  # pragma: no cover - defensivo
            QMessageBox.critical(self, "Estadisticas", f"No se pudo asignar el itemcode.\n\n{exc}")
            return

        self._apply_assignment_locally(self._item_key(row), itemcode, descripcion, origen)

    def _clear_selected_assignment(self) -> None:
        row = self._current_selected_row()
        if not row:
            return

        try:
            review_service.clear_itemcode(row["codigo_oc"], int(row["correlativo"]))
        except Exception as exc:  # pragma: no cover - defensivo
            QMessageBox.critical(self, "Estadisticas", f"No se pudo limpiar la asignacion.\n\n{exc}")
            return

        self._apply_clear_locally(self._item_key(row))

    def _apply_assignment_locally(self, row_key: tuple[str, int], itemcode: str, descripcion: str, origen: str) -> None:
        row = self._find_row(row_key)
        if not row:
            return

        prev_state = row.get("estado_homologacion") or "pendiente"
        had_itemcode = bool(row.get("itemcode_sap"))
        was_pending = prev_state == "pendiente" or not had_itemcode
        had_suggestion = row.get("sugerencia_principal") is not None
        total = float(row.get("total", 0) or 0)

        row["itemcode_sap"] = itemcode
        row["descripcion_sap"] = descripcion
        row["estado_homologacion"] = "sugerido" if origen == "sugerencia" else "manual"

        if origen == "sugerencia":
            self._raw_queue = [q for q in self._raw_queue if self._item_key(q) != row_key]

        if was_pending:
            self._summary["lineas_pendientes"] = max(0, int(self._summary.get("lineas_pendientes", 0)) - 1)
            self._summary["lineas_resueltas"] = min(
                int(self._summary.get("total_lineas", 0)),
                int(self._summary.get("lineas_resueltas", 0)) + 1,
            )
            self._summary["monto_resuelto"] = float(self._summary.get("monto_resuelto", 0) or 0) + total
            key = "pendientes_con_sugerencia" if had_suggestion else "pendientes_sin_sugerencia"
            self._summary[key] = max(0, int(self._summary.get(key, 0)) - 1)
            self._session_resolved += 1

        self._summary["lineas_manuales"] = max(
            0,
            int(self._summary.get("lineas_manuales", 0))
            - (1 if prev_state == "manual" else 0)
            + (1 if origen == "manual" else 0),
        )
        self._summary["lineas_sugeridas"] = max(
            0,
            int(self._summary.get("lineas_sugeridas", 0))
            - (1 if prev_state == "sugerido" else 0)
            + (1 if origen == "sugerencia" else 0),
        )
        if origen == "sugerencia":
            self._summary["total_cola_sin_limite"] = max(
                0, int(self._summary.get("total_cola_sin_limite", 0)) - 1
            )

        self._refresh_summary_after_queue_change()
        self._refresh_summary()
        self._apply_filters()

    def _apply_clear_locally(self, row_key: tuple[str, int]) -> None:
        row = self._find_row(row_key)
        if not row:
            return

        prev_state = row.get("estado_homologacion") or "pendiente"
        had_itemcode = bool(row.get("itemcode_sap"))
        total = float(row.get("total", 0) or 0)

        row["itemcode_sap"] = None
        row["descripcion_sap"] = None
        row["estado_homologacion"] = "pendiente"

        if had_itemcode:
            self._summary["lineas_pendientes"] = int(self._summary.get("lineas_pendientes", 0)) + 1
            self._summary["lineas_resueltas"] = max(0, int(self._summary.get("lineas_resueltas", 0)) - 1)
            self._summary["monto_resuelto"] = max(
                0.0, float(self._summary.get("monto_resuelto", 0) or 0) - total
            )
            key = "pendientes_con_sugerencia" if row.get("sugerencia_principal") else "pendientes_sin_sugerencia"
            self._summary[key] = int(self._summary.get(key, 0)) + 1

        self._summary["lineas_manuales"] = max(
            0,
            int(self._summary.get("lineas_manuales", 0)) - (1 if prev_state == "manual" else 0),
        )
        self._summary["lineas_sugeridas"] = max(
            0,
            int(self._summary.get("lineas_sugeridas", 0)) - (1 if prev_state == "sugerido" else 0),
        )

        self._refresh_summary_after_queue_change()
        self._refresh_summary()
        self._apply_filters()

    def _refresh_summary_after_queue_change(self) -> None:
        self._summary["cola_revision"] = len(self._raw_queue)
        self._summary["ocs_por_revisar"] = len({row["codigo_oc"] for row in self._raw_queue})
        total_lineas = max(1, int(self._summary.get("total_lineas", 0) or 0))
        total_monto = max(1.0, float(self._summary.get("monto_total", 0) or 0.0))
        self._summary["cobertura_lineas_pct"] = round(
            (float(self._summary.get("lineas_resueltas", 0) or 0) / total_lineas) * 100, 1
        )
        self._summary["cobertura_monto_pct"] = round(
            (float(self._summary.get("monto_resuelto", 0) or 0) / total_monto) * 100, 1
        )

    def _current_selected_row(self) -> dict[str, Any] | None:
        if not self._selected_key:
            return None
        return self._find_row(self._selected_key)

    def _find_row(self, row_key: tuple[str, int]) -> dict[str, Any] | None:
        for row in self._raw_queue:
            if self._item_key(row) == row_key:
                return row
        return None

    def _set_queue_mode(self, mode: str) -> None:
        if mode not in QUEUE_MODE_LABELS:
            return
        self._queue_mode = mode
        self._apply_filters()

    def _refresh_mode_buttons(self) -> None:
        for mode, button in self._mode_buttons.items():
            button.setProperty("quickActive", mode == self._queue_mode)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _apply_quick_range(self, key: str, days: int, auto_refresh: bool = True) -> None:
        today = date.today()
        start = today if days == 0 else today - timedelta(days=max(days - 1, 0))
        self.date_desde.setDate(QDate(start.year, start.month, start.day))
        self.date_hasta.setDate(QDate(today.year, today.month, today.day))
        self._active_quick = key
        self._refresh_quick_buttons()
        if auto_refresh:
            self.refresh()

    def _clear_quick_range(self) -> None:
        if self._active_quick is None:
            return
        self._active_quick = None
        self._refresh_quick_buttons()

    def _refresh_quick_buttons(self) -> None:
        for key, button in self._quick_buttons.items():
            button.setProperty("quickActive", key == self._active_quick)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _set_banner(self, tone: str | None, text: str) -> None:
        if not text:
            self.banner.setVisible(False)
            self.banner.clear()
            self.banner.setStyleSheet("")
            return
        tone_styles = {
            "warning": "background-color: #3A2A08; color: #FCD34D; border: 1px solid #5A3B12; border-radius: 8px; padding: 7px 9px;",
            "info": "background-color: #132C47; color: #93C5FD; border: 1px solid #1E466F; border-radius: 8px; padding: 7px 9px;",
        }
        self.banner.setText(text)
        self.banner.setStyleSheet(tone_styles.get(tone or "info", ""))
        self.banner.setVisible(True)

    def _clear_detail_panel(self) -> None:
        self.lbl_selected_meta.setText("Selecciona una linea para revisar.")
        self.lbl_suggestions_meta.setText("Sin linea seleccionada.")
        self.lbl_search_results.setText("Sin busqueda reciente.")
        self.suggestions_table.setRowCount(0)
        self.search_results_table.setRowCount(0)
        self.btn_clear.setEnabled(False)
        for label in self.ctx_labels.values():
            label.setText("-")

    def _queue_state_text(self, item: dict[str, Any]) -> str:
        state = item.get("estado_homologacion") or "pendiente"
        if state == "manual":
            return "Revisada manual"
        if state == "sugerido":
            return "Aceptada del motor"
        return "Pendiente"

    def _queue_suggestion_text(self, item: dict[str, Any]) -> str:
        if item.get("itemcode_sap"):
            prefix = "Manual" if (item.get("estado_homologacion") == "manual") else "Sugerido"
            desc = item.get("descripcion_sap") or ""
            if desc:
                return f"{prefix}: {item['itemcode_sap']} · {desc}"
            return f"{prefix}: {item['itemcode_sap']}"
        suggestion = item.get("sugerencia_principal")
        if suggestion:
            pct = round(float(suggestion.get("score", 0)) * 100)
            return f"{suggestion.get('itemcode_sap', '')} · {pct}%"
        return "Sin sugerencia"

    def _queue_suggestion_tooltip(self, item: dict[str, Any]) -> str:
        if item.get("itemcode_sap"):
            return "\n".join(filter(None, [item.get("itemcode_sap", ""), item.get("descripcion_sap", "") or ""]))
        suggestion = item.get("sugerencia_principal")
        if not suggestion:
            return "Sin sugerencia automatica."
        lines = [
            suggestion.get("itemcode_sap", ""),
            suggestion.get("descripcion_sap", "") or "",
            f"Confianza: {round(float(suggestion.get('score', 0)) * 100)}%",
        ]
        if suggestion.get("descripcion_match"):
            lines.append(f"Match historico: {suggestion['descripcion_match']}")
        return "\n".join(filter(None, lines))

    def _apply_state_colors(self, item_widget: QTableWidgetItem, row: dict[str, Any]) -> None:
        state = row.get("estado_homologacion") or "pendiente"
        if state == "manual":
            item_widget.setForeground(Qt.GlobalColor.yellow)
        elif state == "sugerido":
            item_widget.setForeground(Qt.GlobalColor.green)
        else:
            item_widget.setForeground(Qt.GlobalColor.white)

    @staticmethod
    def _is_pending(item: dict[str, Any]) -> bool:
        return (item.get("estado_homologacion") or "pendiente") == "pendiente" or not item.get("itemcode_sap")

    @staticmethod
    def _item_key(item: dict[str, Any]) -> tuple[str, int]:
        return str(item.get("codigo_oc", "")), int(item.get("correlativo", 0))

    @staticmethod
    def _style_table(table: QTableWidget, row_height: int = 36) -> None:
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(row_height)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #22304A;
                border-radius: 8px;
                background-color: #0F172A;
                selection-background-color: #162033;
                selection-color: #E5EEF9;
                alternate-background-color: #111827;
            }
            QTableWidget::item {
                padding: 3px 6px;
            }
            QHeaderView::section {
                background-color: #111827;
                color: #8FA3BF;
                border: none;
                border-bottom: 1px solid #22304A;
                padding: 5px 6px;
                font-size: 10px;
                font-weight: 600;
            }
            """
        )

    @staticmethod
    def _build_strip(title: str, value: str, helper: str) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("SectionEyebrow")
        value_label = QLabel(value)
        value_label.setObjectName("StripValue")
        value_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #E5EEF9;")
        helper_label = QLabel(helper)
        helper_label.setObjectName("MetricCaption")
        helper_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(helper_label)
        return card

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
    def _date_to_iso(qdate: QDate) -> str:
        return f"{qdate.year():04d}-{qdate.month():02d}-{qdate.day():02d}"

    @staticmethod
    def _fmt_int(value: Any) -> str:
        try:
            return f"{int(value):,}".replace(",", ".")
        except Exception:
            return "0"

    @staticmethod
    def _fmt_number(value: Any) -> str:
        try:
            number = float(value or 0)
        except Exception:
            return "0"
        if number.is_integer():
            return f"{int(number):,}".replace(",", ".")
        return f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    @staticmethod
    def _fmt_money(value: Any) -> str:
        try:
            amount = float(value or 0)
        except Exception:
            amount = 0.0
        return f"${amount:,.0f}".replace(",", ".")

    @staticmethod
    def _fmt_date(value: Any) -> str:
        if not value:
            return ""
        text = str(value)
        return text.split("T", 1)[0]
