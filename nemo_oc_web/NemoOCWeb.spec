# NemoOCWeb.spec
# Ejecutar desde nemo_oc_web/:
#   pyinstaller NemoOCWeb.spec --clean

from pathlib import Path

ROOT     = Path(SPECPATH)            # .../nemo_oc_web/
NEMO_OC  = ROOT.parent / "nemo_oc"  # .../nemo_oc/
FE_DIST  = ROOT / "frontend" / "dist"

a = Analysis(
    [str(ROOT / "launcher.py")],
    pathex=[str(ROOT), str(NEMO_OC)],
    binaries=[],
    datas=[
        (str(FE_DIST),  "frontend_dist"),   # React build → sys._MEIPASS/frontend_dist
        (str(NEMO_OC),  "nemo_oc"),         # paquete nemo_oc → sys._MEIPASS/nemo_oc
    ],
    hiddenimports=[
        # ── paquete backend (importado como string por uvicorn en dev; explícito aquí) ──
        "backend",
        "backend.main",
        "backend.api",
        "backend.api.auth_routes",
        "backend.api.catalog_routes",
        "backend.api.config_routes",
        "backend.api.holdings_routes",
        "backend.api.oc_routes",
        "backend.api.schemas",
        "backend.api.sync_routes",
        "backend.core",
        "backend.core.auth",
        "backend.core.deps",
        "backend.core.startup",
        "backend.core.tasks",
        # uvicorn internals (no detectados automáticamente)
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # starlette / fastapi
        "starlette.middleware.sessions",
        "multipart",
        "multipart.multipart",
        # datos / parsing
        "openpyxl",
        "openpyxl.cell._writer",
        "pdfplumber",
        "pdfminer",
        "pdfminer.high_level",
        "pdfminer.layout",
        "pdfminer.pdfpage",
        "pdfminer.converter",
        "pdfminer.pdfinterp",
        "pdfminer.pdfdevice",
        "bs4",
        "html.parser",
        # auth / sesiones
        "itsdangerous",
        "itsdangerous.url_safe",
        # stdlib en runtime
        "email",
        "email.mime",
        "email.mime.text",
        "email.mime.multipart",
        "imaplib",
        "smtplib",
        "sqlite3",
        "csv",
        "zipfile",
        "xml",
        "xml.etree.ElementTree",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL", "pytest",
              "pandas", "pyarrow", "scipy", "numba", "IPython",
              "notebook", "jupyter", "sphinx", "docutils"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NemoOCWeb",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,   # ventana de consola: muestra logs y URL
    icon=str(NEMO_OC / "assets" / "mono.ico"),
)
