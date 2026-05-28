"""Bandeja principal de OCs para la nueva shell Qt."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QSizePolicy,
)

from app.config import get_config_dir
from app.models.linea_oc import LineaOC
from app.models.orden_compra import OrdenCompra
from app.repositories.oc_repository import (
    actualizar_estado,
    get_all_ocs,
    get_distinct_estados_mp,
    get_distinct_tipos,
    get_lineas,
    guardar_notas,
    marcar_ingresada,
)
from app.services.cartera_service import get_cartera_service
from app_qt.models.lineas_table_model import LineasTableModel
from app_qt.models.oc_table_model import OcTableModel, OcTableRow
from app_qt.models.oc_table_proxy import OcTableProxyModel
from app_qt.widgets.badge_delegate import BadgeDelegate


SAP_COLUMN_SPECS = [
    {"id": "correlativo", "label": "#", "width": 42, "visible": False, "copy": False},
    {"id": "codigo_mp", "label": "Cod. MP", "width": 88, "visible": True, "copy": False},
    {"id": "descripcion", "label": "Descripcion OC", "width": 320, "visible": True, "copy": False},
    {"id": "itemcode_sap", "label": "ItemCode SAP", "width": 96, "visible": True, "copy": True},
    {"id": "descripcion_sap", "label": "Descripcion SAP", "width": 320, "visible": True, "copy": True},
    {"id": "cantidad", "label": "Cant. OC", "width": 70, "visible": True, "copy": False},
    {"id": "cantidad_sap", "label": "Cant. SAP", "width": 72, "visible": False, "copy": True},
    {"id": "factor_empaque", "label": "F.Emp", "width": 58, "visible": False, "copy": False},
    {"id": "precio_neto", "label": "Precio Neto", "width": 92, "visible": False, "copy": False},
    {"id": "precio_sap", "label": "Precio SAP", "width": 92, "visible": False, "copy": True},
    {"id": "unidad", "label": "Unidad", "width": 68, "visible": False, "copy": False},
    {"id": "total", "label": "Total", "width": 84, "visible": True, "copy": False},
    {"id": "estado_homologacion", "label": "Estado", "width": 92, "visible": True, "copy": False},
]
SAP_COLUMN_LOOKUP = {item["id"]: item for item in SAP_COLUMN_SPECS}
SAP_COLUMN_PREFS_FILE = get_config_dir() / "sap_column_prefs_qt.json"


def _default_sap_column_order() -> list[str]:
    return [item["id"] for item in SAP_COLUMN_SPECS]


def _default_sap_column_visible() -> dict[str, bool]:
    return {item["id"]: bool(item["visible"]) for item in SAP_COLUMN_SPECS}


def _default_sap_column_copy() -> dict[str, bool]:
    return {item["id"]: bool(item["copy"]) for item in SAP_COLUMN_SPECS}


def _load_sap_column_prefs() -> tuple[list[str], dict[str, bool], dict[str, bool]]:
    order = _default_sap_column_order()
    visible = _default_sap_column_visible()
    copy = _default_sap_column_copy()
    try:
        if SAP_COLUMN_PREFS_FILE.exists():
            data = json.loads(SAP_COLUMN_PREFS_FILE.read_text(encoding="utf-8"))
            stored_order = [value for value in data.get("order", []) if value in SAP_COLUMN_LOOKUP]
            for column_id in order:
                if column_id not in stored_order:
                    stored_order.append(column_id)
            order = stored_order
            visible.update({key: bool(value) for key, value in data.get("visible", {}).items() if key in SAP_COLUMN_LOOKUP})
            copy.update({key: bool(value) for key, value in data.get("copy", {}).items() if key in SAP_COLUMN_LOOKUP})
    except Exception:
        pass
    return order, visible, copy


def _save_sap_column_prefs(order: list[str], visible: dict[str, bool], copy: dict[str, bool]) -> None:
    payload = {"order": order, "visible": visible, "copy": copy}
    SAP_COLUMN_PREFS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SapColumnConfigDialog(QDialog):
    """Dialogo simple para ordenar columnas SAP y definir visibilidad/copia."""

    def __init__(
        self,
        order: list[str],
        visible: dict[str, bool],
        copy: dict[str, bool],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._order = list(order)
        self._visible = dict(visible)
        self._copy = dict(copy)
        self.setWindowTitle("Ajustes SAP")
        self.resize(520, 560)
        self.setMinimumSize(500, 520)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel("Columnas SAP")
        title.setObjectName("CardTitle")
        subtitle = QLabel(
            "Define el orden, que columnas se ven en la tabla y cuales se incluyen al copiar para SAP."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addSpacing(56)
        lbl_name = QLabel("Columna")
        lbl_name.setObjectName("SectionEyebrow")
        header.addWidget(lbl_name, 1)
        lbl_visible = QLabel("Ver")
        lbl_visible.setObjectName("SectionEyebrow")
        header.addWidget(lbl_visible, 0)
        lbl_copy = QLabel("Copiar")
        lbl_copy.setObjectName("SectionEyebrow")
        header.addWidget(lbl_copy, 0)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._rows_host = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        scroll.setWidget(self._rows_host)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)
        btn_reset = QPushButton("Restaurar")
        btn_reset.clicked.connect(self._reset_defaults)
        footer.addWidget(btn_reset, 0)
        footer.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons, 0)
        root.addLayout(footer)

        self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, column_id in enumerate(self._order):
            spec = SAP_COLUMN_LOOKUP[column_id]
            row = QFrame()
            row.setObjectName("InsetCard")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(8)

            move_up = QPushButton("▲")
            move_up.setMinimumWidth(28)
            move_up.clicked.connect(lambda _checked=False, idx=index: self._move(idx, -1))
            layout.addWidget(move_up, 0)

            move_down = QPushButton("▼")
            move_down.setMinimumWidth(28)
            move_down.clicked.connect(lambda _checked=False, idx=index: self._move(idx, 1))
            layout.addWidget(move_down, 0)

            label = QLabel(spec["label"])
            label.setObjectName("CardBody")
            layout.addWidget(label, 1)

            visible_box = QCheckBox()
            visible_box.setChecked(self._visible.get(column_id, True))
            visible_box.stateChanged.connect(
                lambda _state, key=column_id, box=visible_box: self._visible.__setitem__(key, box.isChecked())
            )
            layout.addWidget(visible_box, 0)

            copy_box = QCheckBox()
            copy_box.setChecked(self._copy.get(column_id, False))
            copy_box.stateChanged.connect(
                lambda _state, key=column_id, box=copy_box: self._copy.__setitem__(key, box.isChecked())
            )
            layout.addWidget(copy_box, 0)

            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch(1)

    def _move(self, index: int, delta: int) -> None:
        new_index = index + delta
        if new_index < 0 or new_index >= len(self._order):
            return
        self._order[index], self._order[new_index] = self._order[new_index], self._order[index]
        self._rebuild_rows()

    def _reset_defaults(self) -> None:
        self._order = _default_sap_column_order()
        self._visible = _default_sap_column_visible()
        self._copy = _default_sap_column_copy()
        self._rebuild_rows()

    def get_prefs(self) -> tuple[list[str], dict[str, bool], dict[str, bool]]:
        return list(self._order), dict(self._visible), dict(self._copy)


class OcListPage(QWidget):
    page_title = "Ordenes de compra"
    page_subtitle = "Bandeja principal desktop con tabla densa, filtros compactos y detalle inferior siempre visible."
    page_eyebrow = "Modulo prioritario"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[OcTableRow] = []
        self._sap_col_order, self._sap_col_visible, self._sap_col_copy = _load_sap_column_prefs()
        self._selected_row: OcTableRow | None = None
        self._selected_oc: OrdenCompra | None = None
        self._selected_line: LineaOC | None = None
        self._loading_detail = False
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        filters_card = QFrame()
        filters_card.setObjectName("PageCard")
        filters_layout = QVBoxLayout(filters_card)
        filters_layout.setContentsMargins(10, 8, 10, 8)
        filters_layout.setSpacing(4)

        row = QGridLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setHorizontalSpacing(6)
        row.setVerticalSpacing(4)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por codigo, cliente, estado o cliente SAP...")
        self.search_input.textChanged.connect(self._apply_filters)

        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["Todos", "Pendiente", "Nueva", "Revisada", "Lista para SAP", "Ingresada", "Con error"])
        self.estado_combo.currentTextChanged.connect(self._apply_filters)

        self.estado_mp_combo = QComboBox()
        self.estado_mp_combo.currentTextChanged.connect(self._apply_filters)

        self.tipo_combo = QComboBox()
        self.tipo_combo.currentTextChanged.connect(self._apply_filters)

        self.cartera_combo = QComboBox()
        self.cartera_combo.currentTextChanged.connect(self._apply_filters)

        refresh_button = QPushButton("Actualizar")
        refresh_button.setObjectName("PrimaryButton")
        refresh_button.clicked.connect(self.refresh)
        refresh_button.setMinimumWidth(96)

        for column in range(6):
            row.setColumnStretch(column, 1)
        row.setColumnStretch(0, 2)
        row.setColumnStretch(1, 2)

        row.addWidget(self._labeled_field("Busqueda", self.search_input), 0, 0, 1, 2)
        row.addWidget(self._labeled_field("Estado interno", self.estado_combo), 0, 2)
        row.addWidget(self._labeled_field("Estado MP", self.estado_mp_combo), 0, 3)
        row.addWidget(self._labeled_field("Tipo", self.tipo_combo), 0, 4)
        row.addWidget(self._labeled_field("Cartera", self.cartera_combo), 0, 5)
        row.addWidget(refresh_button, 0, 6)

        filters_layout.addLayout(row)
        root.addWidget(filters_card)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(6)

        self.splitter.addWidget(self._build_top_table_card())
        self.splitter.addWidget(self._build_detail_card())
        self.splitter.setSizes([300, 420])

        root.addWidget(self.splitter, 1)

    def _build_top_table_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        header_row = QHBoxLayout()
        title = QLabel("Bandeja principal")
        title.setObjectName("CardTitle")
        self.lbl_table_meta = QLabel("Sin datos")
        self.lbl_table_meta.setObjectName("PageSubtitle")
        self.lbl_table_meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.lbl_table_meta)
        layout.addLayout(header_row)

        self.table_model = OcTableModel([])
        self.table_proxy = OcTableProxyModel(self)
        self.table_proxy.setSourceModel(self.table_model)
        self.table_proxy.setDynamicSortFilter(True)

        self.table = QTableView()
        self.table.setModel(self.table_proxy)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(True)
        self.table.setGridStyle(Qt.PenStyle.SolidLine)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setFixedHeight(26)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.setStyleSheet(self._dense_table_stylesheet())
        self.table.selectionModel().selectionChanged.connect(self._handle_selection_change)
        layout.addWidget(self.table, 1)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(52)
        self.table.setColumnWidth(1, 132)
        self.table.setColumnWidth(4, 104)
        self.table.setColumnWidth(7, 138)
        self.table.setColumnWidth(8, 62)
        self.table.setColumnWidth(9, 96)
        self.table.setItemDelegateForColumn(
            0,
            BadgeDelegate(
                {
                    "Pendiente": ("#3A2A08", "#FBBF24"),
                    "Nueva": ("#132C47", "#38BDF8"),
                    "Revisada": ("#2A2147", "#C4B5FD"),
                    "Lista para SAP": ("#432313", "#FB923C"),
                    "Ingresada": ("#103226", "#34D399"),
                    "Con error": ("#421A1A", "#F87171"),
                },
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.table,
            ),
        )
        self.table.setItemDelegateForColumn(
            6,
            BadgeDelegate(
                {
                    "CM": ("#2B2152", "#C4B5FD"),
                    "SE": ("#1F334B", "#93C5FD"),
                    "OC": ("#3B2A10", "#FCD34D"),
                    "AG": ("#1D3A33", "#6EE7B7"),
                },
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.table,
            ),
        )
        self.table.setItemDelegateForColumn(
            7,
            BadgeDelegate(
                {
                    "Enviada a proveedor": ("#1E324A", "#93C5FD"),
                    "Aceptada": ("#103226", "#6EE7B7"),
                    "Nueva Orden de Compra": ("#3A2A08", "#FBBF24"),
                    "Cancelada": ("#421A1A", "#FCA5A5"),
                    "Recepcion Conforme": ("#1D3A33", "#5EEAD4"),
                },
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.table,
            ),
        )
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)

        return card

    def _build_detail_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)

        self.lbl_detail_title = QLabel("Detalle de OC")
        self.lbl_detail_title.hide()
        self.lbl_detail_hint = QLabel("Selecciona una fila para ver contexto y lineas.")
        self.lbl_detail_hint.hide()

        self.lbl_oc_codigo = self._make_value_label("--")
        self.lbl_oc_cliente = self._make_value_label("Sin seleccion")
        self.lbl_oc_fecha = self._make_value_label("--")
        self.lbl_oc_cliente_sap = self._make_value_label("--")
        self.lbl_oc_cartera = self._make_value_label("--")
        self.lbl_oc_total = self._make_value_label("$0")
        self.lbl_oc_tipo_chip = self._make_chip_label("--")
        self.lbl_oc_estado_mp_chip = self._make_chip_label("--")
        self.lbl_oc_notas_estado = QLabel("Sin cambios pendientes")
        self.lbl_oc_notas_estado.setObjectName("PageSubtitle")
        self.lbl_oc_cliente_sap.setWordWrap(False)
        self.lbl_oc_codigo.setWordWrap(False)
        self.lbl_oc_cliente_sap.setStyleSheet("font-size: 12px; font-weight: 700; color: #5EEAD4;")
        self.lbl_oc_codigo.setStyleSheet("font-size: 12px; font-weight: 700; color: #BFDBFE;")

        action_card = QFrame()
        action_card.setObjectName("InsetCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(8, 6, 8, 6)
        action_layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        cliente_sap_tag = self._make_chip_label("CLIENTE SAP")
        top_row.addWidget(cliente_sap_tag, 0)
        top_row.addWidget(self.lbl_oc_cliente_sap, 0)

        self.btn_copy_cliente_sap = self._make_ghost_button("Copiar")
        self.btn_copy_cliente_sap.clicked.connect(
            lambda: self._copy_text_value(self.lbl_oc_cliente_sap.text(), "Cliente SAP copiado.")
        )
        top_row.addWidget(self.btn_copy_cliente_sap, 0)

        sep = QLabel("|")
        sep.setObjectName("PageSubtitle")
        top_row.addWidget(sep, 0)
        top_row.addWidget(self.lbl_oc_codigo, 0)

        self.btn_copy_codigo = self._make_ghost_button("Copiar codigo")
        self.btn_copy_codigo.clicked.connect(
            lambda: self._copy_text_value(self.lbl_oc_codigo.text(), "Codigo OC copiado.")
        )
        top_row.addWidget(self.btn_copy_codigo, 0)
        top_row.addWidget(self.lbl_oc_tipo_chip, 0)
        top_row.addWidget(self.lbl_oc_estado_mp_chip, 0)
        top_row.addStretch(1)
        top_row.addWidget(self.lbl_oc_notas_estado, 0)

        self.estado_detail_combo = QComboBox()
        self.estado_detail_combo.addItems(["Pendiente", "Nueva", "Revisada", "Lista para SAP", "Ingresada", "Con error"])
        self.estado_detail_combo.currentTextChanged.connect(self._on_estado_changed)
        self.estado_detail_combo.setMinimumWidth(118)

        self.btn_copy_sap = QPushButton("Copiar a SAP")
        self.btn_copy_sap.setObjectName("PrimaryButton")
        self.btn_copy_sap.clicked.connect(self._copy_sap)
        self.btn_copy_sap.setMinimumWidth(110)
        self.btn_copy_sap.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.btn_sap_settings = QPushButton("Ajustes SAP")
        self.btn_sap_settings.clicked.connect(self._show_sap_settings)
        self.btn_sap_settings.setMinimumWidth(104)

        self.btn_export_excel = QPushButton("Exportar Excel")
        self.btn_export_excel.clicked.connect(self._export_excel)
        self.btn_export_excel.setMinimumWidth(110)

        self.btn_open_portal = QPushButton("Ver portal")
        self.btn_open_portal.clicked.connect(self._open_portal)
        self.btn_open_portal.setMinimumWidth(92)

        self.btn_mark_ingresada = QPushButton("Ingresar en SAP")
        self.btn_mark_ingresada.clicked.connect(self._mark_ingresada)
        self.btn_mark_ingresada.setMinimumWidth(112)
        self.btn_mark_ingresada.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.btn_mark_ingresada.setStyleSheet(
            "background-color:#0E8F62; border:1px solid #0E8F62; color:#F4FFFB; font-weight:700;"
        )

        top_row.addWidget(self.btn_copy_sap, 0)
        top_row.addWidget(self.btn_sap_settings, 0)
        top_row.addWidget(self.btn_export_excel, 0)
        top_row.addWidget(self.btn_open_portal, 0)
        top_row.addWidget(self.btn_mark_ingresada, 0)
        action_layout.addLayout(top_row)

        bottom_row = QGridLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setHorizontalSpacing(8)
        bottom_row.setVerticalSpacing(4)

        bottom_row.addWidget(self._compact_field("Comprador", self.lbl_oc_cliente), 0, 0, 1, 3)
        bottom_row.addWidget(self._compact_field("Fecha envio", self.lbl_oc_fecha), 0, 3)
        bottom_row.addWidget(self._compact_field("Cartera", self.lbl_oc_cartera), 0, 4)
        bottom_row.addWidget(self._compact_field("Total", self.lbl_oc_total), 0, 5)
        bottom_row.addWidget(self._labeled_field("Estado interno", self.estado_detail_combo), 0, 6)

        notes_wrap = QWidget()
        notes_layout = QVBoxLayout(notes_wrap)
        notes_layout.setContentsMargins(0, 0, 0, 0)
        notes_layout.setSpacing(2)
        notes_label = QLabel("Notas internas")
        notes_label.setObjectName("SectionEyebrow")
        self.btn_save_notes = QPushButton("Guardar notas")
        self.btn_save_notes.clicked.connect(self._save_notes)
        self.btn_save_notes.setEnabled(False)
        self.btn_save_notes.setMinimumWidth(100)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Observaciones, seguimiento o contexto para el equipo...")
        self.notes_edit.setFixedHeight(34)
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(notes_label)
        notes_layout.addWidget(self.notes_edit)

        bottom_row.addWidget(notes_wrap, 0, 7, 1, 3)
        bottom_row.addWidget(self.btn_save_notes, 0, 10, 1, 1, Qt.AlignmentFlag.AlignBottom)

        action_layout.addLayout(bottom_row)
        layout.addWidget(action_card)

        lineas_header = QHBoxLayout()
        self.lbl_line_title = QLabel("Lineas de la OC")
        self.lbl_line_title.setObjectName("CardTitle")
        self.lbl_line_meta = QLabel("Sin lineas")
        self.lbl_line_meta.setObjectName("PageSubtitle")
        self.lbl_line_meta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lineas_header.addWidget(self.lbl_line_title)
        lineas_header.addStretch(1)
        lineas_header.addWidget(self.lbl_line_meta)
        layout.addLayout(lineas_header)

        self.lineas_model = LineasTableModel([])
        self.lineas_table = QTableView()
        self.lineas_table.setModel(self.lineas_model)
        self.lineas_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.lineas_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.lineas_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.lineas_table.setAlternatingRowColors(True)
        self.lineas_table.setShowGrid(True)
        self.lineas_table.setGridStyle(Qt.PenStyle.SolidLine)
        self.lineas_table.verticalHeader().setVisible(False)
        self.lineas_table.verticalHeader().setDefaultSectionSize(23)
        self.lineas_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.lineas_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lineas_table.horizontalHeader().setHighlightSections(False)
        self.lineas_table.horizontalHeader().setFixedHeight(26)
        self.lineas_table.setStyleSheet(self._dense_table_stylesheet())
        self.lineas_table.horizontalHeader().setMinimumSectionSize(52)
        for idx, (column_id, _label) in enumerate(self.lineas_model.columns):
            spec = SAP_COLUMN_LOOKUP.get(column_id)
            if spec:
                self.lineas_table.setColumnWidth(idx, int(spec["width"]))
        self.lineas_table.setItemDelegateForColumn(
            12,
            BadgeDelegate(
                {
                    "homologado": ("#103226", "#34D399"),
                    "sugerido": ("#132C47", "#38BDF8"),
                    "manual": ("#2A2147", "#C4B5FD"),
                    "pendiente": ("#3A2A08", "#FBBF24"),
                    "sin_homologacion": ("#421A1A", "#F87171"),
                },
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                self.lineas_table,
            ),
        )
        self.lineas_table.selectionModel().selectionChanged.connect(self._handle_line_selection_change)
        self._apply_line_table_column_prefs()

        layout.addWidget(self.lineas_table, 1)

        self.line_detail_card = QFrame()
        self.line_detail_card.setObjectName("InsetCard")
        line_detail_layout = QVBoxLayout(self.line_detail_card)
        line_detail_layout.setContentsMargins(8, 6, 8, 6)
        line_detail_layout.setSpacing(2)

        self.lbl_line_summary = QLabel("Selecciona una linea para ver el contexto.")
        self.lbl_line_summary.setObjectName("PageSubtitle")
        self.lbl_line_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_line_desc = QLabel("Selecciona una linea para ver la especificacion completa.")
        self.lbl_line_desc.setObjectName("CardBody")
        self.lbl_line_desc.setWordWrap(True)
        self.lbl_line_desc.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_line_desc_sap = QLabel("--")
        self.lbl_line_desc_sap.setObjectName("CardBody")
        self.lbl_line_desc_sap.setWordWrap(False)
        self.lbl_line_desc_sap.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_line_desc_sap.hide()
        line_detail_layout.addWidget(self.lbl_line_summary)
        line_detail_layout.addWidget(self.lbl_line_desc)

        layout.addWidget(self.line_detail_card)

        return card

    def refresh(self) -> None:
        current_code = self._selected_oc.codigo_oc if self._selected_oc else None
        rows = self._load_rows()
        self._rows = rows
        self.table_model.set_rows(rows)
        self._reload_filter_options(rows)
        self._apply_filters()
        if current_code and self._select_oc_by_code(current_code):
            return
        self._select_first_row()

    def _load_rows(self) -> list[OcTableRow]:
        cartera_svc = get_cartera_service()
        rows: list[OcTableRow] = []
        for oc in get_all_ocs():
            cartera = ""
            region = ""
            if oc.cliente_sap_sugerido:
                match = cartera_svc.lookup(oc.cliente_sap_sugerido)
                if match:
                    cartera = match.cartera or ""
                    region = match.region_nombre or ""
            rows.append(OcTableRow(oc=oc, cartera=cartera, region=region))
        return rows

    def _reload_filter_options(self, rows: list[OcTableRow]) -> None:
        self._set_combo_items(self.estado_mp_combo, ["Todos"] + get_distinct_estados_mp())
        self._set_combo_items(self.tipo_combo, ["Todos"] + get_distinct_tipos())
        carteras = sorted({row.cartera for row in rows if row.cartera})
        self._set_combo_items(self.cartera_combo, ["Todas"] + carteras)

    def _set_combo_items(self, combo: QComboBox, values: list[str]) -> None:
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        if current and current in values:
            combo.setCurrentText(current)
        elif values:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _apply_filters(self) -> None:
        self.table_proxy.set_search_text(self.search_input.text())
        self.table_proxy.set_estado(self.estado_combo.currentText())
        self.table_proxy.set_estado_mp(self.estado_mp_combo.currentText())
        self.table_proxy.set_tipo(self.tipo_combo.currentText())
        self.table_proxy.set_cartera(self.cartera_combo.currentText())
        visible = self.table_proxy.rowCount()
        total = self.table_model.rowCount()
        self.lbl_table_meta.setText(f"{visible} visibles de {total} OCs")
        self._select_first_row()

    def _select_first_row(self) -> None:
        if self.table_proxy.rowCount() <= 0:
            self._set_selected_oc(None)
            return
        self.table.selectRow(0)
        index = self.table_proxy.index(0, 0)
        self._update_detail_from_proxy_index(index)

    def _select_oc_by_code(self, codigo_oc: str) -> bool:
        for row in range(self.table_proxy.rowCount()):
            proxy_index = self.table_proxy.index(row, 1)
            source_index = self.table_proxy.mapToSource(proxy_index)
            model_row = self.table_model.row_at(source_index.row())
            if model_row and model_row.oc.codigo_oc == codigo_oc:
                self.table.selectRow(row)
                self._update_detail_from_proxy_index(proxy_index)
                return True
        return False

    def _handle_selection_change(self, *_args) -> None:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            self._set_selected_oc(None)
            return
        self._update_detail_from_proxy_index(indexes[0])

    def _update_detail_from_proxy_index(self, proxy_index) -> None:
        if not proxy_index.isValid():
            self._selected_row = None
            self._set_selected_oc(None)
            return
        source_index = self.table_proxy.mapToSource(proxy_index)
        row = self.table_model.row_at(source_index.row())
        self._selected_row = row
        self._set_selected_oc(row.oc if row else None)

    def _set_selected_oc(self, oc: OrdenCompra | None) -> None:
        self._loading_detail = True
        self._selected_oc = oc
        if oc is None:
            self.lbl_detail_title.setText("Detalle de OC")
            self.lbl_detail_hint.setText("Selecciona una fila para ver contexto y lineas.")
            self.lbl_oc_codigo.setText("--")
            self.lbl_oc_cliente.setText("Sin seleccion")
            self.lbl_oc_fecha.setText("--")
            self.lbl_oc_cliente_sap.setText("--")
            self.lbl_oc_cartera.setText("--")
            self.lbl_oc_total.setText("$0")
            self._apply_badge(self.lbl_oc_tipo_chip, "--", {})
            self._apply_badge(self.lbl_oc_estado_mp_chip, "--", {})
            self.lbl_oc_codigo.setToolTip("")
            self.lbl_oc_cliente.setToolTip("")
            self.lbl_oc_fecha.setToolTip("")
            self.lbl_oc_cliente_sap.setToolTip("")
            self.lbl_oc_cartera.setToolTip("")
            self.lbl_oc_total.setToolTip("")
            self.estado_detail_combo.setCurrentText("Pendiente")
            self.notes_edit.clear()
            self.btn_save_notes.setEnabled(False)
            self.btn_mark_ingresada.setEnabled(False)
            self.btn_copy_sap.setEnabled(False)
            self.btn_copy_cliente_sap.setEnabled(False)
            self.btn_copy_codigo.setEnabled(False)
            self.btn_export_excel.setEnabled(False)
            self.btn_open_portal.setEnabled(False)
            self.btn_sap_settings.setEnabled(False)
            self.lbl_oc_notas_estado.setText("Sin seleccion")
            self.lineas_model.set_rows([])
            self.lbl_line_title.setText("Lineas de la OC")
            self.lbl_line_meta.setText("Sin lineas")
            self._set_selected_line(None)
            self._loading_detail = False
            return

        lineas = get_lineas(oc.codigo_oc)
        homologadas = sum(1 for linea in lineas if linea.itemcode_sap)
        self.lbl_detail_title.setText(f"Detalle de OC ({len(lineas)} lineas)")
        self.lbl_detail_hint.setText(
            f"{len(lineas)} linea(s) | {homologadas} con itemcode | Estado app: {oc.estado_interno or '--'}"
        )
        self.lbl_oc_codigo.setText(oc.codigo_oc)
        self.lbl_oc_cliente.setText(oc.nombre_organismo or "--")
        self.lbl_oc_fecha.setText(self._format_date(oc.fecha_envio))
        self.lbl_oc_cliente_sap.setText(oc.cliente_sap_sugerido or "--")
        self.lbl_oc_cartera.setText((self._selected_row.cartera if self._selected_row else "") or "--")
        self.lbl_oc_total.setText(self._format_money(oc.total))
        self._apply_badge(
            self.lbl_oc_tipo_chip,
            oc.tipo_oc or "--",
            {
                "cm": ("#2B2152", "#C4B5FD", "#4C3D86"),
                "se": ("#1F334B", "#93C5FD", "#315983"),
                "oc": ("#3B2A10", "#FCD34D", "#6B4B16"),
                "ag": ("#1D3A33", "#6EE7B7", "#245B4F"),
                "privada": ("#2B3044", "#D7E2F5", "#3A4568"),
            },
        )
        self._apply_badge(
            self.lbl_oc_estado_mp_chip,
            oc.estado_mp or "--",
            {
                "enviada a proveedor": ("#1E324A", "#93C5FD", "#35557F"),
                "aceptada": ("#103226", "#6EE7B7", "#1F6A4C"),
                "nueva orden de compra": ("#3A2A08", "#FBBF24", "#6C4E11"),
                "cancelada": ("#421A1A", "#FCA5A5", "#7F1D1D"),
                "recepcion conforme": ("#1D3A33", "#5EEAD4", "#245B4F"),
            },
        )
        self.lbl_oc_codigo.setToolTip(oc.codigo_oc)
        self.lbl_oc_cliente.setToolTip(oc.nombre_organismo or "--")
        self.lbl_oc_fecha.setToolTip(self._format_date(oc.fecha_envio))
        self.lbl_oc_cliente_sap.setToolTip(oc.cliente_sap_sugerido or "--")
        self.lbl_oc_cartera.setToolTip((self._selected_row.cartera if self._selected_row else "") or "--")
        self.lbl_oc_total.setToolTip(self._format_money(oc.total))
        self.estado_detail_combo.setCurrentText(oc.estado_interno or "Nueva")
        self.notes_edit.setPlainText((oc.notas or "").replace("\r\n", "\n"))
        self.btn_save_notes.setEnabled(False)
        self.btn_mark_ingresada.setEnabled(oc.estado_interno != "Ingresada")
        self.btn_copy_sap.setEnabled(bool(lineas))
        self.btn_copy_cliente_sap.setEnabled(bool(oc.cliente_sap_sugerido))
        self.btn_copy_codigo.setEnabled(bool(oc.codigo_oc))
        self.btn_export_excel.setEnabled(bool(lineas))
        self.btn_open_portal.setEnabled(True)
        self.btn_sap_settings.setEnabled(True)
        self.lbl_oc_notas_estado.setText("Sin cambios pendientes")
        self.lineas_model.set_rows(lineas)
        self.lbl_line_title.setText(f"Lineas de la OC ({len(lineas)})")
        self.lbl_line_meta.setText(f"{len(lineas)} linea(s) | {homologadas} homologadas")
        if lineas:
            self.lineas_table.selectRow(0)
            self._set_selected_line(lineas[0])
        else:
            self._set_selected_line(None)
        self._loading_detail = False

    @staticmethod
    def _dense_table_stylesheet() -> str:
        return """
            QTableView {
                border: 1px solid #22304A;
                border-radius: 8px;
                background-color: #0F172A;
                gridline-color: #1D2940;
                selection-background-color: #19304D;
                selection-color: #F8FBFF;
                alternate-background-color: #111C2C;
                outline: 0;
            }
            QTableView::item {
                padding: 2px 5px;
                border-bottom: 1px solid #182235;
            }
            QTableView::item:selected {
                background-color: #19304D;
                color: #F8FBFF;
            }
            QHeaderView::section {
                background-color: #162033;
                color: #B8C8DD;
                border: none;
                border-right: 1px solid #22304A;
                border-bottom: 1px solid #2A3A57;
                padding: 3px 5px;
                font-size: 10px;
                font-weight: 700;
            }
            QHeaderView::section:first {
                border-top-left-radius: 10px;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """

    @staticmethod
    def _format_date(value: str) -> str:
        if not value:
            return "--"
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d")
        except Exception:
            return str(value)[:10]

    @staticmethod
    def _format_money(value: float | int | None) -> str:
        return f"${float(value or 0):,.0f}".replace(",", ".")

    @staticmethod
    def _format_quantity(value: float | int | None) -> str:
        numeric = float(value or 0)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _make_value_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldValue")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    @staticmethod
    def _make_chip_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Chip")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    @staticmethod
    def _make_ghost_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumWidth(84)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setStyleSheet(
            "QPushButton {"
            " background: transparent;"
            " border: 1px solid transparent;"
            " color: #CBD5E1;"
            " padding: 2px 6px;"
            " min-height: 24px;"
            "}"
            "QPushButton:hover {"
            " background: #162033;"
            " border: 1px solid #22304A;"
            "}"
        )
        return btn

    @staticmethod
    def _apply_badge(label: QLabel, text: str, palette: dict[str, tuple[str, str, str]]) -> None:
        raw = (text or "--").strip() or "--"
        bg, fg, border = palette.get(raw.casefold(), ("#162033", "#CBD5E1", "#22304A"))
        label.setText(raw)
        label.setStyleSheet(
            "padding: 3px 8px;"
            "border-radius: 999px;"
            f"background-color: {bg};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            "font-size: 10px;"
            "font-weight: 600;"
        )

    @staticmethod
    def _compact_field(title: str, value_label: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        caption = QLabel(title)
        caption.setObjectName("SectionEyebrow")
        layout.addWidget(caption)
        layout.addWidget(value_label)
        return wrap

    @staticmethod
    def _detail_field(title: str, value_label: QWidget) -> QWidget:
        wrap = QFrame()
        wrap.setObjectName("DetailField")
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)
        caption = QLabel(title)
        caption.setObjectName("SectionEyebrow")
        caption.setMinimumWidth(62)
        layout.addWidget(caption)
        layout.addWidget(value_label, 1)
        return wrap

    @staticmethod
    def _labeled_field(title: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        label = QLabel(title)
        label.setObjectName("SectionEyebrow")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrap

    def _apply_line_table_column_prefs(self) -> None:
        header = self.lineas_table.horizontalHeader()
        model_columns = [column_id for column_id, _label in self.lineas_model.columns]

        for logical_index, column_id in enumerate(model_columns):
            spec = SAP_COLUMN_LOOKUP.get(column_id)
            if spec:
                self.lineas_table.setColumnWidth(logical_index, int(spec["width"]))
            self.lineas_table.setColumnHidden(logical_index, not self._sap_col_visible.get(column_id, True))

        for visual_index, column_id in enumerate(self._sap_col_order):
            if column_id not in model_columns:
                continue
            logical_index = model_columns.index(column_id)
            current_visual = header.visualIndex(logical_index)
            if current_visual != visual_index:
                header.moveSection(current_visual, visual_index)

    def _copy_text_value(self, text: str, status: str) -> None:
        value = (text or "").strip()
        if not value or value == "--":
            return
        QGuiApplication.clipboard().setText(value)
        self.lbl_oc_notas_estado.setText(status)

    def _show_sap_settings(self) -> None:
        dialog = SapColumnConfigDialog(self._sap_col_order, self._sap_col_visible, self._sap_col_copy, self)
        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return
        self._sap_col_order, self._sap_col_visible, self._sap_col_copy = dialog.get_prefs()
        _save_sap_column_prefs(self._sap_col_order, self._sap_col_visible, self._sap_col_copy)
        self._apply_line_table_column_prefs()
        self.lbl_oc_notas_estado.setText("Ajustes SAP guardados.")

    def _open_portal(self) -> None:
        if not self._selected_oc:
            return
        url = (
            "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
            f"DetailsPurchaseOrder.aspx?codigoOC={self._selected_oc.codigo_oc}"
        )
        webbrowser.open(url)
        self.lbl_oc_notas_estado.setText("Portal abierto en el navegador.")

    def _export_excel(self) -> None:
        if not self._selected_oc:
            return
        lineas = get_lineas(self._selected_oc.codigo_oc)
        if not lineas:
            QMessageBox.information(self, "Exportar Excel", "La OC seleccionada no tiene lineas para exportar.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar detalle OC",
            f"OC_{self._selected_oc.codigo_oc}.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return

        try:
            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Detalle OC"

            ws.append(["OC", self._selected_oc.codigo_oc])
            ws.append(["Comprador", self._selected_oc.nombre_organismo])
            ws.append(["Cliente SAP", self._selected_oc.cliente_sap_sugerido])
            ws.append(["Fecha envio", self._format_date(self._selected_oc.fecha_envio)])
            ws.append(["Estado MP", self._selected_oc.estado_mp])
            ws.append(["Total", self._selected_oc.total])
            ws.append(["Cantidad lineas", len(lineas)])
            ws.append([])
            ws.append(["#", "Cod. MP", "Descripcion", "ItemCode", "Descripcion SAP", "Cant.", "Total", "Estado"])

            for linea in lineas:
                ws.append(
                    [
                        linea.correlativo,
                        linea.codigo_mp,
                        (linea.especificacion_comprador or linea.producto or "").strip(),
                        linea.itemcode_sap or "",
                        linea.descripcion_sap or "",
                        self._format_quantity(linea.cantidad),
                        float(linea.total or 0),
                        linea.estado_homologacion or "",
                    ]
                )

            wb.save(path)
            self.lbl_oc_notas_estado.setText(f"Exportado: {Path(path).name}")
        except Exception as exc:
            QMessageBox.warning(self, "Exportar Excel", f"No se pudo exportar el archivo.\n\n{exc}")

    def _handle_line_selection_change(self, *_args) -> None:
        indexes = self.lineas_table.selectionModel().selectedRows()
        if not indexes:
            self._set_selected_line(None)
            return
        self._set_selected_line(self.lineas_model.row_at(indexes[0].row()))

    def _set_selected_line(self, linea: LineaOC | None) -> None:
        self._selected_line = linea
        if linea is None:
            self.lbl_line_summary.setText("Selecciona una linea para ver el contexto.")
            self.lbl_line_desc.setText("Selecciona una linea para ver la especificacion completa.")
            return

        descripcion = (linea.especificacion_comprador or linea.producto or "").strip() or "--"
        descripcion_sap = (linea.descripcion_sap or "").strip() or "Sin descripcion SAP."
        codigo_mp = (linea.codigo_mp or linea.codigo_producto_api or "").strip() or f"Linea {linea.correlativo}"
        cantidad = self._format_quantity(linea.cantidad)
        unidad = linea.unidad or ""
        total = self._format_money(linea.total)

        itemcode = linea.itemcode_sap or "--"
        estado = linea.estado_homologacion or "--"
        self.lbl_line_summary.setText(
            f"Cod. MP: {codigo_mp} | Estado: {estado} | Cantidad: {cantidad} {unidad} | Total: {total} | ItemCode: {itemcode}"
        )
        self.lbl_line_desc.setText(f"{descripcion}\nSAP: {descripcion_sap}")
        self.lbl_line_desc.setToolTip(f"{descripcion}\nSAP: {descripcion_sap}")

    def _on_estado_changed(self, estado: str) -> None:
        if self._loading_detail or not self._selected_oc:
            return
        if not estado or estado == self._selected_oc.estado_interno:
            return
        if self._selected_oc.estado_interno == "Ingresada" and estado != "Ingresada":
            answer = QMessageBox.question(
                self,
                "Cambiar estado",
                "Esta OC ya fue marcada como Ingresada. ¿Deseas cambiar el estado igualmente?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._loading_detail = True
                self.estado_detail_combo.setCurrentText(self._selected_oc.estado_interno or "Ingresada")
                self._loading_detail = False
                return

        actualizar_estado(self._selected_oc.codigo_oc, estado)
        self._selected_oc.estado_interno = estado
        self.lbl_oc_notas_estado.setText(f"Estado actualizado a {estado}.")
        self.btn_mark_ingresada.setEnabled(estado != "Ingresada")
        self.refresh()

    def _mark_ingresada(self) -> None:
        if not self._selected_oc:
            return
        answer = QMessageBox.question(
            self,
            "Marcar como ingresada",
            f"¿Marcar la OC {self._selected_oc.codigo_oc} como ingresada en SAP?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        marcar_ingresada(self._selected_oc.codigo_oc)
        self._selected_oc.estado_interno = "Ingresada"
        self.lbl_oc_notas_estado.setText("OC marcada como ingresada.")
        self.refresh()

    def _on_notes_changed(self) -> None:
        if self._loading_detail or not self._selected_oc:
            return
        current = self.notes_edit.toPlainText().strip()
        original = (self._selected_oc.notas or "").strip()
        changed = current != original
        self.btn_save_notes.setEnabled(changed)
        self.lbl_oc_notas_estado.setText("Cambios sin guardar" if changed else "Sin cambios pendientes")

    def _save_notes(self) -> None:
        if not self._selected_oc:
            return
        notas = self.notes_edit.toPlainText().strip()
        guardar_notas(self._selected_oc.codigo_oc, notas)
        self._selected_oc.notas = notas
        self.btn_save_notes.setEnabled(False)
        self.lbl_oc_notas_estado.setText("Notas guardadas.")

    def _copy_sap(self) -> None:
        if not self._selected_oc:
            return
        lineas = get_lineas(self._selected_oc.codigo_oc)
        if not lineas:
            QMessageBox.warning(self, "Sin lineas", "Esta OC no tiene lineas disponibles para copiar.")
            return

        selected_columns = [column_id for column_id in self._sap_col_order if self._sap_col_copy.get(column_id, False)]
        if not selected_columns:
            QMessageBox.warning(
                self,
                "Ajustes SAP",
                "No hay columnas marcadas para copiar.\n\nUsa el boton Ajustes SAP para activar al menos una.",
            )
            return

        def _fmt_cantidad(value: float | int | None) -> str:
            number = float(value or 0)
            if number.is_integer():
                return str(int(number))
            return f"{number:.4f}".rstrip("0").rstrip(".").replace(".", ",")

        def _fmt_precio(value: float | int | None) -> str:
            return f"{float(value or 0):.4f}".rstrip("0").rstrip(".").replace(".", ",")

        extractors = {
            "correlativo": lambda l: str(l.correlativo),
            "codigo_mp": lambda l: (l.codigo_mp or l.codigo_producto_api or "").strip(),
            "descripcion": lambda l: (l.especificacion_comprador or l.producto or "").strip(),
            "itemcode_sap": lambda l: (l.itemcode_sap or "").strip(),
            "descripcion_sap": lambda l: (l.descripcion_sap or l.producto or "").strip(),
            "cantidad": lambda l: _fmt_cantidad(l.cantidad),
            "cantidad_sap": lambda l: _fmt_cantidad(l.cantidad_sap if l.cantidad_sap is not None else l.cantidad),
            "factor_empaque": lambda l: _fmt_cantidad(l.factor_empaque or 1),
            "precio_neto": lambda l: _fmt_precio(l.precio_neto),
            "precio_sap": lambda l: _fmt_precio(l.precio_sap if l.precio_sap is not None else l.precio_neto),
            "unidad": lambda l: (l.unidad or "").strip(),
            "total": lambda l: _fmt_precio(l.total),
            "estado_homologacion": lambda l: (l.estado_homologacion or "").strip(),
        }

        filas: list[str] = []
        excluidos: list[int] = []
        for linea in lineas:
            if not linea.itemcode_sap:
                excluidos.append(linea.correlativo)
                continue
            valores = [extractors[column_id](linea) for column_id in selected_columns if column_id in extractors]
            filas.append("\t".join(valores))

        if not filas:
            QMessageBox.warning(
                self,
                "Sin lineas homologadas",
                "No hay lineas con itemcode SAP listas para copiar.",
            )
            return

        if excluidos:
            answer = QMessageBox.question(
                self,
                "Lineas excluidas",
                f"Se excluiran {len(excluidos)} linea(s) sin itemcode SAP.\n\nDeseas copiar igualmente las homologadas?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        clipboard = QGuiApplication.clipboard()
        clipboard.setText("\r\n".join(filas))
        if excluidos:
            self.lbl_oc_notas_estado.setText(
                f"Copiadas {len(filas)} linea(s). Excluidas: {len(excluidos)} sin itemcode."
            )
        else:
            self.lbl_oc_notas_estado.setText(f"Copiadas {len(filas)} linea(s) para SAP.")
