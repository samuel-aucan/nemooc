"""
Servicio IMAP para leer OCs privadas desde Gmail.
Busca emails no leídos con PDFs adjuntos que coincidan con el filtro de asunto.
Usa la misma App Password que el servicio SMTP (Gmail).
"""
import email
import html as html_module
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
    filter_from: str = "ordenesdecompra@nemochile.cl",
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

        # Buscar emails no leídos enviados por el remitente indicado
        search_query = f'(UNSEEN FROM "{filter_from}")'
        status, data = mail.search(None, search_query)

        if status != "OK" or not data[0]:
            logger.info(f"IMAP: No hay emails nuevos del remitente '{filter_from}'")
            mail.logout()
            return []

        message_ids = data[0].split()
        logger.info(f"IMAP: {len(message_ids)} email(s) encontrados del remitente '{filter_from}'")

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


def buscar_artikos_emails_gmail(
    smtp_user: str,
    smtp_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    marcar_leidos: bool = True,
) -> List[Tuple[dict, str]]:
    """
    Busca emails no leídos de Artikos y extrae la URL de OC del cuerpo.

    Retorna lista de (metadata_dict, url_artikos).
    """
    _ARTIKOS_URL_RE = re.compile(
        r'https?://art-p-ptk\.artikos\.cl/[^\s\'"<>\r\n]+Key2=[^\s\'"<>\r\n]+',
        re.IGNORECASE,
    )

    if not smtp_user or not smtp_password:
        raise ValueError("Se requieren credenciales SMTP/IMAP para conectar a Gmail.")

    resultados: List[Tuple[dict, str]] = []

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)

        # Los emails de Artikos llegan reenviados con asunto "Nueva Orden de Compra"
        status, data = mail.search(None, '(UNSEEN SUBJECT "Nueva Orden de Compra")')
        if status != "OK" or not data[0]:
            logger.info("IMAP Artikos: no hay emails nuevos con asunto 'Nueva Orden de Compra'")
            mail.logout()
            return []

        message_ids = data[0].split()
        logger.info(f"IMAP Artikos: {len(message_ids)} email(s) encontrados")

        for msg_id in message_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject    = _decode_str(msg.get("Subject", ""))
            from_addr  = _decode_str(msg.get("From", ""))
            date_str   = msg.get("Date", "")
            message_id = msg.get("Message-ID", str(msg_id))

            # Extraer URL del cuerpo (texto plano o HTML)
            url = None
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype not in ("text/plain", "text/html"):
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
                m = _ARTIKOS_URL_RE.search(body)
                if m:
                    # Decodificar entidades HTML (&amp; → &) que aparecen en href="..."
                    url = html_module.unescape(m.group(0).strip())
                    break

            if not url:
                logger.warning(f"IMAP Artikos: email sin URL reconocible (asunto: {subject!r})")
                continue

            metadata = {
                "subject":    subject,
                "from_addr":  from_addr,
                "date":       date_str,
                "message_id": message_id,
            }
            resultados.append((metadata, url))

            if marcar_leidos:
                mail.store(msg_id, "+FLAGS", "\\Seen")

        mail.logout()

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP Artikos: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado en IMAP Artikos: {e}")

    return resultados
