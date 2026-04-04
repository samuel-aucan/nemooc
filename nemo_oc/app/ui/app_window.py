"""
Ventana principal de NemoOC.
Sidebar de navegación + área de contenido + barra de estado.
"""
import customtkinter as ctk
import tkinter as tk
import logging

logger = logging.getLogger(__name__)

NAV_WIDTH = 200


class AppState:
    """Estado global compartido entre frames."""
    def __init__(self, config):
        self.config = config


class AppWindow(ctk.CTk):

    def __init__(self, config):
        super().__init__()
        self.app_state = AppState(config)

        # Configuración de ventana
        self.title("NemoOC — Gestión Órdenes de Compra")
        self.geometry("1280x800")
        self.minsize(900, 600)

        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme(config.color_theme or "blue")

        self._build()
        self._show_frame("oc_list")

        # Auto-sync al iniciar si está configurado
        if config.auto_sync:
            self.after(1500, self._auto_sync)

        # Auto-sync periódico
        self._schedule_periodic_sync()

    def _build(self):
        # Layout raíz: sidebar | contenido
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)  # status bar

        # ── Sidebar ──────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=NAV_WIDTH, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self._build_sidebar()

        # ── Área de contenido ────────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self._frames = {}
        self._build_frames()

        # ── Barra de estado ──────────────────────────────────────────────
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="gray15")
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.lbl_status = ctk.CTkLabel(
            self.status_bar, text="Listo", anchor="w",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.lbl_status.pack(side="left", padx=12)
        self.lbl_status_right = ctk.CTkLabel(
            self.status_bar, text="", anchor="e",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.lbl_status_right.pack(side="right", padx=12)
        self._update_status()

    def _build_sidebar(self):
        # Logo / título
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", pady=(20, 16))
        ctk.CTkLabel(
            logo_frame, text="NemoOC",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).pack()
        ctk.CTkLabel(
            logo_frame, text="Mercado Público",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack()

        ctk.CTkFrame(self.sidebar, height=1, fg_color="gray30").pack(fill="x", padx=16, pady=(0, 12))

        # Botones de navegación
        self._nav_buttons = {}
        nav_items = [
            ("oc_list",   "📋  Órdenes CM"),
            ("import",    "⬇  Importar"),
            ("config",    "⚙  Configuración"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                fg_color="transparent",
                hover_color="gray25",
                height=40,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self._show_frame(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons[key] = btn

        # Separador inferior y última sync
        ctk.CTkFrame(self.sidebar, height=1, fg_color="gray30").pack(fill="x", padx=16, pady=(12, 8))
        self.lbl_last_sync = ctk.CTkLabel(
            self.sidebar,
            text=self._last_sync_text(),
            font=ctk.CTkFont(size=10),
            text_color="gray",
            wraplength=NAV_WIDTH - 24,
        )
        self.lbl_last_sync.pack(padx=12)

    def _build_frames(self):
        from app.ui.frames.oc_list_frame import OcListFrame
        from app.ui.frames.import_frame import ImportFrame
        from app.ui.frames.config_frame import ConfigFrame

        self._frames["oc_list"] = OcListFrame(self.content, self.app_state)
        self._frames["import"] = ImportFrame(
            self.content, self.app_state,
            on_sync_done=self._on_sync_done
        )
        self._frames["config"] = ConfigFrame(self.content, self.app_state)

        for frame in self._frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

    def _show_frame(self, key: str):
        # Actualizar botones activos
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color="gray25")
            else:
                btn.configure(fg_color="transparent")

        # Mostrar frame
        for k, frame in self._frames.items():
            if k == key:
                frame.tkraise()
                if hasattr(frame, "on_show"):
                    frame.on_show()

    def _on_sync_done(self):
        """Callback cuando la sincronización termina."""
        from datetime import datetime
        from app.config import save_config
        self.app_state.config.last_sync = datetime.now().isoformat()
        save_config(self.app_state.config)
        self.lbl_last_sync.configure(text=self._last_sync_text())
        self._update_status()
        # Auto-navegar a lista de OCs
        self._show_frame("oc_list")

    def _auto_sync(self):
        """Ejecuta auto-sync al iniciar si está configurado."""
        import_frame = self._frames.get("import")
        if import_frame and hasattr(import_frame, "auto_sync_if_configured"):
            import_frame.auto_sync_if_configured()

    def _schedule_periodic_sync(self):
        """Programa el próximo sync periódico."""
        interval_min = self.app_state.config.auto_sync_interval or 15
        interval_ms = interval_min * 60 * 1000
        self.after(interval_ms, self._periodic_sync)

    def _periodic_sync(self):
        """Sync automático periódico: solo si está habilitado y no hay sync en curso."""
        if not self.app_state.config.auto_sync_interval:
            return
        import_frame = self._frames.get("import")
        if import_frame and not getattr(import_frame, "_polling", False):
            import_frame._set_quick(0)  # Solo hoy
            import_frame._iniciar_sync()
            self.lbl_status.configure(text="Auto-sync: buscando OCs nuevas de hoy...")
        # Reprogramar siempre
        self._schedule_periodic_sync()

    def _update_status(self):
        """Actualiza la barra de estado con stats de la BD."""
        try:
            from app.repositories.oc_repository import get_stats
            s = get_stats()
            self.lbl_status.configure(
                text=f"Total OCs CM: {s['total']}  |  "
                     f"Sin homologar: {s['sin_homolog']}  |  "
                     f"Ingresadas: {s['ingresadas']}"
            )
        except Exception:
            self.lbl_status.configure(text="Listo")

        self.after(30_000, self._update_status)  # Refrescar cada 30s

    def _last_sync_text(self) -> str:
        last = self.app_state.config.last_sync
        if not last:
            return "Sin sincronizar"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(last)
            return f"Última sync:\n{dt.strftime('%d/%m/%Y %H:%M')}"
        except Exception:
            return "Sin sincronizar"
