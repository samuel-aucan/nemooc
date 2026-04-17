"""Modulo real de holdings para la shell Qt."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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

from app.models.cartera import CarteraCliente
from app.services.cartera_service import get_cartera_service
from app.services.holding_admin_service import (
    HoldingAdmin,
    create_holding,
    create_holding_rule,
    delete_holding_rule,
    delete_holding_rut,
    list_holdings_admin,
    update_holding,
    upsert_holding_rut,
)
from app.services.private_catalog_service import import_private_catalog
from app_qt.bootstrap import QtAppContext


class HoldingsPage(QWidget):
    page_title = "Holdings"
    page_subtitle = (
        "Administracion multi-holding en desktop con clientes, correos esperados, "
        "reglas y catalogos por holding."
    )
    page_eyebrow = "Modulo de negocio"

    def __init__(self, context: QtAppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context
        self._holdings: list[HoldingAdmin] = []
        self._selected_holding_id: str | None = None
        self._cartera_search_results: list[CarteraCliente] = []

        self._build()
        self.on_show()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_intro_card())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)

        splitter.addWidget(self._build_list_panel())
        splitter.addWidget(self._build_detail_scroll())
        splitter.setSizes([240, 960])

        root.addWidget(splitter, 1)

    def _build_detail_scroll(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._build_detail_panel())
        return scroll

    def _build_intro_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("PageCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("Configuracion de holdings privados")
        title.setObjectName("CardTitle")
        subtitle = QLabel(
            "Mantiene el modelo simplificado: identidad del holding, RUTs compradores, "
            "correos esperados, ayudas avanzadas y catalogo privado."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        self.notice_label = QLabel("Sin cambios recientes.")
        self.notice_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.notice_label)
        self._set_notice("info", "Sin cambios recientes.")
        return card

    def _build_list_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("PageCard")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Holdings")
        title.setObjectName("CardTitle")
        subtitle = QLabel("Selecciona uno existente o crea uno nuevo.")
        subtitle.setObjectName("PageSubtitle")

        self.input_holding_filter = QLineEdit()
        self.input_holding_filter.setPlaceholderText("Buscar holding...")
        self.input_holding_filter.textChanged.connect(self._filter_holdings_list)

        self.holdings_list = QListWidget()
        self.holdings_list.setSpacing(1)
        self.holdings_list.itemSelectionChanged.connect(self._on_holding_selected)

        actions = QHBoxLayout()
        self.btn_new_holding = QPushButton("Nuevo holding")
        self.btn_new_holding.clicked.connect(self._start_new_holding)
        self.btn_refresh = QPushButton("Actualizar")
        self.btn_refresh.clicked.connect(self._reload_holdings)
        actions.addWidget(self.btn_new_holding)
        actions.addWidget(self.btn_refresh)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.input_holding_filter)
        layout.addWidget(self.holdings_list, 1)
        layout.addLayout(actions)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._build_identity_card())
        layout.addWidget(self._build_ruts_card())
        layout.addWidget(self._build_emails_card())
        layout.addWidget(self._build_catalog_card())
        layout.addWidget(self._build_rules_card())
        layout.addStretch(1)
        return panel

    def _build_identity_card(self) -> QWidget:
        card = self._card("Identidad del holding", "Define el holding, parser, prefijo y estado general.")
        layout = card.layout()
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        self.entry_holding_id = QLineEdit()
        self.entry_holding_id.setPlaceholderText("banmedica")
        self.entry_holding_name = QLineEdit()
        self.entry_holding_name.setPlaceholderText("Banmedica")
        self.entry_holding_prefix = QLineEdit()
        self.entry_holding_prefix.setPlaceholderText("BM")
        self.combo_parser = QComboBox()
        self.combo_parser.setEditable(True)
        self.combo_parser.addItems(["redsalud", "indisa", "banmedica", "achs", "clinicas_regionales"])
        self.entry_homo_file = QLineEdit()
        self.entry_homo_file.setPlaceholderText("HOMO ACHS.xlsx")
        self.chk_holding_active = QCheckBox("Holding activo")

        self.btn_save_holding = QPushButton("Guardar holding")
        self.btn_save_holding.setObjectName("PrimaryButton")
        self.btn_save_holding.clicked.connect(self._save_holding)

        grid.addWidget(self._labeled_field("ID interno", self.entry_holding_id), 0, 0)
        grid.addWidget(self._labeled_field("Nombre visible", self.entry_holding_name), 0, 1)
        grid.addWidget(self._labeled_field("Prefijo", self.entry_holding_prefix), 1, 0)
        grid.addWidget(self._labeled_field("Parser", self.combo_parser), 1, 1)
        grid.addWidget(self._labeled_field("Archivo sugerido", self.entry_homo_file), 2, 0, 1, 2)
        grid.addWidget(self.chk_holding_active, 3, 0)
        grid.addWidget(self.btn_save_holding, 3, 1, 1, 1, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(grid)
        return card

    def _build_ruts_card(self) -> QWidget:
        card = self._card(
            "Empresas y sucursales del holding",
            "Puedes buscar en cartera maestra o agregar el RUT manualmente.",
        )
        layout = card.layout()

        search_row = QHBoxLayout()
        self.input_cartera_search = QLineEdit()
        self.input_cartera_search.setPlaceholderText("Buscar en cartera maestra por razon social, RUT o CN...")
        self.input_cartera_search.textChanged.connect(self._search_cartera)
        search_row.addWidget(self.input_cartera_search)
        layout.addLayout(search_row)

        self.cartera_results = QListWidget()
        self.cartera_results.setMaximumHeight(92)
        self.cartera_results.itemClicked.connect(self._apply_selected_cartera_result)
        layout.addWidget(self.cartera_results)

        form_row = QGridLayout()
        form_row.setContentsMargins(0, 0, 0, 0)
        form_row.setHorizontalSpacing(8)
        form_row.setVerticalSpacing(6)

        self.entry_rut_value = QLineEdit()
        self.entry_rut_value.setPlaceholderText("99.579.260-5")
        self.entry_rut_name = QLineEdit()
        self.entry_rut_name.setPlaceholderText("Empresa de Servicios Externos ACHS")
        self.entry_rut_branch = QLineEdit()
        self.entry_rut_branch.setPlaceholderText("Ramón Carnicer 151, Providencia")
        self.btn_add_rut = QPushButton("Agregar RUT")
        self.btn_add_rut.clicked.connect(self._add_rut_to_holding)
        self.btn_remove_rut = QPushButton("Quitar seleccionado")
        self.btn_remove_rut.clicked.connect(self._remove_selected_rut)

        form_row.addWidget(self._labeled_field("RUT", self.entry_rut_value), 0, 0)
        form_row.addWidget(self._labeled_field("Nombre visible", self.entry_rut_name), 0, 1)
        form_row.addWidget(self._labeled_field("Sucursal / direccion", self.entry_rut_branch), 1, 0, 1, 2)
        form_row.addWidget(self.btn_add_rut, 2, 0)
        form_row.addWidget(self.btn_remove_rut, 2, 1, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form_row)

        self.ruts_table = QTableWidget(0, 3)
        self.ruts_table.setHorizontalHeaderLabels(["RUT", "Nombre", "Sucursal"])
        self._style_table(self.ruts_table)
        self.ruts_table.verticalHeader().setVisible(False)
        self.ruts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ruts_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ruts_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.ruts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ruts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ruts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.ruts_table)
        return card

    def _build_emails_card(self) -> QWidget:
        card = self._card(
            "Correos esperados",
            "Agrega un correo o dominio. Si pegas un correo completo, se guarda solo el dominio.",
        )
        layout = card.layout()

        row = QHBoxLayout()
        self.entry_expected_email = QLineEdit()
        self.entry_expected_email.setPlaceholderText("fastudillo@clinicasantamaria.cl o achs.cl")
        self.btn_add_email = QPushButton("Agregar")
        self.btn_add_email.clicked.connect(self._add_expected_email)
        self.btn_remove_email = QPushButton("Quitar seleccionado")
        self.btn_remove_email.clicked.connect(self._remove_expected_email)
        row.addWidget(self.entry_expected_email, 1)
        row.addWidget(self.btn_add_email)
        row.addWidget(self.btn_remove_email)

        self.email_rules_list = QListWidget()
        self.email_rules_list.setMaximumHeight(96)

        layout.addLayout(row)
        layout.addWidget(self.email_rules_list)
        return card

    def _build_catalog_card(self) -> QWidget:
        card = self._card(
            "Catalogo privado por holding",
            "Permite cargar el Excel de homologacion privada del holding activo.",
        )
        layout = card.layout()

        row = QHBoxLayout()
        self.catalog_info = QLabel("Sin holding seleccionado.")
        self.catalog_info.setObjectName("CardBody")
        self.btn_import_catalog = QPushButton("Importar catalogo")
        self.btn_import_catalog.clicked.connect(self._import_private_catalog_for_holding)
        row.addWidget(self.catalog_info, 1)
        row.addWidget(self.btn_import_catalog)

        layout.addLayout(row)
        return card

    def _build_rules_card(self) -> QWidget:
        card = self._card(
            "Ayudas avanzadas de reconocimiento",
            "Solo para casos especiales. El usuario comun deberia operar casi solo con RUTs y correos.",
        )
        layout = card.layout()

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)

        self.combo_rule_type = QComboBox()
        self.combo_rule_type.addItems(["pdf_contains", "subject_contains", "from_contains", "email_domain"])
        self.entry_rule_value = QLineEdit()
        self.entry_rule_value.setPlaceholderText("CLINICA SANTA MARIA")
        self.entry_rule_priority = QLineEdit()
        self.entry_rule_priority.setPlaceholderText("10")
        self.chk_rule_active = QCheckBox("Activa")
        self.chk_rule_active.setChecked(True)
        self.entry_rule_notes = QLineEdit()
        self.entry_rule_notes.setPlaceholderText("Uso interno")
        self.btn_add_rule = QPushButton("Agregar regla")
        self.btn_add_rule.clicked.connect(self._add_rule)
        self.btn_remove_rule = QPushButton("Quitar regla")
        self.btn_remove_rule.clicked.connect(self._remove_selected_rule)

        form.addWidget(self._labeled_field("Tipo", self.combo_rule_type), 0, 0)
        form.addWidget(self._labeled_field("Valor", self.entry_rule_value), 0, 1)
        form.addWidget(self._labeled_field("Prioridad", self.entry_rule_priority), 0, 2)
        form.addWidget(self.chk_rule_active, 1, 0)
        form.addWidget(self._labeled_field("Notas", self.entry_rule_notes), 1, 1, 1, 2)
        form.addWidget(self.btn_add_rule, 2, 2, 1, 1, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(form)

        self.rules_table = QTableWidget(0, 5)
        self.rules_table.setHorizontalHeaderLabels(["Tipo", "Valor", "Prioridad", "Activo", "Notas"])
        self._style_table(self.rules_table)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rules_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.rules_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rules_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.rules_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.rules_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rules_table)
        layout.addWidget(self.btn_remove_rule, 0, Qt.AlignmentFlag.AlignRight)
        return card

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

    def _labeled_field(self, title: str, widget: QWidget, *_unused) -> QWidget:
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
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.setGridStyle(Qt.PenStyle.SolidLine)
        table.verticalHeader().setDefaultSectionSize(26)
        table.horizontalHeader().setStretchLastSection(False)
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
                gridline-color: #1D2940;
                selection-background-color: #19304D;
                selection-color: #F8FBFF;
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

    def on_show(self) -> None:
        self._reload_holdings()

    def _reload_holdings(self, preserve_selection: bool = True) -> None:
        current_id = self._selected_holding_id if preserve_selection else None
        self._holdings = list_holdings_admin()
        self._filter_holdings_list()

        if current_id:
            self._select_holding_by_id(current_id)
        elif self._holdings:
            self._select_holding_by_id(self._holdings[0].id)
        else:
            self._start_new_holding()

    def _filter_holdings_list(self) -> None:
        query = self.input_holding_filter.text().strip().casefold()
        self.holdings_list.clear()
        for holding in self._holdings:
            haystack = f"{holding.nombre} {holding.id} {holding.prefijo}".casefold()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(f"{holding.nombre}  ·  {holding.prefijo}")
            item.setData(Qt.ItemDataRole.UserRole, holding.id)
            item.setToolTip(
                f"ID: {holding.id}\nParser: {holding.parser_type}\nRUTs: {len(holding.ruts)}\nCatalogo: {holding.catalog_count}"
            )
            self.holdings_list.addItem(item)

    def _select_holding_by_id(self, holding_id: str) -> None:
        for idx in range(self.holdings_list.count()):
            item = self.holdings_list.item(idx)
            if item.data(Qt.ItemDataRole.UserRole) == holding_id:
                self.holdings_list.setCurrentRow(idx)
                break

    def _get_holding(self, holding_id: str | None = None) -> HoldingAdmin | None:
        target = holding_id or self._selected_holding_id
        for holding in self._holdings:
            if holding.id == target:
                return holding
        return None

    def _on_holding_selected(self) -> None:
        items = self.holdings_list.selectedItems()
        if not items:
            return
        holding_id = items[0].data(Qt.ItemDataRole.UserRole)
        holding = self._get_holding(holding_id)
        if not holding:
            return
        self._selected_holding_id = holding.id
        self._load_holding(holding)

    def _load_holding(self, holding: HoldingAdmin) -> None:
        self.entry_holding_id.setText(holding.id)
        self.entry_holding_id.setEnabled(False)
        self.entry_holding_name.setText(holding.nombre)
        self.entry_holding_prefix.setText(holding.prefijo)
        self.combo_parser.setCurrentText(holding.parser_type)
        self.entry_homo_file.setText(holding.homo_file or "")
        self.chk_holding_active.setChecked(bool(holding.activo))
        self.catalog_info.setText(
            f"Catalogo cargado: {holding.catalog_count} item(s)  |  Archivo sugerido: {holding.homo_file or 'Sin nombre sugerido'}"
        )

        self._populate_ruts_table(holding)
        self._populate_email_rules(holding)
        self._populate_rules_table(holding)

        self.entry_expected_email.clear()
        self.entry_rut_value.clear()
        self.entry_rut_name.clear()
        self.entry_rut_branch.clear()
        self.input_cartera_search.clear()
        self.cartera_results.clear()
        self.entry_rule_value.clear()
        self.entry_rule_priority.clear()
        self.entry_rule_notes.clear()
        self.chk_rule_active.setChecked(True)

    def _start_new_holding(self) -> None:
        self._selected_holding_id = None
        self.holdings_list.clearSelection()
        self.entry_holding_id.setEnabled(True)
        self.entry_holding_id.clear()
        self.entry_holding_name.clear()
        self.entry_holding_prefix.clear()
        self.combo_parser.setCurrentText("")
        self.entry_homo_file.clear()
        self.chk_holding_active.setChecked(True)
        self.catalog_info.setText("Guarda primero el holding para poder cargar RUTs, correos y catalogo.")
        self.ruts_table.setRowCount(0)
        self.email_rules_list.clear()
        self.rules_table.setRowCount(0)
        self.cartera_results.clear()
        self.entry_rut_value.clear()
        self.entry_rut_name.clear()
        self.entry_rut_branch.clear()
        self._set_notice("info", "Modo nuevo holding. Completa identidad y guarda para seguir.")

    def _populate_ruts_table(self, holding: HoldingAdmin) -> None:
        self.ruts_table.setRowCount(len(holding.ruts))
        for row, rut in enumerate(holding.ruts):
            self._set_readonly_item(self.ruts_table, row, 0, rut.rut_norm, rut.rut_norm)
            self._set_readonly_item(self.ruts_table, row, 1, rut.rut_display or "", rut.rut_norm)
            self._set_readonly_item(self.ruts_table, row, 2, rut.nombre_sucursal or "", rut.rut_norm)

    def _populate_email_rules(self, holding: HoldingAdmin) -> None:
        self.email_rules_list.clear()
        for rule in holding.rules:
            if rule.rule_type != "email_domain":
                continue
            item = QListWidgetItem(rule.rule_value)
            item.setData(Qt.ItemDataRole.UserRole, rule.id)
            item.setToolTip(rule.notas or "Correo esperado")
            self.email_rules_list.addItem(item)

    def _populate_rules_table(self, holding: HoldingAdmin) -> None:
        rules = [rule for rule in holding.rules if rule.rule_type != "email_domain"]
        self.rules_table.setRowCount(len(rules))
        for row, rule in enumerate(rules):
            self._set_readonly_item(self.rules_table, row, 0, rule.rule_type, rule.id)
            self._set_readonly_item(self.rules_table, row, 1, rule.rule_value, rule.id)
            self._set_readonly_item(self.rules_table, row, 2, str(rule.prioridad), rule.id)
            self._set_readonly_item(self.rules_table, row, 3, "Si" if rule.activo else "No", rule.id)
            self._set_readonly_item(self.rules_table, row, 4, rule.notas or "", rule.id)

    def _set_readonly_item(self, table: QTableWidget, row: int, column: int, text: str, user_data) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(Qt.ItemDataRole.UserRole, user_data)
        table.setItem(row, column, item)

    def _current_holding_id(self) -> str | None:
        if self._selected_holding_id:
            return self._selected_holding_id
        candidate = self.entry_holding_id.text().strip().lower()
        return candidate or None

    def _require_saved_holding(self) -> str | None:
        holding_id = self._current_holding_id()
        if not holding_id or not self._get_holding(holding_id):
            QMessageBox.information(
                self,
                "Guardar primero",
                "Guarda primero el holding para poder administrar RUTs, correos, reglas o catalogos.",
            )
            return None
        return holding_id

    def _save_holding(self) -> None:
        holding_id = self.entry_holding_id.text().strip().lower()
        nombre = self.entry_holding_name.text().strip()
        prefijo = self.entry_holding_prefix.text().strip().upper()
        parser_type = self.combo_parser.currentText().strip().lower()
        homo_file = self.entry_homo_file.text().strip()
        activo = self.chk_holding_active.isChecked()

        if not holding_id or not nombre or not prefijo or not parser_type:
            QMessageBox.warning(self, "Holding", "Completa ID, nombre, prefijo y parser.")
            return

        try:
            existing = self._get_holding(holding_id)
            if existing:
                update_holding(holding_id, nombre, prefijo, parser_type, homo_file, activo)
                message = f"Holding actualizado: {nombre}"
            else:
                create_holding(holding_id, nombre, prefijo, parser_type, homo_file, activo)
                message = f"Holding creado: {nombre}"
            self._set_notice("success", message)
            self._reload_holdings(preserve_selection=False)
            self._select_holding_by_id(holding_id)
        except Exception as exc:
            self._set_notice("error", f"No se pudo guardar el holding: {exc}")
            QMessageBox.critical(self, "Holding", f"No se pudo guardar el holding.\n\n{exc}")

    def _search_cartera(self) -> None:
        query = self.input_cartera_search.text().strip()
        self.cartera_results.clear()
        self._cartera_search_results = []
        if len(query) < 2:
            return
        self._cartera_search_results = get_cartera_service().search(query, limit=8)
        for result in self._cartera_search_results:
            item = QListWidgetItem(f"{result.razon}  ·  {result.rut}  ·  {result.cod_cliente}")
            item.setToolTip(f"Cartera: {result.cartera}\nComuna: {result.comuna}\nVendedor: {result.vendedor}")
            item.setData(Qt.ItemDataRole.UserRole, result.cod_cliente)
            self.cartera_results.addItem(item)

    def _apply_selected_cartera_result(self, item: QListWidgetItem) -> None:
        code = item.data(Qt.ItemDataRole.UserRole)
        selected = next((row for row in self._cartera_search_results if row.cod_cliente == code), None)
        if not selected:
            return
        self.entry_rut_value.setText(selected.rut)
        self.entry_rut_name.setText(selected.razon)
        self.entry_rut_branch.setText(selected.comuna or selected.region_nombre or selected.cartera)

    def _add_rut_to_holding(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return

        rut_value = self.entry_rut_value.text().strip()
        rut_name = self.entry_rut_name.text().strip()
        rut_branch = self.entry_rut_branch.text().strip()
        if not rut_value:
            QMessageBox.warning(self, "RUT", "Ingresa un RUT antes de agregarlo.")
            return

        try:
            upsert_holding_rut(holding_id, rut_value, rut_name, rut_branch)
            self._set_notice("success", f"RUT agregado a {holding_id}: {rut_value}")
            self._reload_holdings()
            self._select_holding_by_id(holding_id)
            self.entry_rut_value.clear()
            self.entry_rut_name.clear()
            self.entry_rut_branch.clear()
        except Exception as exc:
            self._set_notice("error", f"No se pudo agregar el RUT: {exc}")
            QMessageBox.warning(self, "RUT", f"No se pudo agregar el RUT.\n\n{exc}")

    def _remove_selected_rut(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        row = self.ruts_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "RUT", "Selecciona un RUT para quitar.")
            return
        item = self.ruts_table.item(row, 0)
        rut_norm = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not rut_norm:
            return
        delete_holding_rut(holding_id, rut_norm)
        self._set_notice("success", f"RUT eliminado de {holding_id}.")
        self._reload_holdings()
        self._select_holding_by_id(holding_id)

    def _normalize_expected_domain(self, raw: str) -> str:
        value = raw.strip().lower()
        if "@" in value:
            value = value.split("@", 1)[1]
        return value.strip()

    def _add_expected_email(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        domain = self._normalize_expected_domain(self.entry_expected_email.text())
        if not domain or "." not in domain:
            QMessageBox.warning(self, "Correos esperados", "Ingresa un correo o dominio valido.")
            return
        try:
            create_holding_rule(holding_id, "email_domain", domain, 10, True, "Creado desde correos esperados")
            self.entry_expected_email.clear()
            self._set_notice("success", f"Correo esperado agregado: {domain}")
            self._reload_holdings()
            self._select_holding_by_id(holding_id)
        except Exception as exc:
            self._set_notice("error", f"No se pudo agregar el correo esperado: {exc}")
            QMessageBox.warning(self, "Correos esperados", f"No se pudo agregar.\n\n{exc}")

    def _remove_expected_email(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        item = self.email_rules_list.currentItem()
        if not item:
            QMessageBox.information(self, "Correos esperados", "Selecciona un dominio para quitar.")
            return
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        delete_holding_rule(holding_id, int(rule_id))
        self._set_notice("success", "Correo esperado eliminado.")
        self._reload_holdings()
        self._select_holding_by_id(holding_id)

    def _add_rule(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        rule_type = self.combo_rule_type.currentText().strip()
        rule_value = self.entry_rule_value.text().strip()
        if not rule_type or not rule_value:
            QMessageBox.warning(self, "Reglas", "Completa tipo y valor de la regla.")
            return
        try:
            prioridad = int(self.entry_rule_priority.text().strip() or "100")
        except ValueError:
            QMessageBox.warning(self, "Reglas", "La prioridad debe ser numerica.")
            return

        try:
            create_holding_rule(
                holding_id,
                rule_type,
                rule_value,
                prioridad,
                self.chk_rule_active.isChecked(),
                self.entry_rule_notes.text().strip(),
            )
            self.entry_rule_value.clear()
            self.entry_rule_priority.clear()
            self.entry_rule_notes.clear()
            self.chk_rule_active.setChecked(True)
            self._set_notice("success", "Regla avanzada agregada.")
            self._reload_holdings()
            self._select_holding_by_id(holding_id)
        except Exception as exc:
            self._set_notice("error", f"No se pudo agregar la regla: {exc}")
            QMessageBox.warning(self, "Reglas", f"No se pudo agregar la regla.\n\n{exc}")

    def _remove_selected_rule(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        row = self.rules_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Reglas", "Selecciona una regla para quitar.")
            return
        item = self.rules_table.item(row, 0)
        rule_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if rule_id is None:
            return
        delete_holding_rule(holding_id, int(rule_id))
        self._set_notice("success", "Regla avanzada eliminada.")
        self._reload_holdings()
        self._select_holding_by_id(holding_id)

    def _import_private_catalog_for_holding(self) -> None:
        holding_id = self._require_saved_holding()
        if not holding_id:
            return
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar catalogo privado",
            str(Path.cwd()),
            "Excel (*.xlsx *.xlsm);;Todos (*.*)",
        )
        if not selected:
            return
        try:
            count, errors = import_private_catalog(holding_id, selected)
            message = f"Catalogo importado para {holding_id}: {count} registro(s)."
            if errors:
                message += "\n" + "\n".join(errors[:4])
            self._set_notice("success" if count > 0 else "error", message)
            QMessageBox.information(self, "Catalogo privado", message)
            self._reload_holdings()
            self._select_holding_by_id(holding_id)
        except Exception as exc:
            self._set_notice("error", f"No se pudo importar el catalogo: {exc}")
            QMessageBox.warning(self, "Catalogo privado", f"No se pudo importar el catalogo.\n\n{exc}")

    def _set_notice(self, kind: str, message: str) -> None:
        styles = {
            "info": "border:1px solid #22304A; background:#0F172A; color:#CBD5E1; border-radius:10px; padding:8px 10px;",
            "success": "border:1px solid #14532D; background:#052E1A; color:#BBF7D0; border-radius:10px; padding:8px 10px;",
            "error": "border:1px solid #7F1D1D; background:#3B0A0A; color:#FECACA; border-radius:10px; padding:8px 10px;",
        }
        self.notice_label.setStyleSheet(styles.get(kind, styles["info"]))
        self.notice_label.setText(message)
