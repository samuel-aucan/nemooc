"""
Bandeja principal de Órdenes de Compra.
Tabla con filtros, detalle expandido en panel inferior.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

try:
    from tkcalendar import DateEntry
    _HAS_CALENDAR = True
except ImportError:
    _HAS_CALENDAR = False

class _NullCartera:
    """Objeto nulo para clientes sin match en cartera."""
    cartera = ""
    razon = ""
    region_nombre = ""


ESTADO_COLORS = {
    "Pendiente":       "#FFC107",
    "Nueva":           "#2196F3",
    "Revisada":        "#9C27B0",
    "Lista para SAP":  "#FF9800",
    "Ingresada":       "#4CAF50",
    "Con error":       "#F44336",
}


class OcListFrame(ctk.CTkFrame):

    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._all_ocs = []
        self._detail_visible = False
        self._build()
        self._apply_styles()

    def _build(self):
        # ── Título + acciones globales ────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkLabel(top, text="Órdenes de Compra CM",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="↑ Exportar todo a Excel", width=160,
                      fg_color="gray40", command=self._exportar_todo).pack(side="right")
        ctk.CTkButton(top, text="⟳ Actualizar", width=110,
                      fg_color="gray30", command=self.refresh).pack(side="right", padx=(0, 8))

        # ── Filtros ──────────────────────────────────────────────────────
        filter_card = ctk.CTkFrame(self)
        filter_card.pack(fill="x", padx=20, pady=(0, 8))

        # Fila 1: búsqueda + estado interno + fechas
        row1 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(row1, text="Buscar:").pack(side="left", padx=(0, 4))
        self.entry_search = ctk.CTkEntry(row1, width=200, placeholder_text="Código OC, organismo...")
        self.entry_search.pack(side="left", padx=(0, 12))
        self.entry_search.bind("<Return>", lambda e: self._aplicar_filtros())

        ctk.CTkLabel(row1, text="Estado app:").pack(side="left", padx=(0, 4))
        self.opt_estado = ctk.CTkOptionMenu(
            row1,
            values=["Todos", "Pendiente", "Nueva", "Revisada", "Lista para SAP", "Ingresada", "Con error"],
            width=130, command=lambda _: self._aplicar_filtros()
        )
        self.opt_estado.set("Todos")
        self.opt_estado.pack(side="left", padx=(0, 12))

        self.var_filtrar_fechas = tk.BooleanVar(value=False)
        self.chk_fechas = ctk.CTkCheckBox(
            row1, text="Fecha:", variable=self.var_filtrar_fechas,
            width=70, command=self._on_toggle_fechas
        )
        self.chk_fechas.pack(side="left", padx=(0, 4))
        self.date_desde = self._make_date(row1)
        self.date_desde.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row1, text="→").pack(side="left", padx=(0, 4))
        self.date_hasta = self._make_date(row1)
        self.date_hasta.pack(side="left", padx=(0, 12))
        self._set_date_widgets_state(False)

        # Fila 2: Estado MP + Cartera + botones
        row2 = ctk.CTkFrame(filter_card, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(row2, text="Estado MP:").pack(side="left", padx=(0, 4))
        self.opt_estado_mp = ctk.CTkOptionMenu(
            row2, values=["Todos"], width=170,
            command=lambda _: self._aplicar_filtros()
        )
        self.opt_estado_mp.set("Todos")
        self.opt_estado_mp.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row2, text="Tipo:").pack(side="left", padx=(0, 4))
        self.opt_tipo = ctk.CTkOptionMenu(
            row2, values=["Todos"], width=80,
            command=lambda _: self._aplicar_filtros()
        )
        self.opt_tipo.set("Todos")
        self.opt_tipo.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row2, text="Cartera:").pack(side="left", padx=(0, 4))
        self.opt_cartera = ctk.CTkOptionMenu(
            row2, values=["Todas"], width=120,
            command=lambda _: self._aplicar_filtros()
        )
        self.opt_cartera.set("Todas")
        self.opt_cartera.pack(side="left", padx=(0, 12))

        ctk.CTkButton(row2, text="Filtrar", width=80,
                      command=self._aplicar_filtros).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row2, text="Limpiar", width=80,
                      fg_color="gray30", command=self._limpiar_filtros).pack(side="left")

        # Contador
        self.lbl_count = ctk.CTkLabel(row2, text="", text_color="gray",
                                       font=ctk.CTkFont(size=12))
        self.lbl_count.pack(side="right")

        # ── PanedWindow (tabla arriba / detalle abajo) ────────────────────
        self.paned = tk.PanedWindow(self, orient="vertical",
                                     bg="#1a1a1a", sashwidth=6, sashrelief="flat")
        self.paned.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        # Panel superior: tabla OCs
        top_panel = ctk.CTkFrame(self.paned)
        self.paned.add(top_panel, minsize=160)

        cols = ("estado", "estado_mp", "tipo_oc", "codigo_oc", "fecha", "organismo", "rut", "cliente_sap",
                "cartera", "region", "total", "lineas", "ingresada")
        self.tree = ttk.Treeview(top_panel, columns=cols, show="headings", selectmode="browse")

        col_def = [
            ("estado",      "Estado app",      100, "center"),
            ("estado_mp",   "Estado MP",       150, "w"),
            ("tipo_oc",     "Tipo",             50, "center"),
            ("codigo_oc",   "Código OC",       160, "w"),
            ("fecha",       "Fecha envío",      90, "center"),
            ("organismo",   "Cliente",          200, "w"),
            ("rut",         "RUT",              100, "center"),
            ("cliente_sap", "Cliente SAP",      100, "center"),
            ("cartera",     "Cartera",           70, "center"),
            ("region",      "Región",           140, "w"),
            ("total",       "Total CLP",        110, "e"),
            ("lineas",      "Líneas",            60, "center"),
            ("ingresada",   "Ingresada",        130, "center"),
        ]
        for cid, hdr, w, anchor in col_def:
            self.tree.heading(cid, text=hdr, command=lambda c=cid: self._sort(c))
            self.tree.column(cid, width=w, minwidth=40, anchor=anchor)

        vsb = ttk.Scrollbar(top_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Panel inferior: detalle (inicialmente oculto)
        from app.ui.frames.oc_detail_frame import OcDetailFrame
        self.detail_panel = ctk.CTkFrame(self.paned)
        self.detail_frame = OcDetailFrame(
            self.detail_panel, self.app_state,
            on_back=self._hide_detail
        )
        self.detail_frame.pack(fill="both", expand=True)

    # ------------------------------------------------------------------

    def on_show(self):
        """Llamado al navegar a esta pantalla."""
        self._cargar_opciones_filtros()
        self.refresh()

    def _cargar_opciones_filtros(self):
        """Carga los valores únicos de Estado MP, Tipo y Cartera en los dropdowns."""
        from app.repositories import oc_repository
        from app.services.cartera_service import get_cartera_service

        # Estado MP
        estados_mp = oc_repository.get_distinct_estados_mp()
        self.opt_estado_mp.configure(values=["Todos"] + estados_mp)
        if self.opt_estado_mp.get() not in (["Todos"] + estados_mp):
            self.opt_estado_mp.set("Todos")

        # Tipo OC
        tipos = oc_repository.get_distinct_tipos()
        self.opt_tipo.configure(values=["Todos"] + tipos)
        if self.opt_tipo.get() not in (["Todos"] + tipos):
            self.opt_tipo.set("Todos")

        # Cartera — valores únicos del cache
        cache = get_cartera_service()._cache
        carteras = sorted({c.cartera for c in cache.values() if c.cartera})
        self.opt_cartera.configure(values=["Todas"] + carteras)
        if self.opt_cartera.get() not in (["Todas"] + carteras):
            self.opt_cartera.set("Todas")

    def refresh(self):
        """Recarga las OCs desde la BD y actualiza la tabla."""
        self._aplicar_filtros()

    def _on_toggle_fechas(self):
        """Activa o desactiva los widgets de fecha según el checkbox."""
        self._set_date_widgets_state(self.var_filtrar_fechas.get())
        self._aplicar_filtros()

    def _set_date_widgets_state(self, enabled: bool):
        """Habilita o deshabilita los selectores de fecha."""
        state = "normal" if enabled else "disabled"
        try:
            self.date_desde.configure(state=state)
            self.date_hasta.configure(state=state)
        except Exception:
            pass

    def _aplicar_filtros(self):
        from app.repositories import oc_repository
        from app.services.cartera_service import get_cartera_service

        estado = self.opt_estado.get()
        estado_mp = self.opt_estado_mp.get()
        tipo_sel = self.opt_tipo.get()
        cartera_sel = self.opt_cartera.get()
        busqueda = self.entry_search.get().strip()

        usar_fechas = self.var_filtrar_fechas.get()
        desde = self._get_date(self.date_desde) if usar_fechas else None
        hasta = self._get_date(self.date_hasta) if usar_fechas else None

        ocs = oc_repository.get_all_ocs(
            estado=estado if estado != "Todos" else None,
            estado_mp=estado_mp if estado_mp != "Todos" else None,
            tipo_oc=tipo_sel if tipo_sel != "Todos" else None,
            fecha_desde=desde or None,
            fecha_hasta=hasta or None,
            busqueda=busqueda or None,
        )

        # Filtro por cartera (en memoria, via cartera_service)
        if cartera_sel and cartera_sel != "Todas":
            svc = get_cartera_service()
            ocs = [oc for oc in ocs
                   if (svc.lookup(oc.cliente_sap_sugerido) or _NullCartera()).cartera == cartera_sel]

        self._all_ocs = ocs
        self._poblar_tabla(ocs)
        self.lbl_count.configure(text=f"{len(ocs)} OC(s)")

    def _poblar_tabla(self, ocs):
        from app.services.cartera_service import get_cartera_service
        cartera_svc = get_cartera_service()

        self.tree.delete(*self.tree.get_children())
        for oc in ocs:
            fecha = oc.fecha_envio[:10] if oc.fecha_envio else ""
            total = f"${oc.total:,.0f}" if oc.total else "$0"
            ingresada = oc.fecha_ingreso[:10] if oc.fecha_ingreso else ""
            tag = f"estado_{oc.estado_interno.lower().replace(' ', '_')}"

            # Lookup en cartera para enriquecer datos
            info = cartera_svc.lookup(oc.cliente_sap_sugerido)
            nombre = (info.razon[:35] if info else None) or (oc.nombre_organismo[:35] if oc.nombre_organismo else "")
            cartera_val = info.cartera if info else ""
            region_val = info.region_nombre[:30] if info else ""

            self.tree.insert("", "end", iid=oc.codigo_oc, tags=(tag,), values=(
                oc.estado_interno,
                oc.estado_mp or "",
                oc.tipo_oc or "",
                oc.codigo_oc,
                fecha,
                nombre,
                oc.rut_unidad,
                oc.cliente_sap_sugerido,
                cartera_val,
                region_val,
                total,
                oc.cantidad_lineas,
                ingresada,
            ))

        # Colores por estado
        for estado, color in ESTADO_COLORS.items():
            tag = f"estado_{estado.lower().replace(' ', '_')}"
            try:
                self.tree.tag_configure(tag, foreground=color)
            except Exception:
                pass

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        codigo_oc = sel[0]
        self._cargar_detalle(codigo_oc)

    def _cargar_detalle(self, codigo_oc: str):
        from app.repositories import oc_repository
        oc = oc_repository.get_oc(codigo_oc)
        lineas = oc_repository.get_lineas(codigo_oc)
        if oc:
            self.detail_frame.load_oc(oc, lineas)
            if not self._detail_visible:
                self.paned.add(self.detail_panel, minsize=300)
                self._detail_visible = True

    def _hide_detail(self):
        if self._detail_visible:
            self.paned.remove(self.detail_panel)
            self._detail_visible = False

    def _limpiar_filtros(self):
        self.entry_search.delete(0, "end")
        self.opt_estado.set("Todos")
        self.opt_estado_mp.set("Todos")
        self.opt_tipo.set("Todos")
        self.opt_cartera.set("Todas")
        self.var_filtrar_fechas.set(False)
        self._set_date_widgets_state(False)
        self._aplicar_filtros()

    def _sort(self, col: str):
        """Ordena la tabla por columna."""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        data.sort()
        for idx, (_, k) in enumerate(data):
            self.tree.move(k, "", idx)

    def _exportar_todo(self):
        if not self._all_ocs:
            messagebox.showinfo("Exportar", "No hay OCs para exportar con los filtros actuales.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="OCs_NemoChile.xlsx"
        )
        if not path:
            return
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "OCs CM"
            from app.services.cartera_service import get_cartera_service
            cartera_svc = get_cartera_service()
            headers = ["Estado", "Código OC", "Fecha", "Cliente", "Cartera", "Región",
                       "RUT", "Cliente SAP", "Total", "Moneda", "Líneas",
                       "Estado MP", "Fecha Ingreso", "Notas"]
            ws.append(headers)
            for oc in self._all_ocs:
                info = cartera_svc.lookup(oc.cliente_sap_sugerido)
                nombre = (info.razon if info else None) or oc.nombre_organismo or ""
                ws.append([
                    oc.estado_interno, oc.codigo_oc,
                    oc.fecha_envio[:10] if oc.fecha_envio else "",
                    nombre,
                    info.cartera if info else "",
                    info.region_nombre if info else "",
                    oc.rut_unidad, oc.cliente_sap_sugerido,
                    oc.total, oc.moneda, oc.cantidad_lineas,
                    oc.estado_mp,
                    oc.fecha_ingreso[:10] if oc.fecha_ingreso else "",
                    oc.notas or ""
                ])
            wb.save(path)
            messagebox.showinfo("Exportación completada", f"Archivo guardado:\n{path}")
        except Exception as e:
            messagebox.showerror("Error exportando", str(e))

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                         background="#2b2b2b", foreground="white",
                         fieldbackground="#2b2b2b", rowheight=28,
                         font=("Segoe UI", 11))
        style.configure("Treeview.Heading",
                         background="#1f1f1f", foreground="white",
                         font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#1565C0")])

    def _make_date(self, parent):
        if _HAS_CALENDAR:
            return DateEntry(parent, width=11, date_pattern="yyyy-mm-dd",
                             background="gray20", foreground="white",
                             borderwidth=2, locale="es_CL")
        e = ctk.CTkEntry(parent, width=100, placeholder_text="YYYY-MM-DD")
        return e

    def _get_date(self, widget) -> str:
        try:
            if _HAS_CALENDAR and isinstance(widget, DateEntry):
                return widget.get_date().strftime("%Y-%m-%d")
            return widget.get().strip()
        except Exception:
            return ""
