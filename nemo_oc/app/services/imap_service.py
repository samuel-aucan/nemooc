"""
Servicio IMAP para leer OCs privadas desde Gmail.
Busca emails no leídos con PDFs adjuntos que coincidan con el filtro de asunto.
Usa la misma App Password que el servicio SMTP (Gmail).
"""
import email
import imaplib
import logging
import os
import re
import tempfile
from email.header import decode_header
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _decode_str(value: str) -> str:
    """Decodifica encabezados de email (pueden venir en base64 o quoted-printable)."""
    if not value:
        return ""
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _extract_body_text(msg) -> str:
    """Extrae una version de texto plano del correo para rescatar metadata reenviada."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() != "text/plain":
                continue
            disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in disposition.lower():
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _extract_forwarded_from(body_text: str) -> str:
    """Intenta rescatar el remitente original desde un correo reenviado."""
    if not body_text:
        return ""

    patterns = [
        r"^From:\s.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        r"^De:\s.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    ]
    for pattern in patterns:
        m = re.search(pattern, body_text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip().lower()
    return ""


def buscar_ocs_gmail(
    smtp_user: str,
    smtp_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    filter_subject: str = "ORDEN DE COMPRA",
    marcar_leidos: bool = True,
) -> List[Tuple[dict, str]]:
    """
    Conecta a Gmail vía IMAP y busca emails no leídos con PDFs adjuntos.

    Retorna lista de (metadata_dict, pdf_path_temporal).
    Los PDFs se guardan en archivos temporales; el llamador debe borrarlos cuando termine.

    metadata_dict contiene:
        - subject: asunto del email
        - from_addr: remitente
        - date: fecha del email
        - message_id: ID único del mensaje
    """
    if not smtp_user or not smtp_password:
        raise ValueError("Se requieren credenciales SMTP/IMAP para conectar a Gmail.")

    resultados: List[Tuple[dict, str]] = []

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)

        # Buscar emails no leídos que contengan el filtro en el asunto
        # IMAP search por asunto (case-insensitive en Gmail)
        search_query = f'(UNSEEN SUBJECT "{filter_subject}")'
        status, data = mail.search(None, search_query)

        if status != "OK" or not data[0]:
            logger.info(f"IMAP: No hay emails nuevos con asunto '{filter_subject}'")
            mail.logout()
            return []

        message_ids = data[0].split()
        logger.info(f"IMAP: {len(message_ids)} email(s) encontrados con asunto '{filter_subject}'")

        for msg_id in message_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject   = _decode_str(msg.get("Subject", ""))
            from_addr = _decode_str(msg.get("From", ""))
            date_str  = msg.get("Date", "")
            message_id = msg.get("Message-ID", str(msg_id))
            body_text = _extract_body_text(msg)
            forwarded_from = _extract_forwarded_from(body_text)

            metadata = {
                "subject":    subject,
                "from_addr":  from_addr,
                "date":       date_str,
                "message_id": message_id,
                "body_text": body_text,
                "forwarded_from": forwarded_from,
            }

            # Extraer adjuntos PDF
            pdfs_encontrados = []
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition  = str(part.get("Content-Disposition", ""))

                if content_type == "application/pdf" or (
                    "attachment" in disposition and
                    part.get_filename("").lower().endswith(".pdf")
                ):
                    filename = _decode_str(part.get_filename("adjunto.pdf"))
                    payload  = part.get_payload(decode=True)
                    if payload:
                        # Guardar en archivo temporal
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".pdf", prefix="redsalud_", delete=False
                        )
                        tmp.write(payload)
                        tmp.close()
                        pdfs_encontrados.append(tmp.name)
                        logger.info(f"  PDF descargado: {filename} → {tmp.name}")

            for pdf_path in pdfs_encontrados:
                resultados.append((metadata, pdf_path))

            # Marcar como leído para no reprocesar
            if marcar_leidos and pdfs_encontrados:
                mail.store(msg_id, "+FLAGS", "\\Seen")

        mail.logout()

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado en IMAP: {e}")

    return resultados


def limpiar_temporales(pdf_paths: List[str]) -> None:
    """Borra los archivos temporales creados durante la descarga."""
    for path in pdf_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass
