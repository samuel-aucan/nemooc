"""
Orquestador de sincronizacion de OCs privadas multi-holding.
Lee Gmail, detecta holding, parsea PDFs, homologa, audita y persiste.
"""

from __future__ import annotations

import logging
import os
import queue
import re
import threading
from datetime import datetime

from app.models.linea_oc import LineaOC
from app.models.orden_compra import OrdenCompra
from app.repositories import oc_repository
from app.services.document_snapshot_service import save_html_snapshot
from app.services.imap_service import (
    buscar_artikos_emails_gmail,
    buscar_ocs_gmail,
    limpiar_temporales,
    marcar_artikos_email_leido_gmail,
)
from app.services.private_holding_service import (
    detect_holding,
    detect_holding_from_identity,
    lookup_private_catalog,
    parse_private_pdf,
    save_private_audit,
)
from app.utils.rut_utils import rut_to_cliente_sap

logger = logging.getLogger(__name__)


def run_sync_privado(
    smtp_user: str,
    smtp_password: str,
    imap_server: str,
    imap_port: int,
    imap_folder: str,
    filter_from: str,
    progress_queue: queue.Queue,
) -> None:
    """
    Worker de sincronizacion privada.
    """
    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Buscando OCs Artikos en Gmail...")
    try:
        artikos_emails = buscar_artikos_emails_gmail(
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            imap_server=imap_server,
            imap_port=imap_port,
            imap_folder=imap_folder,
            marcar_leidos=False,
        )
    except Exception as e:
        emit("log", message=f"Advertencia: no se pudo buscar emails Artikos: {e}")
        artikos_emails = []

    if artikos_emails:
        from app.config import load_config
        from app.services.artikos_scraper import scrape_oc_with_metadata as artikos_scrape
        emit("log", message=f"Emails Artikos encontrados: {len(artikos_emails)}")
        existentes_artikos = oc_repository.get_existing_codes()
        cfg = load_config()
        for meta, url in artikos_emails:
            codigo_hint = _normalize_private_oc_code(meta.get("codigo_oc_hint", ""))
            doc_source = oc_repository.get_document_source(codigo_hint) if codigo_hint else None
            if (
                codigo_hint
                and codigo_hint in existentes_artikos
                and doc_source
                and (doc_source.get("source_type") or "").strip().lower() == "artikos"
            ):
                _mark_artikos_email_as_read(
                    meta,
                    smtp_user=smtp_user,
                    smtp_password=smtp_password,
                    imap_server=imap_server,
                    imap_port=imap_port,
                    imap_folder=imap_folder,
                )
                emit("log", message=f"  Artikos {codigo_hint} ya estaba procesada, omitida")
                continue

            try:
                oc, lineas, scrape_meta = artikos_scrape(
                    url,
                    rut_proveedor=cfg.rut_proveedor,
                    codigo_empresa=cfg.codigo_empresa,
                )
            except Exception as e:
                emit("log", message=f"  ERROR scraping Artikos ({meta.get('subject','')}): {e}")
                continue

            detection = detect_holding_from_identity(
                rut_value=oc.rut_unidad,
                buyer_name=oc.nombre_organismo,
                metadata=meta,
            )
            if detection.resolved:
                oc.codigo_organismo = detection.holding_id
                oc.codigo_tipo = detection.holding_id.upper()

            snapshot_meta = save_html_snapshot("artikos", oc.codigo_oc, scrape_meta.get("html", ""))
            access_payload = {
                "credential_kind": scrape_meta.get("credential_kind", ""),
                "credential_preview": scrape_meta.get("credential_preview", ""),
                "credential_attempts": scrape_meta.get("credential_attempts", []),
                "hidden_fields": scrape_meta.get("hidden_fields", []),
                "print_available": bool(scrape_meta.get("print_available")),
            }

            if oc.codigo_oc in existentes_artikos:
                try:
                    oc_repository.upsert_document_source(
                        oc.codigo_oc,
                        source_type="artikos",
                        source_locator=url,
                        access_payload=access_payload,
                        document_available=True,
                        document_regenerable=True,
                        last_verified_at=scrape_meta.get("verified_at", ""),
                        **snapshot_meta,
                    )
                    _mark_artikos_email_as_read(
                        meta,
                        smtp_user=smtp_user,
                        smtp_password=smtp_password,
                        imap_server=imap_server,
                        imap_port=imap_port,
                        imap_folder=imap_folder,
                    )
                    emit("log", message=f"  Artikos {oc.codigo_oc} ya existe en BD, respaldo actualizado")
                except Exception as e:
                    emit("log", message=f"  ERROR actualizando respaldo Artikos {oc.codigo_oc}: {e}")
                continue
            try:
                oc_repository.save_oc(oc, lineas)
                oc_repository.upsert_document_source(
                    oc.codigo_oc,
                    source_type="artikos",
                    source_locator=url,
                    access_payload=access_payload,
                    document_available=True,
                    document_regenerable=True,
                    last_verified_at=scrape_meta.get("verified_at", ""),
                    **snapshot_meta,
                )
                existentes_artikos.add(oc.codigo_oc)
                _mark_artikos_email_as_read(
                    meta,
                    smtp_user=smtp_user,
                    smtp_password=smtp_password,
                    imap_server=imap_server,
                    imap_port=imap_port,
                    imap_folder=imap_folder,
                )
                emit("log", message=f"  OK Artikos: OC {oc.codigo_oc} — {oc.nombre_organismo} ({len(lineas)} líneas)")
            except Exception as e:
                emit("log", message=f"  ERROR guardando Artikos {oc.codigo_oc}: {e}")

    emit("log", message="Buscando OCs privadas en Gmail...")

    try:
        resultados = buscar_ocs_gmail(
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            imap_server=imap_server,
            imap_port=imap_port,
            imap_folder=imap_folder,
            filter_from=filter_from,
        )
    except Exception as e:
        emit("error", message=f"Error conectando a Gmail: {e}")
        return

    total = len(resultados)
    emit("log", message=f"Emails con PDF encontrados: {total}")
    emit("progress", current=0, total=max(total, 1))

    if total == 0:
        emit("done", message="No hay OCs privadas nuevas en Gmail.", nuevas=0, errores=0)
        return

    nuevas = 0
    errores = 0
    pdfs_temp = [r[1] for r in resultados]

    try:
        existentes = oc_repository.get_existing_codes()
    except Exception as e:
        emit("error", message=f"Error accediendo a la base de datos: {e}")
        limpiar_temporales(pdfs_temp)
        return

    for i, (metadata, pdf_path) in enumerate(resultados, start=1):
        emit("progress", current=i, total=total)

        try:
            detection = detect_holding(pdf_path, metadata)
        except Exception as e:
            emit("log", message=f"  ERROR detectando holding ({metadata.get('subject', '')}): {e}")
            errores += 1
            continue

        if not detection.resolved:
            codigo_oc = _fallback_codigo_oc(pdf_path, i)
            if codigo_oc in existentes:
                emit("log", message=f"  [{i}/{total}] {codigo_oc} - ya existe en BD, omitida")
                continue

            _save_pending_unknown_oc(codigo_oc, metadata, detection, pdf_path)
            _upsert_imap_document_source(codigo_oc, metadata, pdf_path)
            save_private_audit(
                codigo_oc=codigo_oc,
                detection=detection,
                metadata=metadata,
                precio_validacion="sin_revision",
                detalle_validacion="Holding no reconocido automaticamente",
                requiere_revision=True,
            )
            nuevas += 1
            emit("log", message=f"  [{i}/{total}] {codigo_oc} - holding no reconocido, quedo Pendiente")
            continue

        try:
            cabecera, lineas_raw = parse_private_pdf(pdf_path, detection.parser_type)
        except Exception as e:
            emit("log", message=f"  ERROR parseando PDF {detection.holding_nombre}: {e}")
            errores += 1
            continue

        num_oc = cabecera.get("numero_oc", "")
        if not num_oc:
            emit("log", message=f"  ERROR: PDF sin numero de OC ({metadata.get('subject', '')})")
            errores += 1
            continue

        codigo_oc = _normalize_private_oc_code(num_oc)
        emit("log", message=f"  [{i}/{total}] {codigo_oc} - {detection.holding_nombre} ({detection.confidence:.2f})")

        if codigo_oc in existentes:
            emit("log", message="    Ya existe en BD - omitida")
            continue

        now = datetime.now().isoformat()
        cliente_sap = rut_to_cliente_sap(cabecera.get("rut_empresa", ""))
        lineas, sin_homo, price_warnings = _build_lineas(codigo_oc, lineas_raw, detection.holding_id, now)
        nombre_empresa = (
            detection.emisor_detectado
            or cabecera.get("empresa", "")
            or cabecera.get("nombre_unidad", "")
            or detection.holding_nombre
        )

        requiere_revision = detection.confidence < 0.8 or bool(sin_homo)
        estado_interno = "Pendiente" if requiere_revision else "Nueva"
        notas = _build_private_notes(detection, cabecera, price_warnings, sin_homo)

        oc = OrdenCompra(
            codigo_oc=codigo_oc,
            nombre_oc=f"OC {detection.holding_nombre} {num_oc}",
            estado_mp="Enviada",
            tipo_oc="PRIVADA",
            codigo_tipo=detection.holding_id.upper(),
            fecha_envio=cabecera.get("fecha_oc", ""),
            fecha_creacion=cabecera.get("fecha_oc", ""),
            total_neto=cabecera.get("neto_afecto", 0.0),
            impuestos=cabecera.get("iva", 0.0),
            total=cabecera.get("total_bruto", 0.0),
            porcentaje_iva=19.0,
            moneda="CLP",
            codigo_organismo=detection.holding_id,
            nombre_organismo=nombre_empresa,
            rut_unidad=cabecera.get("rut_empresa", ""),
            nombre_unidad=cabecera.get("nombre_unidad", "") or nombre_empresa,
            direccion_unidad=cabecera.get("dir_entrega", ""),
            rut_proveedor="76.215.260-6",
            nombre_proveedor="NEMO CHILE S.A.",
            cliente_sap_sugerido=cliente_sap,
            cantidad_lineas=len(lineas),
            estado_interno=estado_interno,
            notas=notas,
            created_at=now,
            updated_at=now,
        )

        try:
            oc_repository.save_oc(oc, lineas)
            _upsert_imap_document_source(codigo_oc, metadata, pdf_path)
            save_private_audit(
                codigo_oc=codigo_oc,
                detection=detection,
                metadata=metadata,
                precio_validacion="con_alertas" if price_warnings else "ok",
                detalle_validacion=_format_price_warnings(price_warnings),
                requiere_revision=requiere_revision,
            )
            nuevas += 1

            n_homo = len(lineas) - len(sin_homo)
            msg = f"    OK: {len(lineas)} lineas, {n_homo} homologadas"
            if sin_homo:
                msg += f", {len(sin_homo)} sin homologacion (pos: {sin_homo})"
            if price_warnings:
                msg += f", {len(price_warnings)} alerta(s) de precio"
            if requiere_revision:
                msg += " -> estado Pendiente"
            emit("log", message=msg)
        except Exception as e:
            emit("log", message=f"    ERROR guardando {codigo_oc}: {e}")
            errores += 1
            continue

        try:
            from app.config import load_config as _load_cfg
            from app.services.cartera_service import get_cartera_service
            from app.services.email_service import get_email_service

            _cfg = _load_cfg()
            if _cfg.smtp_enabled and oc.cliente_sap_sugerido:
                _cliente = get_cartera_service().lookup(oc.cliente_sap_sugerido)
                if _cliente:
                    get_email_service().enviar_notificacion_oc(oc, _cliente)
        except Exception as _e:
            logger.warning(f"Email no enviado para {oc.codigo_oc}: {_e}")

    limpiar_temporales(pdfs_temp)

    resumen = (
        f"Sincronizacion privada completada. "
        f"Nuevas: {nuevas} | Errores: {errores} | "
        f"Omitidas (ya existian): {total - nuevas - errores}"
    )
    emit("log", message=resumen)
    emit("done", message=resumen, nuevas=nuevas, errores=errores)


def _build_lineas(
    codigo_oc: str,
    lineas_raw: list[dict],
    holding_id: str,
    now: str,
) -> tuple[list[LineaOC], list[int], list[str]]:
    lineas: list[LineaOC] = []
    sin_homo: list[int] = []
    price_warnings: list[str] = []

    for idx, raw in enumerate(lineas_raw, start=1):
        codigo_cliente = str(raw.get("codigo", "")).strip()
        homo = lookup_private_catalog(holding_id, codigo_cliente)

        itemcode = None
        desc_sap = None
        precio_ref = 0.0
        estado_homo = "sin_homologacion"
        if homo and homo.itemcode_sap:
            itemcode = homo.itemcode_sap
            desc_sap = homo.descripcion or raw.get("descripcion", "")
            precio_ref = homo.precio_ref or 0.0
            estado_homo = "homologado"
        else:
            sin_homo.append(raw.get("pos", idx))

        precio_pdf = raw.get("precio_unit", 0.0) or 0.0
        if precio_ref > 0:
            delta = abs(precio_pdf - precio_ref)
            if delta > max(1.0, precio_ref * 0.03):
                price_warnings.append(
                    f"pos {raw.get('pos', idx)}: pdf={precio_pdf:.2f} ref={precio_ref:.2f}"
                )

        lineas.append(LineaOC(
            codigo_oc=codigo_oc,
            correlativo=raw.get("pos", idx),
            codigo_mp=codigo_cliente or None,
            codigo_producto_api=codigo_cliente,
            producto=raw.get("descripcion", ""),
            especificacion_comprador=raw.get("descripcion", ""),
            especificacion_proveedor="",
            cantidad=raw.get("cantidad", 1.0),
            unidad=raw.get("unidad", "UN"),
            precio_neto=precio_pdf,
            total=raw.get("valor_total", 0.0),
            factor_empaque=1.0,
            cantidad_sap=raw.get("cantidad", 1.0),
            precio_sap=round(float(precio_pdf or 0), 4),
            itemcode_sap=itemcode,
            descripcion_sap=desc_sap,
            estado_homologacion=estado_homo,
            created_at=now,
            updated_at=now,
        ))

    return lineas, sin_homo, price_warnings


def _normalize_private_oc_code(raw_code: str) -> str:
    code = (raw_code or "").strip()
    digits = re.sub(r"\D+", "", code)
    return digits or code


def _mark_artikos_email_as_read(
    metadata: dict,
    *,
    smtp_user: str,
    smtp_password: str,
    imap_server: str,
    imap_port: int,
    imap_folder: str,
) -> bool:
    imap_uid = str(metadata.get("imap_uid") or "").strip()
    if not imap_uid:
        return False
    return marcar_artikos_email_leido_gmail(
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        imap_uid=imap_uid,
        imap_server=imap_server,
        imap_port=imap_port,
        imap_folder=imap_folder,
    )


def _build_private_notes(detection, cabecera: dict, price_warnings: list[str], sin_homo: list[int]) -> str:
    notes = [
        f"Holding: {detection.holding_nombre}",
        f"Deteccion: {detection.metodo_deteccion or 'sin detalle'}",
        f"Confianza: {detection.confidence:.2f}",
    ]
    if cabecera.get("condicion_pago"):
        notes.append(f"Pago: {cabecera['condicion_pago']}")
    if cabecera.get("contrato_marco"):
        notes.append(f"Contrato Marco: {cabecera['contrato_marco']}")
    if sin_homo:
        notes.append(f"Sin homologacion: {sin_homo}")
    if price_warnings:
        notes.append(f"Alertas de precio: {len(price_warnings)}")
    return " | ".join(notes)


def _format_price_warnings(price_warnings: list[str]) -> str:
    if not price_warnings:
        return "Sin diferencias relevantes de precio"
    return " ; ".join(price_warnings[:10])


def _fallback_codigo_oc(pdf_path: str, seq: int) -> str:
    from pathlib import Path

    stem = Path(pdf_path).stem.upper()
    stem = "".join(ch for ch in stem if ch.isalnum())[:18]
    return f"PR-PEND-{stem or seq}"


def _save_pending_unknown_oc(codigo_oc: str, metadata: dict, detection, pdf_path: str) -> None:
    now = datetime.now().isoformat()
    notas = " | ".join([
        "Holding no reconocido automaticamente",
        f"Asunto: {metadata.get('subject', '')}",
        f"Remitente: {metadata.get('forwarded_from') or metadata.get('from_addr') or ''}",
        f"Archivo: {pdf_path}",
    ])
    oc = OrdenCompra(
        codigo_oc=codigo_oc,
        nombre_oc="OC Privada Pendiente de Clasificacion",
        estado_mp="Pendiente",
        tipo_oc="PRIVADA",
        fecha_creacion=now[:10],
        fecha_envio=now[:10],
        nombre_organismo=detection.emisor_detectado or "No identificado",
        rut_unidad=detection.rut_emisor_norm,
        nombre_unidad=detection.emisor_detectado or "No identificado",
        estado_interno="Pendiente",
        notas=notas,
        created_at=now,
        updated_at=now,
    )
    oc_repository.save_oc(oc, [])


def _upsert_imap_document_source(codigo_oc: str, metadata: dict, pdf_path: str) -> None:
    attachment_filename = (metadata.get("attachment_filename") or "orden_compra.pdf").strip()
    imap_folder = (metadata.get("imap_folder") or "INBOX").strip()
    imap_uid = str(metadata.get("imap_uid") or "").strip()
    message_id = str(metadata.get("message_id") or "").strip()
    attachment_index = int(metadata.get("attachment_index") or 1)
    attachment_sha256 = str(metadata.get("attachment_sha256") or "").strip()
    attachment_size = int(metadata.get("attachment_size_bytes") or 0)
    if not attachment_size and pdf_path and os.path.exists(pdf_path):
        try:
            attachment_size = os.path.getsize(pdf_path)
        except Exception:
            attachment_size = 0

    source_locator = f"imap://{imap_folder}/{imap_uid or message_id}/{attachment_filename}"
    access_payload = {
        "imap_uid": imap_uid,
        "message_id": message_id,
        "imap_folder": imap_folder,
        "attachment_filename": attachment_filename,
        "attachment_index": attachment_index,
        "attachment_sha256": attachment_sha256,
        "attachment_size_bytes": attachment_size,
        "email_subject": metadata.get("subject", ""),
        "email_date": metadata.get("date", ""),
        "email_from": metadata.get("forwarded_from") or metadata.get("from_addr") or "",
    }
    oc_repository.upsert_document_source(
        codigo_oc,
        source_type="imap_attachment",
        source_locator=source_locator,
        access_payload=access_payload,
        snapshot_type="",
        snapshot_path="",
        snapshot_sha256=attachment_sha256,
        snapshot_size_bytes=attachment_size,
        document_available=True,
        document_regenerable=True,
        last_verified_at=datetime.now().isoformat(),
    )


def start_sync_privado_thread(
    smtp_user: str,
    smtp_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    filter_from: str = "ordenesdecompra@nemochile.cl",
) -> queue.Queue:
    """Inicia el sync privado en thread daemon y retorna la Queue de progreso."""
    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=run_sync_privado,
        args=(smtp_user, smtp_password, imap_server, imap_port, imap_folder, filter_from, q),
        daemon=True,
        name="SyncPrivadoThread",
    )
    t.start()
    return q
