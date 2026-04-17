"""
Pantalla de Configuración.
Gestiona API ticket, empresa, catálogos de homologación y preferencias.
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import threading
import logging

logger = logging.getLogger(__name__)


class ConfigFrame(ctk.CTkFrame):

    def __init__(self, master, app_state, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app_state = app_state
        self._build()

    def _build(self):
        # Scroll container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Título ──────────────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="Configuración", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(0, 16))

        # ── Sección API ─────────────────────────────────────────────────
        self._section(scroll, "Conexión API Mercado Público")
        api_frame = ctk.CTkFrame(scroll)
        api_frame.pack(fill="x", pady=(0, 12))
        api_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(api_frame, text="Ticket API:", anchor="w").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.entry_ticket = ctk.CTkEntry(api_frame, show="*", placeholder_text="Ingrese su ticket de API")
        self.entry_ticket.grid(row=0, column=1, padx=12, pady=8, sticky="ew")
        self.btn_show = ctk.CTkButton(api_frame, text="Mostrar", width=80, command=self._toggle_ticket)
        self.btn_show.grid(row=0, column=2, padx=(0, 12), pady=8)

        ctk.CTkLabel(api_frame, text="Código Empresa:", anchor="w").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self.entry_empresa = ctk.CTkEntry(api_frame, placeholder_text="227926")
        self.entry_empresa.grid(row=1, column=1, padx=12, pady=8, sticky="ew")

        ctk.CTkLabel(api_frame, text="RUT Proveedor:", anchor="w").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        lbl_rut = ctk.CTkLabel(api_frame, text="76.215.260-6 (Nemo Chile S.A.)", anchor="w", text_color="gray")
        lbl_rut.grid(row=2, column=1, padx=12, pady=8, sticky="w")

        # Test connection button
        btn_frame = ctk.CTkFrame(api_frame, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")
        self.btn_test = ctk.CTkButton(btn_frame, text="Probar conexión", command=self._probar_conexion, width=150)
        self.btn_test.pack(side="left", padx=(0, 10))
        self.lbl_test_result = ctk.CTkLabel(btn_frame, text="")
        self.lbl_test_result.pack(side="left")

        # ── Sección Catálogos ────────────────────────────────────────────
        self._section(scroll, "Catálogos de Homologación")

        # Info carpeta catalogs
        from app.config import get_catalogs_dir
        catalogs_path = str(get_catalogs_dir())
        info_frame = ctk.CTkFrame(scroll, fg_color="gray20", corner_radius=6)
        info_frame.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            info_frame,
            text=f"📁  Carpeta de catálogos: {catalogs_path}",
            anchor="w", font=ctk.CTkFont(size=11), text_color="gray70"
        ).pack(side="left", padx=12, pady=6)
        ctk.CTkButton(
            info_frame, text="Abrir carpeta", width=100, height=26,
            fg_color="gray35", hover_color="gray45",
            command=lambda: self._abrir_carpeta_catalogs()
        ).pack(side="right", padx=8, pady=6)

        cat_frame = ctk.CTkFrame(scroll)
        cat_frame.pack(fill="x", pady=(0, 12))
        cat_frame.columnconfigure(1, weight=1)

        # HOMOLOGACION.xlsx
        ctk.CTkLabel(cat_frame, text="Convenio Marco:", anchor="w").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.entry_homo = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a HOMOLOGACION.xlsx")
        self.entry_homo.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_homo_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_homo_status.grid(row=0, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_homo).grid(row=0, column=3, padx=(0, 4), pady=8)
        self.btn_import_homo = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_homo)
        self.btn_import_homo.grid(row=0, column=4, padx=(0, 12), pady=8)

        # Maestra SAP
        ctk.CTkLabel(cat_frame, text="Maestra Materiales:", anchor="w").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self.entry_maestra = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a Maestra de Materiales")
        self.entry_maestra.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_maestra_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_maestra_status.grid(row=1, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_maestra).grid(row=1, column=3, padx=(0, 4), pady=8)
        self.btn_import_maestra = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_maestra)
        self.btn_import_maestra.grid(row=1, column=4, padx=(0, 12), pady=8)

        # Cartera Clientes
        ctk.CTkLabel(cat_frame, text="Cartera Clientes:", anchor="w").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self.entry_cartera = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a CARTERA(PBI).xlsx")
        self.entry_cartera.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_cartera_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_cartera_status.grid(row=2, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_cartera).grid(row=2, column=3, padx=(0, 4), pady=8)
        self.btn_import_cartera = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_cartera)
        self.btn_import_cartera.grid(row=2, column=4, padx=(0, 12), pady=8)

        # Correos Vendedores
        ctk.CTkLabel(cat_frame, text="Correos Vendedores:", anchor="w").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self.entry_correos = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a CORREOS.xlsx")
        self.entry_correos.grid(row=3, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_correos_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_correos_status.grid(row=3, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_correos).grid(row=3, column=3, padx=(0, 4), pady=8)
        self.btn_import_correos = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_correos)
        self.btn_import_correos.grid(row=3, column=4, padx=(0, 12), pady=8)

        # Homologación RedSalud
        ctk.CTkLabel(cat_frame, text="Homo RedSalud:", anchor="w").grid(row=4, column=0, padx=12, pady=8, sticky="w")
        self.entry_redsalud = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a HOMO RED SALUD.xlsx")
        self.entry_redsalud.grid(row=4, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_redsalud_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_redsalud_status.grid(row=4, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_redsalud).grid(row=4, column=3, padx=(0, 4), pady=8)
        self.btn_import_redsalud = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_redsalud)
        self.btn_import_redsalud.grid(row=4, column=4, padx=(0, 12), pady=8)

        # Licitaciones (referencia para OCs no-CM)
        ctk.CTkLabel(cat_frame, text="Licitaciones:", anchor="w").grid(row=5, column=0, padx=12, pady=8, sticky="w")
        self.entry_licitaciones = ctk.CTkEntry(cat_frame, placeholder_text="Ruta a lic.xlsx")
        self.entry_licitaciones.grid(row=5, column=1, padx=8, pady=8, sticky="ew")
        self.lbl_licit_status = ctk.CTkLabel(cat_frame, text="", width=20, font=ctk.CTkFont(size=13))
        self.lbl_licit_status.grid(row=5, column=2, padx=(0, 4), pady=8)
        ctk.CTkButton(cat_frame, text="...", width=36, command=self._browse_licitaciones).grid(row=5, column=3, padx=(0, 4), pady=8)
        self.btn_import_licit = ctk.CTkButton(cat_frame, text="Actualizar", width=90, command=self._importar_licitaciones)
        self.btn_import_licit.grid(row=5, column=4, padx=(0, 12), pady=8)

        # Stats de catálogo
        self.lbl_stats = ctk.CTkLabel(cat_frame, text="", anchor="w", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_stats.grid(row=6, column=0, columnspan=5, padx=12, pady=(0, 8), sticky="w")

        # ── Sección Notificaciones Email ─────────────────────────────────
        self._section(scroll, "Notificaciones Email")
        email_frame = ctk.CTkFrame(scroll)
        email_frame.pack(fill="x", pady=(0, 12))
        email_frame.columnconfigure(1, weight=1)

        self.var_smtp_enabled = tk.BooleanVar()
        ctk.CTkCheckBox(
            email_frame, text="Activar notificaciones por email al recibir OCs nuevas",
            variable=self.var_smtp_enabled
        ).grid(row=0, column=0, columnspan=3, padx=12, pady=(10, 6), sticky="w")

        ctk.CTkLabel(email_frame, text="Servidor SMTP:", anchor="w").grid(row=1, column=0, padx=12, pady=6, sticky="w")
        self.entry_smtp_host = ctk.CTkEntry(email_frame, placeholder_text="smtp.office365.com")
        self.entry_smtp_host.grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkLabel(email_frame, text="Puerto:", anchor="w").grid(row=1, column=2, padx=(0, 4), pady=6, sticky="w")
        self.entry_smtp_port = ctk.CTkEntry(email_frame, width=70, placeholder_text="587")
        self.entry_smtp_port.grid(row=1, column=3, padx=(0, 12), pady=6)

        ctk.CTkLabel(email_frame, text="Usuario/Email:", anchor="w").grid(row=2, column=0, padx=12, pady=6, sticky="w")
        self.entry_smtp_user = ctk.CTkEntry(email_frame, placeholder_text="correo@nemo.cl")
        self.entry_smtp_user.grid(row=2, column=1, columnspan=2, padx=8, pady=6, sticky="ew")

        ctk.CTkLabel(email_frame, text="Contraseña:", anchor="w").grid(row=3, column=0, padx=12, pady=6, sticky="w")
        self.entry_smtp_pass = ctk.CTkEntry(email_frame, show="*", placeholder_text="Contraseña de la cuenta")
        self.entry_smtp_pass.grid(row=3, column=1, columnspan=2, padx=8, pady=6, sticky="ew")

        ctk.CTkLabel(
            email_frame,
            text="⚠  La contraseña se guarda en texto plano en settings.json",
            text_color="orange", font=ctk.CTkFont(size=11)
        ).grid(row=4, column=0, columnspan=4, padx=12, pady=(0, 6), sticky="w")

        smtp_btn_frame = ctk.CTkFrame(email_frame, fg_color="transparent")
        smtp_btn_frame.grid(row=5, column=0, columnspan=4, padx=12, pady=(4, 10), sticky="w")
        ctk.CTkButton(smtp_btn_frame, text="Guardar", width=100, command=self._guardar_smtp).pack(side="left", padx=(0, 8))
        ctk.CTkButton(smtp_btn_frame, text="Probar envío", width=110, fg_color="gray40", command=self._probar_smtp).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(smtp_btn_frame, text="→", text_color="gray").pack(side="left", padx=(0, 4))
        self.entry_test_email = ctk.CTkEntry(smtp_btn_frame, width=220, placeholder_text="correo de prueba")
        self.entry_test_email.insert(0, "samuel.belmar@nemochile.cl")
        self.entry_test_email.pack(side="left", padx=(0, 10))
        self.lbl_smtp_status = ctk.CTkLabel(smtp_btn_frame, text="", font=ctk.CTkFont(size=12))
        self.lbl_smtp_status.pack(side="left")

        # ── Sección OCs Privadas (IMAP) ──────────────────────────────────
        self._section(scroll, "OCs Privadas — Búsqueda en Gmail (IMAP)")
        imap_frame = ctk.CTkFrame(scroll)
        imap_frame.pack(fill="x", pady=(0, 12))
        imap_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            imap_frame,
            text="Usa las mismas credenciales Gmail configuradas en Notificaciones Email.",
            text_color="gray", font=ctk.CTkFont(size=11)
        ).grid(row=0, column=0, columnspan=4, padx=12, pady=(10, 4), sticky="w")

        ctk.CTkLabel(imap_frame, text="Filtro remitente:", anchor="w").grid(row=1, column=0, padx=12, pady=6, sticky="w")
        self.entry_imap_filter = ctk.CTkEntry(imap_frame, placeholder_text="ordenesdecompra@nemochile.cl")
        self.entry_imap_filter.grid(row=1, column=1, columnspan=2, padx=8, pady=6, sticky="ew")

        ctk.CTkLabel(
            imap_frame,
            text="Emails no leídos enviados por este remitente y con PDF adjunto serán importados.",
            text_color="gray", font=ctk.CTkFont(size=11)
        ).grid(row=2, column=0, columnspan=4, padx=12, pady=(0, 8), sticky="w")

        imap_btn_frame = ctk.CTkFrame(imap_frame, fg_color="transparent")
        imap_btn_frame.grid(row=3, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w")
        ctk.CTkButton(imap_btn_frame, text="Guardar filtro", width=120, command=self._guardar_imap).pack(side="left", padx=(0, 8))

        # ── Sección Preferencias ─────────────────────────────────────────
        self._section(scroll, "Preferencias")
        pref_frame = ctk.CTkFrame(scroll)
        pref_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(pref_frame, text="Tema de la aplicación:", anchor="w").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        self.opt_theme = ctk.CTkOptionMenu(pref_frame, values=["dark", "light", "system"], command=self._cambiar_tema)
        self.opt_theme.grid(row=0, column=1, padx=12, pady=8, sticky="w")

        # ── Botones de acción ────────────────────────────────────────────
        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(action_frame, text="Guardar configuración", command=self._guardar, width=180).pack(side="left", padx=(0, 10))
        ctk.CTkButton(action_frame, text="Abrir carpeta de datos", command=self._abrir_carpeta, fg_color="gray40", width=180).pack(side="left")

    # ------------------------------------------------------------------
    def on_show(self):
        """Llamado al navegar a esta pantalla. Carga config actual."""
        from app.config import (get_default_homo_path, get_default_maestra_path,
                                get_default_cartera_path, get_default_correos_path,
                                get_default_redsalud_homo_path, get_default_licitaciones_path)
        from pathlib import Path

        cfg = self.app_state.config
        self.entry_ticket.delete(0, "end")
        self.entry_ticket.insert(0, cfg.api_ticket)
        self.entry_empresa.delete(0, "end")
        self.entry_empresa.insert(0, cfg.codigo_empresa)

        # Homologación: usar ruta guardada o detectar default
        homo_path = cfg.homologacion_path or str(get_default_homo_path())
        self.entry_homo.delete(0, "end")
        self.entry_homo.insert(0, homo_path)
        self._actualizar_status_archivo(homo_path, self.lbl_homo_status)

        # Maestra: usar ruta guardada o detectar default
        maestra_path = cfg.maestra_path or str(get_default_maestra_path())
        self.entry_maestra.delete(0, "end")
        self.entry_maestra.insert(0, maestra_path)
        self._actualizar_status_archivo(maestra_path, self.lbl_maestra_status)

        # Cartera: usar ruta guardada o detectar default
        cartera_path = cfg.cartera_path or str(get_default_cartera_path())
        self.entry_cartera.delete(0, "end")
        self.entry_cartera.insert(0, cartera_path)
        self._actualizar_status_archivo(cartera_path, self.lbl_cartera_status)

        # Correos vendedores: usar ruta guardada o detectar default
        correos_path = cfg.correos_path or str(get_default_correos_path())
        self.entry_correos.delete(0, "end")
        self.entry_correos.insert(0, correos_path)
        self._actualizar_status_archivo(correos_path, self.lbl_correos_status)

        # Homo RedSalud
        redsalud_path = cfg.redsalud_homo_path or str(get_default_redsalud_homo_path())
        self.entry_redsalud.delete(0, "end")
        self.entry_redsalud.insert(0, redsalud_path)
        self._actualizar_status_archivo(redsalud_path, self.lbl_redsalud_status)

        # Licitaciones
        licit_path = cfg.licitaciones_path or str(get_default_licitaciones_path())
        self.entry_licitaciones.delete(0, "end")
        self.entry_licitaciones.insert(0, licit_path)
        self._actualizar_status_archivo(licit_path, self.lbl_licit_status)

        # IMAP filter
        self.entry_imap_filter.delete(0, "end")
        self.entry_imap_filter.insert(0, cfg.imap_filter_from or "ordenesdecompra@nemochile.cl")

        # Email SMTP
        self.var_smtp_enabled.set(cfg.smtp_enabled)
        self.entry_smtp_host.delete(0, "end")
        self.entry_smtp_host.insert(0, cfg.smtp_host)
        self.entry_smtp_port.delete(0, "end")
        self.entry_smtp_port.insert(0, str(cfg.smtp_port))
        self.entry_smtp_user.delete(0, "end")
        self.entry_smtp_user.insert(0, cfg.smtp_user)
        self.entry_smtp_pass.delete(0, "end")
        self.entry_smtp_pass.insert(0, cfg.smtp_password)

        self.opt_theme.set(cfg.theme)
        self._actualizar_stats()

    def _actualizar_status_archivo(self, path: str, lbl):
        from pathlib import Path
        if path and Path(path).exists():
            lbl.configure(text="✓", text_color="green")
        else:
            lbl.configure(text="✗", text_color="red")

    def _abrir_carpeta_catalogs(self):
        import subprocess
        from app.config import get_catalogs_dir
        subprocess.Popen(f'explorer "{get_catalogs_dir()}"')

    def _section(self, parent, title: str):
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(12, 4))

    def _toggle_ticket(self):
        cur = self.entry_ticket.cget("show")
        self.entry_ticket.configure(show="" if cur == "*" else "*")
        self.btn_show.configure(text="Ocultar" if cur == "*" else "Mostrar")

    def _browse_homo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar HOMOLOGACION.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if path:
            self.entry_homo.delete(0, "end")
            self.entry_homo.insert(0, path)

    def _browse_maestra(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Maestra SAP",
            filetypes=[("Excel/CSV", "*.xlsx *.xlsm *.csv"), ("Todos", "*.*")]
        )
        if path:
            self.entry_maestra.delete(0, "end")
            self.entry_maestra.insert(0, path)

    def _browse_cartera(self):
        path = filedialog.askopenfilename(
            title="Seleccionar CARTERA(PBI).xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if path:
            self.entry_cartera.delete(0, "end")
            self.entry_cartera.insert(0, path)

    def _importar_homo(self):
        path = self.entry_homo.get().strip()
        if not path:
            messagebox.showwarning("Catálogo CM", "No hay ruta de archivo configurada.")
            return
        self.btn_import_homo.configure(state="disabled", text="Actualizando...")
        self._guardar_silencioso()

        def _run():
            from app.services.homologacion_service import get_homologacion_service
            svc = get_homologacion_service()
            count, errores = svc.cargar_homologacion_excel(path)
            self.after(0, lambda: (
                self._actualizar_status_archivo(path, self.lbl_homo_status),
                self._on_import_done("Convenio Marco", count, errores, self.btn_import_homo, "Actualizar")
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _importar_maestra(self):
        path = self.entry_maestra.get().strip()
        if not path:
            messagebox.showwarning("Maestra SAP", "No hay ruta de archivo configurada.")
            return
        self.btn_import_maestra.configure(state="disabled", text="Actualizando...")
        self._guardar_silencioso()

        def _run():
            from app.services.homologacion_service import get_homologacion_service
            svc = get_homologacion_service()
            count, errores = svc.cargar_maestra_sap(path)
            self.after(0, lambda: (
                self._actualizar_status_archivo(path, self.lbl_maestra_status),
                self._on_import_done("Maestra SAP", count, errores, self.btn_import_maestra, "Actualizar")
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _importar_cartera(self):
        path = self.entry_cartera.get().strip()
        if not path:
            messagebox.showwarning("Cartera Clientes", "No hay ruta de archivo configurada.")
            return
        self.btn_import_cartera.configure(state="disabled", text="Actualizando...")
        self._guardar_silencioso()

        def _run():
            from app.services.cartera_service import get_cartera_service
            svc = get_cartera_service()
            count, errores = svc.cargar_cartera_excel(path)
            self.after(0, lambda: (
                self._actualizar_status_archivo(path, self.lbl_cartera_status),
                self._on_import_done("Cartera Clientes", count, errores, self.btn_import_cartera, "Actualizar")
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _browse_redsalud(self):
        path = filedialog.askopenfilename(
            title="Seleccionar HOMO RED SALUD.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if path:
            self.entry_redsalud.delete(0, "end")
            self.entry_redsalud.insert(0, path)

    def _importar_redsalud(self):
        path = self.entry_redsalud.get().strip()
        if not path:
            messagebox.showwarning("Homo RedSalud", "No hay ruta de archivo configurada.")
            return
        self.btn_import_redsalud.configure(state="disabled", text="Actualizando...")
        self.app_state.config.redsalud_homo_path = path
        from app.config import save_config
        save_config(self.app_state.config)

        def _run():
            from app.services.redsalud_homo_service import get_redsalud_homo_service
            svc = get_redsalud_homo_service()
            count, errores = svc.cargar_excel(path)
            self.after(0, lambda: (
                self._actualizar_status_archivo(path, self.lbl_redsalud_status),
                self._on_import_done("Homo RedSalud", count, errores, self.btn_import_redsalud, "Actualizar")
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _guardar_imap(self):
        cfg = self.app_state.config
        cfg.imap_filter_from = self.entry_imap_filter.get().strip() or "ordenesdecompra@nemochile.cl"
        from app.config import save_config
        save_config(cfg)
        messagebox.showinfo("IMAP", "Filtro de remitente guardado correctamente.")

    def _on_import_done(self, nombre, count, errores, btn, btn_text):
        btn.configure(state="normal", text=btn_text)
        self._actualizar_stats()
        if errores:
            messagebox.showwarning(f"Importación {nombre}", f"Importados: {count}\n\nAdvertencias:\n" + "\n".join(errores))
        else:
            messagebox.showinfo(f"Importación {nombre}", f"Se importaron {count} registros correctamente.")

    def _actualizar_stats(self):
        try:
            from app.repositories.homologacion_repo import count_homologacion
            from app.repositories.cartera_repo import count_cartera
            from app.services.redsalud_homo_service import get_redsalud_homo_service
            from app.services.maestra_service import get_maestra_service
            from app.services.licitaciones_service import get_licitaciones_service
            s = count_homologacion()
            c = count_cartera()
            r = get_redsalud_homo_service().count()
            m = get_maestra_service().count()
            l = get_licitaciones_service().count()
            self.lbl_stats.configure(
                text=(f"CM: {s['cm']}  |  SAP: {s['sap']}  |  Cruzados: {s['cruzados']}  |  "
                      f"Cartera: {c}  |  RedSalud: {r}  |  Maestra: {m}  |  Licitaciones: {l} ref")
            )
        except Exception:
            pass

    def _probar_conexion(self):
        ticket = self.entry_ticket.get().strip()
        empresa = self.entry_empresa.get().strip() or "227926"
        if not ticket:
            messagebox.showwarning("Ticket vacío", "Ingrese un ticket de API antes de probar la conexión.")
            return
        self.btn_test.configure(state="disabled", text="Probando...")
        self.lbl_test_result.configure(text="")

        def _run():
            from app.services.mp_api_service import MercadoPublicoAPI
            api = MercadoPublicoAPI(ticket=ticket, codigo_empresa=empresa)
            ok, msg = api.probar_conexion()
            self.after(0, lambda: self._on_test_done(ok, msg))

        threading.Thread(target=_run, daemon=True).start()

    def _on_test_done(self, ok: bool, msg: str = ""):
        self.btn_test.configure(state="normal", text="Probar conexión")
        if ok:
            self.lbl_test_result.configure(text="✓ Conexión exitosa", text_color="green")
        else:
            error_txt = f"✗ {msg}" if msg else "✗ Falló — verifique ticket e internet"
            self.lbl_test_result.configure(text=error_txt, text_color="red")

    def _cambiar_tema(self, theme: str):
        ctk.set_appearance_mode(theme)
        self.app_state.config.theme = theme

    def _guardar_silencioso(self):
        """Guarda sin mostrar mensaje."""
        cfg = self.app_state.config
        cfg.api_ticket = self.entry_ticket.get().strip()
        cfg.codigo_empresa = self.entry_empresa.get().strip() or "227926"
        cfg.homologacion_path = self.entry_homo.get().strip()
        cfg.maestra_path = self.entry_maestra.get().strip()
        cfg.cartera_path = self.entry_cartera.get().strip()
        cfg.correos_path = self.entry_correos.get().strip()
        cfg.redsalud_homo_path = self.entry_redsalud.get().strip()
        cfg.licitaciones_path = self.entry_licitaciones.get().strip()
        cfg.imap_filter_from = self.entry_imap_filter.get().strip() or "ordenesdecompra@nemochile.cl"
        cfg.theme = self.opt_theme.get()
        from app.config import save_config
        save_config(cfg)

    def _guardar(self):
        self._guardar_silencioso()
        messagebox.showinfo("Configuración", "Configuración guardada correctamente.")

    def _browse_correos(self):
        path = filedialog.askopenfilename(
            title="Seleccionar CORREOS.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if path:
            self.entry_correos.delete(0, "end")
            self.entry_correos.insert(0, path)

    def _importar_correos(self):
        path = self.entry_correos.get().strip()
        if not path:
            messagebox.showwarning("Correos Vendedores", "No hay ruta de archivo configurada.")
            return
        self.btn_import_correos.configure(state="disabled", text="Cargando...")
        self._guardar_silencioso()

        def _run():
            from app.services.email_service import get_email_service
            ok, msg = get_email_service().cargar_correos(path)
            self.after(0, lambda: self._on_correos_done(ok, msg, path))

        threading.Thread(target=_run, daemon=True).start()

    def _on_correos_done(self, ok: bool, msg: str, path: str):
        self.btn_import_correos.configure(state="normal", text="Actualizar")
        self._actualizar_status_archivo(path, self.lbl_correos_status)
        if ok:
            messagebox.showinfo("Correos Vendedores", msg)
        else:
            messagebox.showerror("Correos Vendedores", f"Error: {msg}")

    def _guardar_smtp(self):
        cfg = self.app_state.config
        cfg.smtp_enabled = self.var_smtp_enabled.get()
        cfg.smtp_host = self.entry_smtp_host.get().strip()
        try:
            cfg.smtp_port = int(self.entry_smtp_port.get().strip() or "587")
        except ValueError:
            self.lbl_smtp_status.configure(text="Puerto inválido", text_color="red")
            return
        cfg.smtp_user = self.entry_smtp_user.get().strip()
        cfg.smtp_password = self.entry_smtp_pass.get()
        from app.config import save_config
        save_config(cfg)
        self.app_state.config = cfg
        self.lbl_smtp_status.configure(text="Guardado ✓", text_color="green")
        self.after(3000, lambda: self.lbl_smtp_status.configure(text=""))

    def _probar_smtp(self):
        import dataclasses
        from app.config import load_config
        cfg = load_config()
        try:
            port = int(self.entry_smtp_port.get().strip() or "587")
        except ValueError:
            self.lbl_smtp_status.configure(text="Puerto inválido", text_color="red")
            return
        test_cfg = dataclasses.replace(
            cfg,
            smtp_host=self.entry_smtp_host.get().strip(),
            smtp_port=port,
            smtp_user=self.entry_smtp_user.get().strip(),
            smtp_password=self.entry_smtp_pass.get(),
        )
        self.lbl_smtp_status.configure(text="Enviando...", text_color="gray")
        self.update_idletasks()

        to_email = self.entry_test_email.get().strip() or test_cfg.smtp_user

        def _run():
            from app.services.email_service import get_email_service
            ok, msg = get_email_service().enviar_prueba(test_cfg, to_email=to_email)
            self.after(0, lambda: self.lbl_smtp_status.configure(
                text=msg[:55],
                text_color="green" if ok else "red"
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _browse_licitaciones(self):
        path = filedialog.askopenfilename(
            title="Seleccionar lic.xlsx",
            filetypes=[("Excel", "*.xlsx *.xlsm"), ("Todos", "*.*")]
        )
        if path:
            self.entry_licitaciones.delete(0, "end")
            self.entry_licitaciones.insert(0, path)

    def _importar_licitaciones(self):
        path = self.entry_licitaciones.get().strip()
        if not path:
            messagebox.showwarning("Licitaciones", "No hay ruta de archivo configurada.")
            return
        self.btn_import_licit.configure(state="disabled", text="Importando...")
        self._guardar_silencioso()

        def _run():
            try:
                from app.services.licitaciones_service import get_licitaciones_service
                svc = get_licitaciones_service()
                count, errores = svc.importar_lic(path)
                self.after(0, lambda: (
                    self._actualizar_status_archivo(path, self.lbl_licit_status),
                    self._on_import_done("Licitaciones", count, errores, self.btn_import_licit, "Actualizar")
                ))
            except Exception as e:
                self.after(0, lambda: (
                    self.btn_import_licit.configure(state="normal", text="Actualizar"),
                    messagebox.showerror("Licitaciones", f"Error: {e}")
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _abrir_carpeta(self):
        import subprocess
        from app.config import get_data_dir
        folder = str(get_data_dir().parent)
        subprocess.Popen(f'explorer "{folder}"')
