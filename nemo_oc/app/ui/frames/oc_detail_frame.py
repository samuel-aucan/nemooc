"""
Panel de detalle de una Orden de Compra.
Muestra cabecera, líneas con estado de homologación y acciones SAP.
"""
import json
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import logging

from app.models.orden_compra import OrdenCompra
from app.models.linea_oc import LineaOC
from app.utils.clipboard_utils import generar_texto_sap, copiar_al_portapapeles
from app.config import get_config_dir

logger = logging.getLogger(__name__)

HOMO_COLORS = {
    "homologado":       {"bg": "#1a3a1a", "fg": "#4caf50", "badge": "✓"},
    "sin_homologacion": {"bg": "#3a1a1a", "fg": "#f44336", "badge": "✗"},
    "pendiente":        {"bg": "#2a2a1a", "fg": "#ff9800", "badge": "⏳"},
    "manual":           {"bg": "#1a2a3a", "fg": "#64b5f6", "badge": "✎"},
}

# Definición de columnas CM: (id, header, ancho, anchor, visible_default, copy_default)
DEFAULT_COLUMNS = [
    ("#",              "#",                40,  "center", True,  False),
    ("codigo_mp",      "Cód. MP",          80,  "center", True,  False),
    ("descripcion_mp", "Descripción OC",  200,  "w",      True,  False),
    ("itemcode",       "ItemCode SAP",    110,  "center", True,  True),
    ("desc_sap",       "Descripción SAP", 180,  "w",      True,  True),
    ("cant_oc",        "Cant OC",          70,  "center", True,  False),
    ("cant_sap",       "Cant SAP",         70,  "center", True,  True),
    ("precio_sap",     "Precio SAP",       90,  "e",      True,  True),
    ("f_emp",          "F.Emp",            50,  "center", True,  False),
    ("estado",         "Homologación",    110,  "center", True,  False),
]

# Columnas para OCs no-CM (SE, AG, CC, etc.)
NONCM_COLUMNS = [
    ("#",               "#",                 40,  "center", True,  False),
    ("espec_comprador", "Espec. Comprador", 220,  "w",      True,  False),
    ("itemcode",        "ItemCode SAP",     110,  "center", True,  True),
    ("desc_sap",        "Desc. SAP",        170,  "w",      True,  True),
    ("sug_top",         "Sugerido SAP",     140,  "w",      True,  False),
    ("cant_oc",         "Cantidad",          70,  "center", True,  False),
    ("precio_neto",     "Precio Neto",       90,  "e",      True,  False),
    ("total",           "Total",            100,  "e",      True,  False),
]

# Todas las columnas posibles (unión CM + no-CM) para inicializar el Treeview
ALL_COLUMNS_INIT = [
    ("#",               "#",                 40,  "center"),
    ("codigo_mp",       "Cód. MP",           80,  "center"),
    ("descripcion_mp",  "Descripción OC",   200,  "w"),
    ("producto",        "Producto portal",  180,  "w"),
    ("espec_comprador", "Espec. Comprador", 200,  "w"),
    ("itemcode",        "ItemCode SAP",     110,  "center"),
    ("desc_sap",        "Descripción SAP",  180,  "w"),
    ("sug_top",         "Sugerido SAP",     140,  "w"),
    ("cant_oc",         "Cant OC",           70,  "center"),
    ("cant_sap",        "Cant SAP",          70,  "center"),
    ("precio_sap",      "Precio SAP",        90,  "e"),
    ("f_emp",           "F.Emp",             50,  "center"),
    ("unidad",          "Unidad",            70,  "center"),
    ("precio_neto",     "Precio Neto",       90,  "e"),
    ("total",           "Total",            100,  "e"),
    ("estado",          "Homologación",     110,  "center"),
]

COLUMN_PREFS_FILE = get_config_dir() / "column_prefs.json"


def _load_column_prefs():
    """Carga preferencias de columnas (orden, visibilidad y copia) del usuario."""
    try:
        if COLUMN_PREFS_FILE.exists():
            data = json.loads(COLUMN_PREFS_FILE.read_text(encoding="utf-8"))
            order = data.get("order", [])
            visible = data.get("visible", {})
            copy = data.get("copy", {})
            if order:
                return order, visible, copy
    except Exception:
        pass
    return (
        [c[0] for c in DEFAULT_COLUMNS],
        {c[0]: c[4] for c in DEFAULT_COLUMNS},
        {c[0]: c[5] for c in DEFAULT_COLUMNS},
    )


def _save_column_prefs(order: list, visible: dict, copy: dict):
    """Guarda preferencias de columnas del usuario."""
    try:
        COLUMN_PREFS_FILE.write_text(
            json.dumps({"order": order, "visible": visible, "copy": copy},
                       ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.warning(f"No se pudieron guardar preferencias de columnas: {e}")


class OcDetailFrame(ctk.CTkFrame):

    def __init__(self, master, app_state, on_back=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_back = on_back
        self._oc: OrdenCompra = None
        self._lineas: list[LineaOC] = []
        self._col_order, self._col_visible, self._col_copy = _load_column_prefs()
        # Asegurar que todas las columnas default estén presentes
        all_ids = {c[0] for c in DEFAULT_COLUMNS}
        defaults_copy = {c[0]: c[5] for c in DEFAULT_COLUMNS}
        for cid in all_ids:
            if cid not in self._col_visible:
                self._col_visible[cid] = True
            if cid not in self._col_copy:
                self._col_copy[cid] = defaults_copy[cid]
        for cid in all_ids:
            if cid not in self._col_order:
                self._col_order.append(cid)
        self._build()
        self._apply_treeview_style()

    def _build(self):
        # ── Barra superior con botón Volver ─────────────────────────────
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(12, 0))
        if self.on_back:
            ctk.CTkButton(top_bar, text="← Volver", width=90, fg_color="gray30",
                          command=self.on_back).pack(side="left")
        self.lbl_title = ctk.CTkLabel(top_bar, text="Detalle OC",
                                       font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_title.pack(side="left", padx=16)

        # ── Datos para copiar (OC + Cliente SAP) ─────────────────────
        copy_card = ctk.CTkFrame(self, fg_color="#1a2a3a", corner_radius=8)
        copy_card.pack(fill="x", padx=20, pady=(12, 0))

        copy_row = ctk.CTkFrame(copy_card, fg_color="transparent")
        copy_row.pack(fill="x", padx=16, pady=10)

        # Código OC + Copiar
        ctk.CTkLabel(copy_row, text="OC:", text_color="gray",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self.lbl_codigo = ctk.CTkLabel(copy_row, text="",
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_codigo.pack(side="left", padx=(6, 0))
        ctk.CTkButton(copy_row, text="Copiar OC", width=80, height=28,
                      fg_color="#424242", hover_color="#616161",
                      font=ctk.CTkFont(size=11),
                      command=self._copiar_codigo_oc).pack(side="left", padx=(8, 0))

        # Separador visual
        ctk.CTkLabel(copy_row, text="  |  ", text_color="gray40").pack(side="left", padx=4)

        # Cliente SAP + Copiar
        ctk.CTkLabel(copy_row, text="Cliente SAP:", text_color="gray",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self.lbl_cliente_sap = ctk.CTkLabel(copy_row, text="",
                                             font=ctk.CTkFont(size=14, weight="bold"),
                                             text_color="#64B5F6")
        self.lbl_cliente_sap.pack(side="left", padx=(6, 0))
        ctk.CTkButton(copy_row, text="Copiar Cliente", width=100, height=28,
                      fg_color="#1565C0", hover_color="#0D47A1",
                      font=ctk.CTkFont(size=11),
                      command=self._copiar_cliente_sap).pack(side="left", padx=(8, 0))

        # Total a la derecha
        self.lbl_total = ctk.CTkLabel(copy_row, text="",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color="#4CAF50")
        self.lbl_total.pack(side="right")

        # ── Cabecera OC (info secundaria) ──────────────────────────────
        self.header_card = ctk.CTkFrame(self)
        self.header_card.pack(fill="x", padx=20, pady=(6, 0))

        # Fila 1: Comprador | Estado MP | Fecha
        row1 = ctk.CTkFrame(self.header_card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(10, 0))
        self.lbl_comprador = ctk.CTkLabel(row1, text="", text_color="gray",
                                           wraplength=500, justify="left")
        self.lbl_comprador.pack(side="left")
        self.lbl_estado_mp = ctk.CTkLabel(row1, text="", width=100)
        self.lbl_estado_mp.pack(side="right", padx=(16, 0))
        self.lbl_fecha = ctk.CTkLabel(row1, text="", text_color="gray")
        self.lbl_fecha.pack(side="right")

        # Fila 2: Estado interno + Notas
        row2 = ctk.CTkFrame(self.header_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(6, 10))

        ctk.CTkLabel(row2, text="Estado:").pack(side="left", padx=(0, 6))
        self.opt_estado = ctk.CTkOptionMenu(
            row2,
            values=["Pendiente", "Nueva", "Revisada", "Lista para SAP", "Ingresada", "Con error"],
            width=140,
            command=self._cambiar_estado
        )
        self.opt_estado.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Notas:").pack(side="left", padx=(0, 6))
        self.entry_notas = ctk.CTkEntry(row2, placeholder_text="Observaciones internas...")
        self.entry_notas.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row2, text="Guardar", width=80,
                      command=self._guardar_notas).pack(side="left", padx=(8, 0))

        # ── Barra de acciones (SIEMPRE VISIBLE — arriba de la tabla) ────
        action_bar = ctk.CTkFrame(self)
        action_bar.pack(fill="x", padx=20, pady=(8, 0))

        self.btn_copiar = ctk.CTkButton(
            action_bar, text="📋 Copiar tabla para SAP",
            fg_color="#1565C0", hover_color="#0D47A1",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._copiar_sap
        )
        self.btn_copiar.pack(side="left", padx=(0, 10))

        self.btn_marcar = ctk.CTkButton(
            action_bar, text="✓ Marcar como Ingresada",
            fg_color="#4CAF50", hover_color="#388E3C",
            command=self._marcar_ingresada
        )
        self.btn_marcar.pack(side="left", padx=(0, 10))

        self.btn_excel = ctk.CTkButton(
            action_bar, text="↑ Exportar a Excel",
            fg_color="gray40",
            command=self._exportar_excel
        )
        self.btn_excel.pack(side="left", padx=(0, 10))

        self.btn_portal = ctk.CTkButton(
            action_bar, text="🌐 Ver en portal / PDF",
            fg_color="#1a5276", hover_color="#154360",
            command=self._abrir_en_portal
        )
        self.btn_portal.pack(side="left", padx=(0, 10))

        # Botón configurar columnas
        ctk.CTkButton(
            action_bar, text="⚙ Columnas", width=100, fg_color="gray30",
            command=self._toggle_column_picker
        ).pack(side="right")

        self.lbl_action_msg = ctk.CTkLabel(action_bar, text="", font=ctk.CTkFont(size=12))
        self.lbl_action_msg.pack(side="left", padx=16)

        # ── Advertencia sin homologación ─────────────────────────────────
        self.warn_frame = ctk.CTkFrame(self, fg_color="#3a1a1a", corner_radius=6)
        self.lbl_warn = ctk.CTkLabel(self.warn_frame, text="", text_color="#f44336",
                                      font=ctk.CTkFont(size=12))
        self.lbl_warn.pack(padx=12, pady=6)

        # ── Barra compacta de asignación (no-CM) — justo sobre la tabla ─
        self._assign_bar = ctk.CTkFrame(self, fg_color="#152030", corner_radius=6)
        # Se pack() / pack_forget() dinámicamente al seleccionar línea

        assign_row = ctk.CTkFrame(self._assign_bar, fg_color="transparent")
        assign_row.pack(fill="x", padx=10, pady=5)

        self._lbl_linea_sel = ctk.CTkLabel(
            assign_row, text="—", text_color="gray",
            font=ctk.CTkFont(size=11), width=190, anchor="w")
        self._lbl_linea_sel.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(assign_row, text="|", text_color="gray30").pack(side="left", padx=2)

        self._lbl_sug_top = ctk.CTkLabel(
            assign_row, text="", text_color="#64b5f6",
            font=ctk.CTkFont(size=11, weight="bold"), width=160, anchor="w")
        self._lbl_sug_top.pack(side="left", padx=(6, 4))

        self._btn_asignar = ctk.CTkButton(
            assign_row, text="✓ Asignar sugerido", width=140, height=26,
            fg_color="#1565C0", font=ctk.CTkFont(size=11),
            command=self._asignar_sugerencia)
        self._btn_asignar.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(assign_row, text="|", text_color="gray30").pack(side="left", padx=2)
        ctk.CTkLabel(assign_row, text="o código:", text_color="gray",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))

        self._entry_itemcode_manual = ctk.CTkEntry(
            assign_row, width=100, height=26, placeholder_text="KNE00010")
        self._entry_itemcode_manual.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            assign_row, text="Asignar", width=65, height=26,
            fg_color="#2e7d32", font=ctk.CTkFont(size=11),
            command=self._asignar_manual).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            assign_row, text="Limpiar", width=65, height=26,
            fg_color="gray30", hover_color="gray40", font=ctk.CTkFont(size=11),
            command=self._limpiar_asignacion).pack(side="left", padx=(0, 6))

        self._lbl_assign_msg = ctk.CTkLabel(
            assign_row, text="", font=ctk.CTkFont(size=11))
        self._lbl_assign_msg.pack(side="left", padx=4)

        # ── Tabla de líneas ─────────────────────────────────────────────
        self._table_frame = ctk.CTkFrame(self)
        self._table_frame.pack(fill="both", expand=True, padx=20, pady=(4, 8))

        all_col_ids = tuple(col[0] for col in ALL_COLUMNS_INIT)
        self.tree = ttk.Treeview(
            self._table_frame, columns=all_col_ids,
            show="headings", selectmode="browse")

        for cid, hdr, w, anchor in ALL_COLUMNS_INIT:
            self.tree.heading(cid, text=hdr)
            self.tree.column(cid, width=w, minwidth=40, anchor=anchor)

        self._apply_column_order()

        vsb = ttk.Scrollbar(self._table_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(self._table_frame, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Cache de sugerencias (correlativo int → SugerenciaProducto)
        self._sug_cache: dict = {}

        self._col_picker = None

    # ── Copiar datos de cabecera ────────────────────────────────────────

    def _copiar_codigo_oc(self):
        if self._oc:
            copiar_al_portapapeles(self._oc.codigo_oc, root=self.winfo_toplevel())
            self.lbl_action_msg.configure(text=f"✓ Código OC copiado: {self._oc.codigo_oc}", text_color="green")

    def _copiar_cliente_sap(self):
        if self._oc:
            copiar_al_portapapeles(self._oc.cliente_sap_sugerido, root=self.winfo_toplevel())
            self.lbl_action_msg.configure(text=f"✓ Cliente SAP copiado: {self._oc.cliente_sap_sugerido}", text_color="green")

    # ── Selección de columnas visibles ──────────────────────────────────

    def _apply_column_order(self):
        """Aplica el orden y visibilidad guardados al Treeview."""
        col_lookup = {c[0]: c for c in DEFAULT_COLUMNS}
        all_ids = {c[0] for c in DEFAULT_COLUMNS}

        # Solo columnas VISIBLES en el orden guardado → las ocultas desaparecen del todo
        visible_ordered = [
            c for c in self._col_order
            if c in all_ids and self._col_visible.get(c, True)
        ]

        self.tree["displaycolumns"] = visible_ordered

        # Restaurar el ancho correcto a las visibles
        for cid in visible_ordered:
            orig_w = col_lookup[cid][2]
            self.tree.column(cid, width=orig_w, minwidth=40)

    def _toggle_column_picker(self):
        if self._col_picker and self._col_picker.winfo_exists():
            self._col_picker.destroy()
            self._col_picker = None
            return

        self._col_picker = ctk.CTkToplevel(self)
        self._col_picker.title("Configurar columnas")
        self._col_picker.geometry("420x480")
        self._col_picker.resizable(False, False)
        self._col_picker.attributes("-topmost", True)

        ctk.CTkLabel(self._col_picker, text="Columnas — Visibilidad y Copia SAP",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(padx=12, pady=(12, 2))
        ctk.CTkLabel(self._col_picker,
                     text="👁 Visible: se muestra en la tabla   📋 Copiar: se incluye al copiar para SAP",
                     text_color="gray", font=ctk.CTkFont(size=11)).pack(padx=12, pady=(0, 8))

        # Encabezado de columnas
        hdr = ctk.CTkFrame(self._col_picker, fg_color="transparent")
        hdr.pack(fill="x", padx=12, pady=(0, 2))
        ctk.CTkLabel(hdr, text="", width=64).pack(side="left")   # flechas
        ctk.CTkLabel(hdr, text="Columna", font=ctk.CTkFont(size=11, weight="bold"),
                     width=140, anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="👁 Ver", font=ctk.CTkFont(size=11, weight="bold"),
                     width=60, anchor="center").pack(side="left")
        ctk.CTkLabel(hdr, text="📋 SAP", font=ctk.CTkFont(size=11, weight="bold"),
                     width=60, anchor="center").pack(side="left")

        # Frame scrollable con la lista de columnas
        self._picker_list_frame = ctk.CTkScrollableFrame(self._col_picker, height=280)
        self._picker_list_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self._rebuild_picker_list()

        # Botones de acción
        btn_frame = ctk.CTkFrame(self._col_picker, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(btn_frame, text="Restaurar defecto", width=130, fg_color="gray40",
                      command=self._reset_columns).pack(side="left")
        ctk.CTkButton(btn_frame, text="Cerrar", width=80,
                      command=self._col_picker.destroy).pack(side="right")

    def _rebuild_picker_list(self):
        """Reconstruye la lista de columnas en el picker."""
        for w in self._picker_list_frame.winfo_children():
            w.destroy()

        col_lookup = {c[0]: c[1] for c in DEFAULT_COLUMNS}

        for idx, cid in enumerate(self._col_order):
            row = ctk.CTkFrame(self._picker_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            # Flechas arriba/abajo
            ctk.CTkButton(row, text="▲", width=28, height=24, fg_color="gray30",
                          command=lambda i=idx: self._move_col(i, -1)).pack(side="left", padx=(0, 2))
            ctk.CTkButton(row, text="▼", width=28, height=24, fg_color="gray30",
                          command=lambda i=idx: self._move_col(i, 1)).pack(side="left", padx=(0, 4))

            # Nombre columna
            ctk.CTkLabel(row, text=col_lookup.get(cid, cid), width=140,
                         anchor="w", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 4))

            # Checkbox visibilidad (👁)
            var_vis = ctk.BooleanVar(value=self._col_visible.get(cid, True))
            ctk.CTkCheckBox(row, text="", variable=var_vis, width=50,
                            command=lambda c=cid, v=var_vis: self._toggle_col_visible(c, v)
                            ).pack(side="left", padx=(4, 0))

            # Checkbox copiar (📋)
            var_copy = ctk.BooleanVar(value=self._col_copy.get(cid, False))
            ctk.CTkCheckBox(row, text="", variable=var_copy, width=50,
                            command=lambda c=cid, v=var_copy: self._toggle_col_copy(c, v)
                            ).pack(side="left", padx=(4, 0))

    def _move_col(self, index: int, direction: int):
        """Mueve una columna arriba (-1) o abajo (+1)."""
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._col_order):
            return
        self._col_order[index], self._col_order[new_index] = \
            self._col_order[new_index], self._col_order[index]
        self._apply_column_order()
        _save_column_prefs(self._col_order, self._col_visible, self._col_copy)
        self._rebuild_picker_list()

    def _toggle_col_visible(self, cid: str, var):
        """Muestra u oculta una columna en la tabla."""
        self._col_visible[cid] = var.get()
        self._apply_column_order()
        _save_column_prefs(self._col_order, self._col_visible, self._col_copy)

    def _toggle_col_copy(self, cid: str, var):
        """Incluye o excluye una columna del clipboard SAP."""
        self._col_copy[cid] = var.get()
        _save_column_prefs(self._col_order, self._col_visible, self._col_copy)

    def _reset_columns(self):
        """Restaura orden, visibilidad y copia por defecto."""
        self._col_order = [c[0] for c in DEFAULT_COLUMNS]
        self._col_visible = {c[0]: c[4] for c in DEFAULT_COLUMNS}
        self._col_copy = {c[0]: c[5] for c in DEFAULT_COLUMNS}
        self._apply_column_order()
        _save_column_prefs(self._col_order, self._col_visible, self._col_copy)
        self._rebuild_picker_list()
        self.lbl_action_msg.configure(text="✓ Columnas restauradas a valores por defecto", text_color="green")

    # ── Carga de datos ──────────────────────────────────────────────────

    def _is_cm(self) -> bool:
        """Retorna True si la OC usa columnas con homologación SAP (CM o PRIVADA)."""
        tipo = (self._oc.tipo_oc or "").upper() if self._oc else ""
        return tipo in ("CM", "PRIVADA")

    def _setup_tree_columns(self):
        """Configura displaycolumns según el tipo de OC (CM vs no-CM)."""
        if self._is_cm():
            # CM: aplicar orden y visibilidad guardados
            self._apply_column_order()
            visible_ordered = [
                c for c in self._col_order
                if c in {x[0] for x in DEFAULT_COLUMNS} and self._col_visible.get(c, True)
            ]
            self.tree["displaycolumns"] = visible_ordered
        else:
            # No-CM: mostrar solo columnas no-CM
            noncm_cols = [c[0] for c in NONCM_COLUMNS]
            self.tree["displaycolumns"] = noncm_cols

    def load_oc(self, oc: OrdenCompra, lineas: list):
        self._oc = oc
        self._lineas = lineas

        # Cabecera
        tipo_label = f" [{oc.tipo_oc}]" if oc.tipo_oc and oc.tipo_oc != "CM" else ""
        self.lbl_title.configure(text=f"OC: {oc.codigo_oc}{tipo_label}")
        self.lbl_codigo.configure(text=oc.codigo_oc)
        self.lbl_estado_mp.configure(text=oc.estado_mp)
        total_fmt = f"${oc.total:,.0f} {oc.moneda}"
        self.lbl_total.configure(text=total_fmt)
        self.lbl_comprador.configure(
            text=f"{oc.nombre_organismo}  |  {oc.nombre_unidad}  |  RUT: {oc.rut_unidad}"
        )
        fecha = oc.fecha_creacion[:10] if oc.fecha_creacion else ""
        self.lbl_fecha.configure(text=f"Fecha: {fecha}")
        self.lbl_cliente_sap.configure(text=f"Cliente SAP sugerido: {oc.cliente_sap_sugerido}")
        self.opt_estado.set(oc.estado_interno or "Nueva")

        self.entry_notas.delete(0, "end")
        if oc.notas:
            self.entry_notas.insert(0, oc.notas)

        # Reconfigurar columnas según tipo
        self._setup_tree_columns()

        # Advertencia homologación (solo CM)
        if self._is_cm():
            sin_homo = [l for l in lineas if l.estado_homologacion != "homologado"]
            if sin_homo:
                self.lbl_warn.configure(
                    text=f"⚠  {len(sin_homo)} línea(s) sin homologar — se excluirán del clipboard SAP  "
                         f"(correlativos: {[l.correlativo for l in sin_homo]})"
                )
                self.warn_frame.pack(fill="x", padx=20, pady=(0, 4),
                                     before=self.tree.master.master if hasattr(self.tree.master, 'master') else None)
            else:
                self.warn_frame.pack_forget()
        else:
            self.warn_frame.pack_forget()

        # Botones según tipo
        if self._is_cm():
            self.btn_copiar.pack(side="left", padx=(0, 10))
            if oc.estado_interno == "Ingresada":
                self.btn_marcar.configure(state="disabled", text="✓ Ya ingresada")
            else:
                self.btn_marcar.configure(state="normal", text="✓ Marcar como Ingresada")
        else:
            self.btn_copiar.pack_forget()
            if oc.estado_interno == "Ingresada":
                self.btn_marcar.configure(state="disabled", text="✓ Ya ingresada")
            else:
                self.btn_marcar.configure(state="normal", text="✓ Marcar como Ingresada")

        # Ocultar barra de asignación al cambiar OC
        self._assign_bar.pack_forget()
        self._sug_cache = {}

        # Poblar tabla
        self._populate_tree(lineas)
        self.lbl_action_msg.configure(text="")

        # Cargar sugerencias en background para no-CM
        if not self._is_cm():
            self._cargar_sugerencias_noncm()

    def _populate_tree(self, lineas: list):
        self.tree.delete(*self.tree.get_children())

        if self._is_cm():
            self._populate_cm(lineas)
        else:
            self._populate_noncm(lineas)

    def _populate_cm(self, lineas: list):
        """Poblar tabla con datos CM (homologación)."""
        for linea in lineas:
            estado = linea.estado_homologacion
            colors = HOMO_COLORS.get(estado, HOMO_COLORS["pendiente"])
            badge = colors["badge"]

            cant_oc = f"{linea.cantidad:g}" if linea.cantidad is not None else ""
            cant_sap = f"{linea.cantidad_sap:g}" if linea.cantidad_sap is not None else ""
            precio_sap = f"${linea.precio_sap:,.2f}" if linea.precio_sap is not None else ""
            f_emp = f"{linea.factor_empaque:g}" if linea.factor_empaque else "1"

            row_tag = f"homo_{estado}"
            # Llenar TODAS las columnas (vacío para las que no aplican)
            self.tree.insert("", "end", tags=(row_tag,), values=(
                linea.correlativo,                    # #
                linea.codigo_mp or "",                # codigo_mp
                (linea.producto or "")[:60],          # descripcion_mp
                "",                                   # producto (no-CM only)
                "",                                   # espec_comprador (no-CM only)
                linea.itemcode_sap or "—",            # itemcode
                (linea.descripcion_sap or "—")[:50],  # desc_sap
                "",                                   # sug_top (no aplica CM)
                cant_oc,                              # cant_oc
                cant_sap,                             # cant_sap
                precio_sap,                           # precio_sap
                f_emp,                                # f_emp
                "",                                   # unidad (no-CM only)
                "",                                   # precio_neto (no-CM only)
                "",                                   # total (no-CM only)
                f"{badge} {estado.replace('_', ' ').title()}"  # estado
            ))

        self.tree.tag_configure("homo_homologado",       background="#1a3a1a", foreground="#c8e6c9")
        self.tree.tag_configure("homo_sin_homologacion", background="#3a1a1a", foreground="#ffcdd2")
        self.tree.tag_configure("homo_pendiente",        background="#2a2a1a", foreground="#fff9c4")
        self.tree.tag_configure("homo_manual",           background="#1a2a3a", foreground="#bbdefb")

    def _populate_noncm(self, lineas: list):
        """Poblar tabla con datos no-CM (descripciones + SAP si asignado)."""
        for linea in lineas:
            cant = f"{linea.cantidad:g}" if linea.cantidad is not None else ""
            precio = f"${linea.precio_neto:,.2f}" if linea.precio_neto else ""
            total = f"${linea.total:,.0f}" if linea.total else ""
            itemcode = linea.itemcode_sap or ""
            desc_sap = (linea.descripcion_sap or "")[:50]

            estado = linea.estado_homologacion or "pendiente"
            if itemcode:
                tag = "homo_manual"
                badge = "✓ " + itemcode
            else:
                tag = "noncm"
                badge = "Sin asignar"

            # Llenar TODAS las columnas (vacío para las que no aplican)
            self.tree.insert("", "end", iid=str(linea.correlativo),
                             tags=(tag,), values=(
                linea.correlativo,                    # #
                "",                                   # codigo_mp (CM only)
                "",                                   # descripcion_mp (CM only)
                linea.producto or "",                 # producto
                linea.especificacion_comprador or "", # espec_comprador
                itemcode,                             # itemcode
                desc_sap,                             # desc_sap
                "",                                   # sug_top (se llena en background)
                cant,                                 # cant_oc
                "",                                   # cant_sap (CM only)
                "",                                   # precio_sap (CM only)
                "",                                   # f_emp (CM only)
                linea.unidad or "",                   # unidad
                precio,                               # precio_neto
                total,                                # total
                badge,                                # estado
            ))

        self.tree.tag_configure("noncm", background="#1a2a3a", foreground="#bbdefb")
        self.tree.tag_configure("homo_manual", background="#1a3a2a", foreground="#a5d6a7")

    # ── Sugerencias para no-CM ───────────────────────────────────────

    def _on_tree_select(self, event):
        """Al seleccionar una línea no-CM actualiza la barra de asignación."""
        if self._is_cm():
            self._assign_bar.pack_forget()
            return

        sel = self.tree.selection()
        if not sel:
            self._assign_bar.pack_forget()
            return

        correlativo_str = sel[0]
        linea = next((l for l in self._lineas if str(l.correlativo) == correlativo_str), None)
        if not linea:
            return

        self._selected_correlativo = int(correlativo_str)

        texto = linea.especificacion_comprador or linea.producto or ""
        lbl = f"Línea {linea.correlativo}: {texto[:38]}…" if len(texto) > 38 \
              else f"Línea {linea.correlativo}: {texto}"
        self._lbl_linea_sel.configure(text=lbl)

        # Sugerencia del cache (ya cargada en background)
        sug = self._sug_cache.get(int(correlativo_str))
        if sug:
            stars = "★" * max(1, round(sug.score * 5))
            self._lbl_sug_top.configure(
                text=f"{sug.itemcode_sap}  {stars}", text_color="#64b5f6")
            self._btn_asignar.configure(state="normal")
        else:
            self._lbl_sug_top.configure(text="sin sugerencia", text_color="gray")
            self._btn_asignar.configure(state="disabled")

        self._lbl_assign_msg.configure(text="")
        self._entry_itemcode_manual.delete(0, "end")
        # Mostrar la barra justo encima de la tabla
        self._assign_bar.pack(fill="x", padx=20, pady=(2, 2),
                              before=self._table_frame)

    def _cargar_sugerencias_noncm(self):
        """Carga la sugerencia top para cada línea no-CM en background."""
        import threading
        lineas_snap = list(self._lineas)
        oc_codigo   = self._oc.codigo_oc if self._oc else None

        def _worker():
            try:
                from app.services.licitaciones_service import get_licitaciones_service
                svc = get_licitaciones_service()
                results = {}
                for linea in lineas_snap:
                    if linea.itemcode_sap:
                        continue
                    texto = " ".join(filter(None, [
                        linea.especificacion_comprador,
                        linea.producto,
                    ]))
                    if not texto.strip():
                        continue
                    sugs = svc.buscar_sugerencias(texto, max_results=1)
                    if sugs:
                        results[linea.correlativo] = sugs[0]
                self.after(0, lambda: self._aplicar_sugerencias_en_tabla(results, oc_codigo))
            except Exception as e:
                logger.warning(f"Error cargando sugerencias no-CM: {e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_sugerencias_en_tabla(self, results: dict, oc_codigo: str):
        """Pone el texto de sugerencia en la columna sug_top del treeview."""
        if not self._oc or self._oc.codigo_oc != oc_codigo:
            return
        self._sug_cache.update(results)

        col_ids = [c[0] for c in ALL_COLUMNS_INIT]
        idx_sug = col_ids.index("sug_top")

        for correlativo, sug in results.items():
            iid = str(correlativo)
            if not self.tree.exists(iid):
                continue
            stars = "★" * max(1, round(sug.score * 5))
            vals = list(self.tree.item(iid, "values"))
            vals[idx_sug] = f"{sug.itemcode_sap}  {stars}"
            self.tree.item(iid, values=vals)

        # Si hay fila seleccionada, refrescar label en la barra
        sel = self.tree.selection()
        if sel:
            try:
                corr_sel = int(sel[0])
                if corr_sel in results:
                    sug = results[corr_sel]
                    stars = "★" * max(1, round(sug.score * 5))
                    self._lbl_sug_top.configure(
                        text=f"{sug.itemcode_sap}  {stars}", text_color="#64b5f6")
                    self._btn_asignar.configure(state="normal")
            except (ValueError, KeyError):
                pass

    # ── Helper compartido de escritura ──────────────────────────────────

    def _set_itemcode_linea(self, correlativo: int, itemcode, desc_sap: str):
        """Escribe itemcode en BD, actualiza modelo local y fila del tree."""
        from app.db import get_connection
        from datetime import datetime
        estado_nuevo = "manual" if itemcode else "pendiente"
        conn = get_connection()
        try:
            conn.execute("""
                UPDATE oc_detalle SET
                    itemcode_sap = ?, descripcion_sap = ?,
                    estado_homologacion = ?, updated_at = ?
                WHERE codigo_oc = ? AND correlativo = ?
            """, (itemcode, desc_sap or None, estado_nuevo,
                  datetime.now().isoformat(), self._oc.codigo_oc, correlativo))
            conn.commit()
        finally:
            conn.close()

        for l in self._lineas:
            if l.correlativo == correlativo:
                l.itemcode_sap = itemcode
                l.descripcion_sap = desc_sap
                l.estado_homologacion = estado_nuevo
                break

        iid = str(correlativo)
        if self.tree.exists(iid):
            vals = list(self.tree.item(iid, "values"))
            col_ids = [c[0] for c in ALL_COLUMNS_INIT]
            vals[col_ids.index("itemcode")] = itemcode or ""
            vals[col_ids.index("desc_sap")]  = (desc_sap or "")[:50]
            vals[col_ids.index("estado")]    = f"✓ {itemcode}" if itemcode else "Sin asignar"
            tag = "homo_manual" if itemcode else "noncm"
            self.tree.item(iid, values=vals, tags=(tag,))

    # ── Acciones de asignación ──────────────────────────────────────────

    def _asignar_sugerencia(self):
        """Asigna la sugerencia top del cache a la línea seleccionada."""
        correlativo = getattr(self, "_selected_correlativo", None)
        if not correlativo or not self._oc:
            return
        sug = self._sug_cache.get(correlativo)
        if not sug:
            self._lbl_assign_msg.configure(text="Sin sugerencia disponible", text_color="orange")
            return
        itemcode = sug.itemcode_sap
        desc_sap  = sug.descripcion_sap or sug.descripcion_match or ""
        self._set_itemcode_linea(correlativo, itemcode, desc_sap)
        self._lbl_assign_msg.configure(text=f"✓ {itemcode}", text_color="green")
        self._lbl_sug_top.configure(text=f"{itemcode} ✓", text_color="#4caf50")
        logger.info(f"Asignado (sugerencia) {itemcode} → línea {correlativo} de {self._oc.codigo_oc}")

    def _asignar_manual(self):
        """Asigna un ItemCode escrito a mano a la línea seleccionada."""
        itemcode = self._entry_itemcode_manual.get().strip().upper()
        if not itemcode:
            self._lbl_assign_msg.configure(text="Escriba un ItemCode", text_color="orange")
            return
        correlativo = getattr(self, "_selected_correlativo", None)
        if not correlativo or not self._oc:
            self._lbl_assign_msg.configure(text="Seleccione una línea", text_color="orange")
            return

        desc_sap = ""
        try:
            from app.services.maestra_service import get_maestra_service
            mat = get_maestra_service().lookup(itemcode)
            if mat:
                desc_sap = mat.descripcion
        except Exception:
            pass

        self._set_itemcode_linea(correlativo, itemcode, desc_sap)
        self._entry_itemcode_manual.delete(0, "end")
        self._lbl_assign_msg.configure(text=f"✓ {itemcode}", text_color="green")
        logger.info(f"Asignado (manual) {itemcode} → línea {correlativo} de {self._oc.codigo_oc}")

    def _limpiar_asignacion(self):
        """Elimina el ItemCode asignado a la línea seleccionada."""
        correlativo = getattr(self, "_selected_correlativo", None)
        if not correlativo or not self._oc:
            self._lbl_assign_msg.configure(text="Seleccione una línea", text_color="orange")
            return
        self._set_itemcode_linea(correlativo, None, "")
        self._lbl_assign_msg.configure(text="Asignación eliminada", text_color="gray")
        # Restaurar sugerencia en barra si existe en cache
        sug = self._sug_cache.get(correlativo)
        if sug:
            stars = "★" * max(1, round(sug.score * 5))
            self._lbl_sug_top.configure(
                text=f"{sug.itemcode_sap}  {stars}", text_color="#64b5f6")
            self._btn_asignar.configure(state="normal")
        logger.info(f"Asignación limpiada en línea {correlativo} de {self._oc.codigo_oc}")

    def _apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                         background="#2b2b2b", foreground="white",
                         fieldbackground="#2b2b2b", rowheight=26,
                         font=("Segoe UI", 11))
        style.configure("Treeview.Heading",
                         background="#1f1f1f", foreground="white",
                         font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#1565C0")])

    # ── Acciones ────────────────────────────────────────────────────────

    def _cambiar_estado(self, estado: str):
        if not self._oc:
            return
        if self._oc.estado_interno == "Ingresada" and estado != "Ingresada":
            if not messagebox.askyesno("Cambiar estado",
                                        "Esta OC ya fue marcada como Ingresada. ¿Desea cambiar el estado?"):
                self.opt_estado.set("Ingresada")
                return
        from app.repositories import oc_repository
        oc_repository.actualizar_estado(self._oc.codigo_oc, estado)
        self._oc.estado_interno = estado
        if estado == "Ingresada":
            self.btn_marcar.configure(state="disabled", text="✓ Ya ingresada")
        else:
            self.btn_marcar.configure(state="normal", text="✓ Marcar como Ingresada")

    def _marcar_ingresada(self):
        if not self._oc:
            return
        if not messagebox.askyesno("Marcar como Ingresada",
                                    f"¿Marcar la OC {self._oc.codigo_oc} como ingresada en SAP?\n"
                                    "Esto guardará la fecha actual de ingreso."):
            return
        from app.repositories import oc_repository
        oc_repository.marcar_ingresada(self._oc.codigo_oc)
        self._oc.estado_interno = "Ingresada"
        self.opt_estado.set("Ingresada")
        self.btn_marcar.configure(state="disabled", text="✓ Ya ingresada")
        self.lbl_action_msg.configure(text="✓ OC marcada como ingresada.", text_color="green")

    def _guardar_notas(self):
        if not self._oc:
            return
        notas = self.entry_notas.get().strip()
        from app.repositories import oc_repository
        oc_repository.guardar_notas(self._oc.codigo_oc, notas)
        self._oc.notas = notas
        self.lbl_action_msg.configure(text="✓ Notas guardadas.", text_color="green")

    def _copiar_sap(self):
        if not self._lineas:
            return

        # Columnas marcadas para copiar, en el orden del usuario
        visible_cols = [c for c in self._col_order if self._col_copy.get(c, False)]
        if not visible_cols:
            messagebox.showwarning("Sin columnas para copiar",
                                   "Ninguna columna está marcada para copiar.\n"
                                   "Usa ⚙ Columnas → columna 📋 para activar las que quieres.")
            return

        # Mapa: id columna → función que extrae el valor de una LineaOC
        # Números usan COMA decimal (formato SAP Chile: 336,68 no 336.68)
        def _fmt_cant(v):
            if v is None: return ""
            if v == int(v): return str(int(v))
            return f"{v:.4f}".rstrip('0').rstrip('.').replace('.', ',')

        def _fmt_precio(v):
            return f"{v:.2f}".replace('.', ',')

        col_extractors = {
            "#":              lambda l: str(l.correlativo),
            "codigo_mp":      lambda l: l.codigo_mp or "",
            "descripcion_mp": lambda l: (l.producto or "")[:60],
            "itemcode":       lambda l: l.itemcode_sap or "",
            "desc_sap":       lambda l: (l.descripcion_sap or "")[:50],
            "cant_oc":        lambda l: _fmt_cant(l.cantidad),
            "cant_sap":       lambda l: _fmt_cant(l.cantidad_sap if l.cantidad_sap is not None else l.cantidad),
            "precio_sap":     lambda l: _fmt_precio(l.precio_sap if l.precio_sap is not None else l.precio_neto),
            "f_emp":          lambda l: f"{l.factor_empaque:g}".replace('.', ',') if l.factor_empaque else "1",
            "estado":         lambda l: l.estado_homologacion,
        }

        filas = []
        excluidos = []
        for linea in self._lineas:
            if linea.estado_homologacion != "homologado" or not linea.itemcode_sap:
                excluidos.append(linea.correlativo)
                continue
            valores = [col_extractors[c](linea) for c in visible_cols if c in col_extractors]
            filas.append("\t".join(valores))

        if not filas:
            messagebox.showwarning(
                "Sin líneas homologadas",
                "No hay líneas homologadas para copiar.\n"
                "Importe el catálogo HOMOLOGACION.xlsx en Configuración."
            )
            return

        if excluidos:
            resp = messagebox.askyesno(
                "Líneas excluidas",
                f"Se excluirán {len(excluidos)} línea(s) sin homologar "
                f"(correlativos: {excluidos}).\n\n¿Copiar igualmente las líneas homologadas?"
            )
            if not resp:
                return

        texto = "\r\n".join(filas)
        ok = copiar_al_portapapeles(texto, root=self.winfo_toplevel())
        if ok:
            self.lbl_action_msg.configure(
                text=f"📋 {len(filas)} línea(s) copiadas ({len(visible_cols)} col.). Listo para pegar en SAP.",
                text_color="green"
            )
        else:
            messagebox.showerror("Error", "No se pudo copiar al portapapeles.")

    def _abrir_en_portal(self):
        """Abre la OC en el portal de Mercado Público (permite descargar PDF)."""
        if not self._oc:
            return
        import webbrowser
        url = (
            "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
            f"DetailsPurchaseOrder.aspx?codigoOC={self._oc.codigo_oc}"
        )
        webbrowser.open(url)

    def _exportar_excel(self):
        if not self._oc or not self._lineas:
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"OC_{self._oc.codigo_oc}.xlsx"
        )
        if not path:
            return
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Detalle OC"

            ws.append(["OC", self._oc.codigo_oc])
            ws.append(["Comprador", self._oc.nombre_organismo])
            ws.append(["Unidad", self._oc.nombre_unidad])
            ws.append(["RUT Unidad", self._oc.rut_unidad])
            ws.append(["Cliente SAP", self._oc.cliente_sap_sugerido])
            ws.append(["Total", self._oc.total])
            ws.append(["Estado MP", self._oc.estado_mp])
            ws.append([])

            headers = ["#", "Cód.MP", "Producto", "ItemCode SAP", "Descripción SAP",
                       "Cant OC", "F.Emp", "Cant SAP", "Precio Neto", "Precio SAP", "Estado Homo"]
            ws.append(headers)

            for l in self._lineas:
                ws.append([
                    l.correlativo, l.codigo_mp, l.producto,
                    l.itemcode_sap or "", l.descripcion_sap or "",
                    l.cantidad, l.factor_empaque, l.cantidad_sap,
                    l.precio_neto, l.precio_sap, l.estado_homologacion
                ])

            wb.save(path)
            self.lbl_action_msg.configure(text=f"✓ Exportado: {path}", text_color="green")
        except Exception as e:
            messagebox.showerror("Error exportando", str(e))
