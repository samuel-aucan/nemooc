"""
Helpers para persistir snapshots livianos de documentos asociados a una OC.
"""

from __future__ import annotations

import gzip
import hashlib
import re

from app.config import get_data_dir


def save_html_snapshot(source_type: str, codigo_oc: str, html: str) -> dict:
    """
    Guarda un snapshot HTML comprimido y retorna metadatos persistibles en BD.
    """
    source_safe = _safe_segment(source_type or "generic")
    code_safe = _safe_segment(codigo_oc or "sin-codigo")

    target_dir = get_data_dir() / "documents" / source_safe
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{code_safe}.html.gz"
    payload = (html or "").encode("utf-8")

    with gzip.open(target_path, "wb") as fh:
        fh.write(payload)

    relative_path = target_path.relative_to(get_data_dir()).as_posix()
    return {
        "snapshot_type": "html_gzip",
        "snapshot_path": relative_path,
        "snapshot_sha256": hashlib.sha256(payload).hexdigest(),
        "snapshot_size_bytes": target_path.stat().st_size,
    }


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "file"
