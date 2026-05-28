"""
Servicios de deteccion y homologacion para OCs privadas multi-holding.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Optional

from app.db import get_connection
from app.utils.rut_utils import normalize_rut, normalize_rut_body

logger = logging.getLogger(__name__)

_RUT_RE = re.compile(r"(\d{1,2}(?:\.\d{3}){2}-[\dkK]|\d{7,8}-[\dkK])")
_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)


@dataclass
class HoldingCatalogItem:
    codigo_cliente: str
    holding_id: str
    descripcion: str = ""
    itemcode_sap: str = ""
    precio_ref: float = 0.0


@dataclass
class HoldingDetection:
    holding_id: str = ""
    holding_nombre: str = ""
    prefijo: str = "PR"
    parser_type: str = ""
    confidence: float = 0.0
    metodo_deteccion: str = ""
    rut_emisor_norm: str = ""
    emisor_detectado: str = ""
    raw_text: str = ""
    evidence: list[str] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return bool(self.holding_id and self.parser_type)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def _extract_pdf_text(pdf_path: str, max_pages: int = 2) -> str:
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages[:max_pages])


def _extract_ruts(text: str) -> list[str]:
    seen: list[str] = []
    for raw in _RUT_RE.findall(text or ""):
        norm = normalize_rut(raw)
        if norm and norm not in seen:
            seen.append(norm)
    return seen


def _sender_candidates(metadata: dict) -> Iterable[str]:
    for key in ("forwarded_from", "from_addr"):
        value = (metadata.get(key) or "").strip()
        if value:
            yield value.lower()


def _sender_domains(senders: Iterable[str]) -> list[str]:
    domains: list[str] = []
    for sender in senders:
        matches = _EMAIL_RE.findall(sender or "")
        if matches:
            for domain in matches:
                domain = domain.lower().strip()
                if domain and domain not in domains:
                    domains.append(domain)
            continue

        sender = (sender or "").lower().strip()
        if "@" in sender:
            candidate = sender.split("@")[-1].strip(" >)")
            if candidate and candidate not in domains:
                domains.append(candidate)
    return domains


def _detect_holding_from_sources(
    raw_text: str,
    rut_candidates: list[str],
    metadata: Optional[dict] = None,
) -> HoldingDetection:
    metadata = metadata or {}
    norm_text = _normalize_text(raw_text)
    subject = (metadata.get("subject") or "").lower()
    senders = list(_sender_candidates(metadata))
    sender_domains = _sender_domains(senders)

    conn = get_connection()
    try:
        holdings = {
            row["id"]: row
            for row in conn.execute(
                "SELECT id, nombre, prefijo, parser_type FROM holdings WHERE activo = 1"
            ).fetchall()
        }
        scores: dict[str, int] = {}
        evidence: dict[str, list[str]] = {}
        emitter_name: dict[str, str] = {}

        for rut_norm in rut_candidates:
            rut_body = normalize_rut_body(rut_norm)
            rows = conn.execute(
                """
                SELECT holding_id, rut_norm, rut_display, nombre_sucursal
                FROM holding_ruts
                WHERE rut_norm = ?
                   OR (? <> '' AND substr(rut_norm, 1, length(?)) = ?)
                """,
                (rut_norm, rut_body, rut_body, rut_body),
            ).fetchall()
            for row in rows:
                hid = row["holding_id"]
                exact_match = row["rut_norm"] == rut_norm
                scores[hid] = scores.get(hid, 0) + (120 if exact_match else 95)
                evidence_key = "rut" if exact_match else "rut_body"
                evidence.setdefault(hid, []).append(f"{evidence_key}:{rut_body or rut_norm}")
                emitter_name[hid] = row["nombre_sucursal"] or row["rut_display"] or rut_norm

        rule_rows = conn.execute(
            "SELECT holding_id, rule_type, rule_value, prioridad FROM holding_match_rules WHERE activo = 1"
        ).fetchall()
        for row in rule_rows:
            hid = row["holding_id"]
            if hid not in holdings:
                continue
            rule_type = row["rule_type"]
            rule_value = row["rule_value"] or ""
            rule_norm = _normalize_text(rule_value)
            matched = False
            weight = 0

            if rule_type == "pdf_rut" and rule_value in rut_candidates:
                matched = True
                weight = 95
            elif rule_type in ("pdf_text", "pdf_contains") and rule_norm and rule_norm in norm_text:
                matched = True
                weight = 35
            elif rule_type in ("email_from", "from_contains") and any(rule_value.lower() in sender for sender in senders):
                matched = True
                weight = 30
            elif rule_type == "email_domain" and any(
                domain == rule_value.lower() or domain.endswith(f".{rule_value.lower()}") or rule_value.lower() in domain
                for domain in sender_domains
            ):
                matched = True
                weight = 25
            elif rule_type == "subject_contains" and rule_value.lower() in subject:
                matched = True
                weight = 20

            if matched:
                scores[hid] = scores.get(hid, 0) + weight
                evidence.setdefault(hid, []).append(f"{rule_type}:{rule_value}")

        if not scores:
            return HoldingDetection(
                raw_text=raw_text,
                rut_emisor_norm=rut_candidates[0] if rut_candidates else "",
            )

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_id, best_score = ordered[0]
        second_score = ordered[1][1] if len(ordered) > 1 else 0
        confidence = _score_to_confidence(best_score, second_score)
        best = holdings[best_id]

        return HoldingDetection(
            holding_id=best_id,
            holding_nombre=best["nombre"],
            prefijo=best["prefijo"] or "PR",
            parser_type=best["parser_type"] or "",
            confidence=confidence,
            metodo_deteccion=" + ".join(sorted({ev.split(":", 1)[0] for ev in evidence.get(best_id, [])})),
            rut_emisor_norm=rut_candidates[0] if rut_candidates else "",
            emisor_detectado=emitter_name.get(best_id, "") or raw_text.strip(),
            raw_text=raw_text,
            evidence=evidence.get(best_id, []),
        )
    finally:
        conn.close()


def detect_holding(pdf_path: str, metadata: Optional[dict] = None) -> HoldingDetection:
    """
    Detecta el holding usando principalmente el PDF y, como apoyo, metadatos del email.
    """
    raw_text = _extract_pdf_text(pdf_path)
    rut_candidates = _extract_ruts(raw_text)
    return _detect_holding_from_sources(raw_text, rut_candidates, metadata)


def detect_holding_from_identity(
    rut_value: str = "",
    buyer_name: str = "",
    metadata: Optional[dict] = None,
) -> HoldingDetection:
    """
    Detecta el holding a partir del RUT y/o nombre del comprador, sin requerir PDF.
    Sirve para normalizar OCs privadas antiguas o flujos como Artikos.
    """
    rut_candidates: list[str] = []
    rut_norm = normalize_rut(rut_value)
    if rut_norm:
        rut_candidates.append(rut_norm)

    for extracted in _extract_ruts(buyer_name):
        if extracted not in rut_candidates:
            rut_candidates.append(extracted)

    return _detect_holding_from_sources(buyer_name or "", rut_candidates, metadata)


def _score_to_confidence(best_score: int, second_score: int) -> float:
    if best_score <= 0:
        return 0.0
    gap = best_score - second_score
    if best_score >= 180 and gap >= 60:
        return 0.99
    if best_score >= 120 and gap >= 40:
        return 0.95
    if best_score >= 80 and gap >= 20:
        return 0.85
    if best_score >= 35:
        return 0.7
    return 0.5


def parse_private_pdf(pdf_path: str, parser_type: str):
    if parser_type == "redsalud":
        from app.services.pdf_parser_redsalud import parse_pdf
    elif parser_type == "indisa":
        from app.services.pdf_parser_indisa import parse_pdf
    elif parser_type == "banmedica":
        from app.services.pdf_parser_banmedica import parse_pdf
    elif parser_type == "achs":
        from app.services.pdf_parser_achs import parse_pdf
    else:
        raise ValueError(f"Parser privado no soportado: {parser_type}")
    return parse_pdf(pdf_path)


def lookup_private_catalog(holding_id: str, codigo_cliente: str) -> Optional[HoldingCatalogItem]:
    if not holding_id or not codigo_cliente:
        return None

    codes = [str(codigo_cliente).strip()]
    if codes[0].isdigit():
        stripped = codes[0].lstrip("0")
        if stripped and stripped not in codes:
            codes.append(stripped)

    conn = get_connection()
    try:
        for code in codes:
            row = conn.execute(
                """
                SELECT codigo_cliente, holding_id, descripcion, itemcode_sap, precio_ref
                FROM homologacion_privados
                WHERE holding_id = ? AND codigo_cliente = ?
                """,
                (holding_id, code),
            ).fetchone()
            if row:
                return HoldingCatalogItem(
                    codigo_cliente=row["codigo_cliente"],
                    holding_id=row["holding_id"],
                    descripcion=row["descripcion"] or "",
                    itemcode_sap=row["itemcode_sap"] or "",
                    precio_ref=row["precio_ref"] or 0.0,
                )
    finally:
        conn.close()
    return None


def save_private_audit(
    codigo_oc: str,
    detection: HoldingDetection,
    metadata: Optional[dict],
    precio_validacion: str,
    detalle_validacion: str,
    requiere_revision: bool,
) -> None:
    from datetime import datetime

    metadata = metadata or {}
    now = datetime.now().isoformat()
    remitente = (metadata.get("forwarded_from") or metadata.get("from_addr") or "").strip()

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO oc_privado_auditoria
                (codigo_oc, holding_id, rut_emisor_norm, emisor_detectado, remitente_email,
                 asunto_email, metodo_deteccion, confianza, parser_usado, precio_validacion,
                 detalle_validacion, requiere_revision, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigo_oc,
                detection.holding_id or None,
                detection.rut_emisor_norm or None,
                detection.emisor_detectado or None,
                remitente or None,
                (metadata.get("subject") or "").strip() or None,
                detection.metodo_deteccion or None,
                detection.confidence,
                detection.parser_type or None,
                precio_validacion,
                detalle_validacion,
                1 if requiere_revision else 0,
                now,
                now,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"No se pudo guardar auditoria privada para {codigo_oc}: {e}")
    finally:
        conn.close()
