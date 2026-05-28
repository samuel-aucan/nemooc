"""Entrypoint para Railway/Docker: agrega paths explícitamente y arranca uvicorn."""
import os
import sys

# Garantizar que los módulos se encuentren sin depender de PYTHONPATH externo
_base = os.path.dirname(os.path.abspath(__file__))
_nemo_oc_web = os.path.join(_base, "nemo_oc_web")
_nemo_oc = os.path.join(_base, "nemo_oc")

for _p in [_nemo_oc_web, _nemo_oc]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Diagnóstico
print(f"[start.py] CWD: {os.getcwd()}", flush=True)
print(f"[start.py] sys.path: {sys.path[:4]}", flush=True)
_api_dir = os.path.join(_nemo_oc_web, "backend", "api")
if os.path.isdir(_api_dir):
    print(f"[start.py] backend/api files: {os.listdir(_api_dir)}", flush=True)
else:
    print(f"[start.py] WARNING: {_api_dir} does not exist!", flush=True)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )
