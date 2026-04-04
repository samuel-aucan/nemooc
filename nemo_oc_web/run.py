"""
NemoOC Web — Script de arranque.
Levanta backend FastAPI (puerto 8000) y frontend Vite (puerto 5173) en paralelo.

Uso:
    cd nemo_oc_web
    python run.py

Luego abrir: http://localhost:5173
"""
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    print("=" * 50)
    print("  NemoOC Web")
    print("  Backend:  http://localhost:8001")
    print("  Frontend: http://localhost:5173")
    print("  Ctrl+C para detener")
    print("=" * 50)

    # Backend: uvicorn desde nemo_oc_web/
    backend = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8001",
            "--reload",
        ],
        cwd=str(ROOT),
    )

    # Frontend: npm run dev desde nemo_oc_web/frontend/
    frontend_dir = ROOT / "frontend"
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=str(frontend_dir),
    )

    def shutdown(sig=None, frame=None):
        print("\nDeteniendo servidores...")
        backend.terminate()
        frontend.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, shutdown)

    # Esperar a que alguno termine (o Ctrl+C)
    try:
        backend.wait()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
