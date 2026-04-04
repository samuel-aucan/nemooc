"""
Orquestador de sincronizacion de OCs privadas multi-holding.
Lee Gmail, detecta holding, parsea PDFs, homologa, audita y persiste.
"""

from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime

from app.models.linea_oc import LineaOC
from app.models.orden_compra import OrdenCompra
from app.repositories import oc_repository
from app.services.imap_service import buscar_ocs_gmail, limpiar_temporales
from app.services.private_holding_service import (
    detect_holding,
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
    filter_subject: str,
    progress_queue: queue.Queue,
) -> None:
    """
    Worker de sincronizacion privada.
    """
    def emit(tipo: str, **kwargs):
        progress_queue.put({"type": tipo, **kwargs})

    emit("log", message="Buscando OCs privadas en Gmail...")

    try:
        resultados = buscar_ocs_gmail(
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            imap_server=imap_server,
            imap_port=imap_port,
            imap_folder=imap_folder,
            filter_subject=filter_subject,
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

        codigo_oc = f"{detection.prefijo}-{num_oc}"
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
            precio_sap=precio_pdf,
            itemcode_sap=itemcode,
            descripcion_sap=desc_sap,
            estado_homologacion=estado_homo,
            created_at=now,
            updated_at=now,
        ))

    return lineas, sin_homo, price_warnings


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


def start_sync_privado_thread(
    smtp_user: str,
    smtp_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    filter_subject: str = "ORDEN DE COMPRA",
) -> queue.Queue:
    """Inicia el sync privado en thread daemon y retorna la Queue de progreso."""
    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=run_sync_privado,
        args=(smtp_user, smtp_password, imap_server, imap_port, imap_folder, filter_subject, q),
        daemon=True,
        name="SyncPrivadoThread",
    )
    t.start()
    return q
