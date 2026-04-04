"""
Pantalla de Importación / Sincronización.
Descarga OCs CM desde la API con selector de fechas y log en tiempo real.
"""
import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta
import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)

try:
    from tkcalendar import DateEntry
    _HAS_CALENDAR = True
except ImportError:
    _HAS_CALENDAR = False


class ImportFrame(ctk.CTkFrame):

    def __init__(self, master, app_state, on_sync_done=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self.on_sync_done = on_sync_done
        self._sync_queue: queue.Queue = None
        self._polling = False
        self._build()

    def _build(self):
        # Título
        ctk.CTkLabel(self, text="Importar Órdenes de Compra", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))

        # ── Panel de fechas ──────────────────────────────────────────────
        date_card = ctk.CTkFrame(self)
        date_card.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(date_card, text="Rango de fechas", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))

        date_row = ctk.CTkFrame(date_card, fg_color="transparent")
        date_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(date_row, text="Desde:").pack(side="left", padx=(0, 6))
        self.date_desde = self._make_date_entry(date_row)
        self.date_desde.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(date_row, text="Hasta:").pack(side="left", padx=(0, 6))
        self.date_hasta = self._make_date_entry(date_row)
        self.date_hasta.pack(side="left", padx=(0, 16))

        # Atajos rápidos
        quick_row = ctk.CTkFrame(date_card, fg_color="transparent")
        quick_row.pack(fill="x", padx=16, pady=(0, 12))
        for label, days in [("Hoy", 0), ("7 días", 7), ("30 días", 30), ("90 días", 90)]:
            ctk.CTkButton(
                quick_row, text=label, width=70, height=28,
                command=lambda d=days: self._set_quick(d),
                fg_color="gray30"
            ).pack(side="left", padx=(0, 6))

        # Auto-sync al iniciar
        auto_row = ctk.CTkFrame(date_card, fg_color="transparent")
        auto_row.pack(fill="x", padx=16, pady=(0, 4))
        self.var_autosync = tk.BooleanVar(value=self.app_state.config.auto_sync)
        ctk.CTkCheckBox(
            auto_row, text="Auto-sincronizar al iniciar la app",
            variable=self.var_autosync,
            command=self._toggle_autosync
        ).pack(side="left")
        ctk.CTkLabel(auto_row, text=" | Días:").pack(side="left", padx=(8, 4))
        self.entry_days = ctk.CTkEntry(auto_row, width=50)
        self.entry_days.insert(0, str(self.app_state.config.auto_sync_days))
        self.entry_days.pack(side="left")
        ctk.CTkLabel(auto_row, text="días atrás", text_color="gray").pack(side="left", padx=4)

        # Auto-sync periódico mientras la app está abierta
        auto_row2 = ctk.CTkFrame(date_card, fg_color="transparent")
        auto_row2.pack(fill="x", padx=16, pady=(0, 12))
        self.var_periodic = tk.BooleanVar(value=(self.app_state.config.auto_sync_interval > 0))
        ctk.CTkCheckBox(
            auto_row2, text="Buscar OCs nuevas cada",
            variable=self.var_periodic,
            command=self._toggle_periodic
        ).pack(side="left")
        self.entry_interval = ctk.CTkEntry(auto_row2, width=45)
        self.entry_interval.insert(0, str(self.app_state.config.auto_sync_interval or 15))
        self.entry_interval.pack(side="left", padx=(8, 4))
        ctk.CTkLabel(auto_row2, text="minutos (mientras la app está abierta)", text_color="gray").pack(side="left", padx=4)

        # Tipos de OC a descargar
        tipo_row = ctk.CTkFrame(date_card, fg_color="transparent")
        tipo_row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(tipo_row, text="Tipos de OC:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))
        self.var_tipo_cm = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(tipo_row, text="Convenio Marco (CM)", variable=self.var_tipo_cm).pack(side="left", padx=(0, 12))
        self.var_tipo_otras = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(tipo_row, text="Otras (SE, AG, CC, etc.)", variable=self.var_tipo_otras).pack(side="left")

        # Botón principal
        self.btn_sync = ctk.CTkButton(
            date_card,
            text="⬇  Descargar OCs",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            command=self._iniciar_sync,
        )
        self.btn_sync.pack(padx=16, pady=(0, 16), fill="x")

        # ── Panel OCs Privadas (Gmail) ────────────────────────────────────
        priv_card = ctk.CTkFrame(self)
        priv_card.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(priv_card, text="OCs Privadas (Email)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))

        priv_info = ctk.CTkFrame(priv_card, fg_color="transparent")
        priv_info.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            priv_info,
            text="Busca emails no leídos en Gmail con PDF de OC adjunto (RedSalud y similares).",
            text_color="gray", font=ctk.CTkFont(size=11)
        ).pack(side="left")

        self.btn_sync_privado = ctk.CTkButton(
            priv_card,
            text="📧  Buscar OCs en Gmail",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            fg_color="#1a5276", hover_color="#154360",
            command=self._iniciar_sync_privado,
        )
        self.btn_sync_privado.pack(padx=16, pady=(0, 16), fill="x")

        # ── Progreso ─────────────────────────────────────────────────────
        prog_card = ctk.CTkFrame(self)
        prog_card.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(prog_card, text="Progreso", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        self.progress_bar = ctk.CTkProgressBar(prog_card)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 4))
        self.progress_bar.set(0)
        self.lbl_progress = ctk.CTkLabel(prog_card, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_progress.pack(anchor="w", padx=16, pady=(0, 12))

        # ── Log ──────────────────────────────────────────────────────────
        log_card = ctk.CTkFrame(self)
        log_card.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(log_header, text="Log de sincronización", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(log_header, text="Limpiar", width=70, height=26, fg_color="gray30", command=self._limpiar_log).pack(side="right")

        self.log_box = ctk.CTkTextbox(log_card, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Establecer fechas por defecto (últimos 7 días)
        self._set_quick(7)

    def on_show(self):
        """Llamado al navegar a esta pantalla."""
        self.var_autosync.set(self.app_state.config.auto_sync)
        self.entry_days.delete(0, "end")
        self.entry_days.insert(0, str(self.app_state.config.auto_sync_days))

    def auto_sync_if_configured(self):
        """Ejecutar auto-sync si está configurado."""
        if self.app_state.config.auto_sync:
            days = self.app_state.config.auto_sync_days or 7
            self._set_quick(days)
            self._iniciar_sync()

    # ------------------------------------------------------------------

    def _make_date_entry(self, parent) -> tk.Widget:
        if _HAS_CALENDAR:
            entry = DateEntry(
                parent, width=12, date_pattern="yyyy-mm-dd",
                background="gray20", foreground="white",
                borderwidth=2, locale="es_CL"
            )
        else:
            entry = ctk.CTkEntry(parent, width=110, placeholder_text="YYYY-MM-DD")
        return entry

    def _get_date(self, widget) -> str:
        if _HAS_CALENDAR and isinstance(widget, DateEntry):
            return widget.get_date().strftime("%Y-%m-%d")
        return widget.get().strip()

    def _set_quick(self, days: int):
        hoy = datetime.now()
        desde = hoy - timedelta(days=days)
        if _HAS_CALENDAR and isinstance(self.date_desde, DateEntry):
            self.date_desde.set_date(desde)
            self.date_hasta.set_date(hoy)
        else:
            self.date_desde.delete(0, "end")
            self.date_desde.insert(0, desde.strftime("%Y-%m-%d"))
            self.date_hasta.delete(0, "end")
            self.date_hasta.insert(0, hoy.strftime("%Y-%m-%d"))

    def _toggle_autosync(self):
        val = self.var_autosync.get()
        self.app_state.config.auto_sync = val
        try:
            days = int(self.entry_days.get())
            self.app_state.config.auto_sync_days = days
        except ValueError:
            pass
        from app.config import save_config
        save_config(self.app_state.config)

    def _toggle_periodic(self):
        try:
            interval = int(self.entry_interval.get()) if self.var_periodic.get() else 0
            self.app_state.config.auto_sync_interval = interval
        except ValueError:
            self.app_state.config.auto_sync_interval = 15 if self.var_periodic.get() else 0
        from app.config import save_config
        save_config(self.app_state.config)

    def _iniciar_sync(self):
        cfg = self.app_state.config
        if not cfg.api_ticket:
            from tkinter import messagebox
            messagebox.showwarning("Sin ticket", "Configure un ticket de API en la pantalla de Configuración.")
            return

        try:
            desde_str = self._get_date(self.date_desde)
            hasta_str = self._get_date(self.date_hasta)
            fecha_desde = datetime.strptime(desde_str, "%Y-%m-%d")
            fecha_hasta = datetime.strptime(hasta_str, "%Y-%m-%d")
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("Fecha inválida", "Use el formato YYYY-MM-DD.")
            return

        self.btn_sync.configure(state="disabled", text="Sincronizando...")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Iniciando...")

        # Determinar filtro de tipo
        cm = self.var_tipo_cm.get()
        otras = self.var_tipo_otras.get()
        if not cm and not otras:
            from tkinter import messagebox
            messagebox.showwarning("Sin tipo", "Seleccione al menos un tipo de OC para descargar.")
            self.btn_sync.configure(state="normal", text="⬇  Descargar OCs")
            return
        # solo_cm=True únicamente si CM activo y Otras no
        solo_cm = cm and not otras

        from app.services.sync_service import start_sync_thread
        self._sync_queue = start_sync_thread(
            ticket=cfg.api_ticket,
            codigo_empresa=cfg.codigo_empresa,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            solo_cm=solo_cm,
        )
        self._polling = True
        self.after(150, self._poll_queue)

    def _poll_queue(self):
        if not self._polling:
            return
        try:
            while True:
                msg = self._sync_queue.get_nowait()
                self._handle_msg(msg)
        except queue.Empty:
            pass

        if self._polling:
            self.after(150, self._poll_queue)

    def _handle_msg(self, msg: dict):
        tipo = msg.get("type")
        if tipo == "log":
            self._append_log(msg.get("message", ""))
        elif tipo == "progress":
            cur = msg.get("current", 0)
            total = msg.get("total", 1)
            pct = cur / total if total > 0 else 0
            self.progress_bar.set(pct)
            self.lbl_progress.configure(text=f"{cur} / {total} OCs procesadas")
        elif tipo == "done":
            self._polling = False
            self.progress_bar.set(1)
            self.lbl_progress.configure(text=msg.get("message", "Completado"))
            self.btn_sync.configure(state="normal", text="⬇  Descargar OCs")
            if self.on_sync_done:
                self.on_sync_done()
        elif tipo == "error":
            self._polling = False
            self._append_log(f"ERROR: {msg.get('message', '')}")
            self.btn_sync.configure(state="normal", text="⬇  Descargar OCs")
            self.lbl_progress.configure(text="Error — ver log")

    def _append_log(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _iniciar_sync_privado(self):
        cfg = self.app_state.config
        if not cfg.smtp_user or not cfg.smtp_password:
            from tkinter import messagebox
            messagebox.showwarning(
                "Credenciales Gmail",
                "Configure el usuario y contraseña de Gmail en Configuración → Notificaciones Email."
            )
            return

        self.btn_sync_privado.configure(state="disabled", text="Buscando en Gmail...")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Conectando a Gmail...")

        from app.services.sync_privado_service import start_sync_privado_thread
        self._sync_queue = start_sync_privado_thread(
            smtp_user=cfg.smtp_user,
            smtp_password=cfg.smtp_password,
            imap_server=cfg.imap_server,
            imap_port=cfg.imap_port,
            imap_folder=cfg.imap_folder,
            filter_subject=cfg.imap_filter_subject or "ORDEN DE COMPRA",
        )
        self._polling = True
        self._sync_privado_active = True
        self.after(150, self._poll_queue_privado)

    def _poll_queue_privado(self):
        if not self._polling:
            return
        try:
            while True:
                msg = self._sync_queue.get_nowait()
                tipo = msg.get("type")
                if tipo == "log":
                    self._append_log(msg.get("message", ""))
                elif tipo == "progress":
                    cur   = msg.get("current", 0)
                    total = msg.get("total", 1)
                    pct   = cur / total if total > 0 else 0
                    self.progress_bar.set(pct)
                    self.lbl_progress.configure(text=f"{cur} / {total} PDFs procesados")
                elif tipo == "done":
                    self._polling = False
                    self.progress_bar.set(1)
                    self.lbl_progress.configure(text=msg.get("message", "Completado"))
                    self.btn_sync_privado.configure(state="normal", text="📧  Buscar OCs en Gmail")
                    if self.on_sync_done:
                        self.on_sync_done()
                    return
                elif tipo == "error":
                    self._polling = False
                    self._append_log(f"ERROR: {msg.get('message', '')}")
                    self.btn_sync_privado.configure(state="normal", text="📧  Buscar OCs en Gmail")
                    self.lbl_progress.configure(text="Error — ver log")
                    return
        except Exception:
            pass
        if self._polling:
            self.after(150, self._poll_queue_privado)

    def _limpiar_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="")
