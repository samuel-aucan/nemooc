"""NemoOC Web — Entry point para PyInstaller (.exe)."""
import os
import sys
import socket
import threading
import time
import webbrowser
import urllib.request
from pathlib import Path


# ── Fix sys.path para bundle frozen ─────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _meipass = Path(sys._MEIPASS)
    for _p in [str(_meipass), str(_meipass / "nemo_oc")]:
        if _p not in sys.path:
            sys.path.insert(0, _p)
    # CWD = carpeta del .exe (donde se crean data/, config/, logs/)
    os.chdir(str(Path(sys.executable).parent))


def _configure_base_dir() -> Path:
    """Resuelve la carpeta de datos/config del producto local.

    Regla especial para builds internas dentro del repo:
    si el .exe está en `nemo_oc_web/dist` y existe `../nemo_oc/data/app.db`,
    reutilizamos esa base principal para no pedir bootstrap otra vez.
    """
    explicit = os.getenv("NEMOOC_BASE_DIR", "").strip()
    if explicit:
        return Path(explicit)

    frozen = getattr(sys, "frozen", False)
    exe_dir = Path(sys.executable).parent if frozen else Path(__file__).parent
    repo_candidate = (exe_dir.parent.parent if frozen else exe_dir.parent) / "nemo_oc"
    if (repo_candidate / "data" / "app.db").exists():
        os.environ["NEMOOC_BASE_DIR"] = str(repo_candidate)
        return repo_candidate

    os.environ["NEMOOC_BASE_DIR"] = str(exe_dir)
    return exe_dir


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_ready(url: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def main():
    base_dir = _configure_base_dir()
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    print(f"\n  NemoOC Web  ->  {base_url}")
    print(f"  Datos/config -> {base_dir}")
    print("  (cierra esta ventana para detener)\n")

    def _run():
        import uvicorn
        # Importar app directamente (no como string) para que PyInstaller
        # detecte el paquete 'backend' durante el análisis estático.
        from backend.main import app as _app
        uvicorn.run(_app, host="127.0.0.1", port=port, log_level="warning")

    threading.Thread(target=_run, daemon=True).start()

    if _wait_ready(f"{base_url}/api/health"):
        print(f"  Servidor listo. Abriendo navegador...")
        webbrowser.open(base_url)
    else:
        print(f"  Servidor tardó demasiado. Abre manualmente: {base_url}")
        webbrowser.open(base_url)

    # Mantener proceso vivo mientras el hilo daemon corre
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCerrando NemoOC Web...")


if __name__ == "__main__":
    main()
