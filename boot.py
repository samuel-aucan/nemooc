"""
Boot script para Railway.
Se descarga desde GitHub en cada arranque via startCommand,
luego descarga los módulos que falten en la imagen cacheada y arranca uvicorn.
"""
import os, sys, time, urllib.request as _r

print(f"[boot] starting at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", flush=True)

_BASE = "https://raw.githubusercontent.com/samuel-aucan/nemooc/main"

_PATCH = [
    ("nemo_oc_web/backend/api/gd_routes.py",           "/app/nemo_oc_web/backend/api/gd_routes.py"),
    ("nemo_oc_web/backend/api/poc_sse.py",              "/app/nemo_oc_web/backend/api/poc_sse.py"),
    ("nemo_oc_web/backend/core/repo_selector.py",       "/app/nemo_oc_web/backend/core/repo_selector.py"),
    ("nemo_oc_web/backend/supabase_oc_repository.py",   "/app/nemo_oc_web/backend/supabase_oc_repository.py"),
    ("nemo_oc_web/backend/supabase_write_service.py",   "/app/nemo_oc_web/backend/supabase_write_service.py"),
    ("nemo_oc_web/backend/main.py",                     "/app/nemo_oc_web/backend/main.py"),
    ("nemo_oc_web/backend/api/oc_routes.py",            "/app/nemo_oc_web/backend/api/oc_routes.py"),
    ("nemo_oc_web/backend/api/schemas.py",              "/app/nemo_oc_web/backend/api/schemas.py"),
    ("nemo_oc/app/services/sync_service.py",            "/app/nemo_oc/app/services/sync_service.py"),
    ("nemo_oc/app/services/sap_mode_service.py",        "/app/nemo_oc/app/services/sap_mode_service.py"),
]

_ok, _fail = 0, 0
for _src, _dst in _PATCH:
    try:
        _r.urlretrieve(f"{_BASE}/{_src}", _dst)
        _ok += 1
    except Exception as _e:
        _fail += 1
        print(f"[boot] WARN {_dst}: {_e}", flush=True)

print(f"[boot] patched {_ok}/{len(_PATCH)} files ({_fail} failed)", flush=True)

# Garantizar paths
for _p in ["/app/nemo_oc_web", "/app/nemo_oc"]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import uvicorn
_port = int(os.environ.get("PORT", 8000))
print(f"[boot] starting uvicorn on port {_port}", flush=True)
uvicorn.run("backend.main:app", host="0.0.0.0", port=_port, log_level="info")
