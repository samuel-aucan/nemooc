"""
IMAP service for private purchase orders received in Gmail.
"""

import email
import hashlib
import html as html_module
import imaplib
import logging
import os
import re
import tempfile
from email.message import Message
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

IMAP_LOOKBACK_DAYS = 1

try:
    CHILE_TZ = ZoneInfo("America/Santiago")
except ZoneInfoNotFoundError:
    CHILE_TZ = None


def _decode_str(value: str) -> str:
    """Decode email headers that may arrive encoded."""
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


def _current_chile_time() -> datetime:
    if CHILE_TZ is None:
        return datetime.now()
    return datetime.now(CHILE_TZ)


def _imap_since_dt(days_back: int = IMAP_LOOKBACK_DAYS) -> datetime:
    now = _current_chile_time()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_of_day - timedelta(days=max(days_back, 0))


def _format_imap_search_date(value: datetime) -> str:
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{value.day:02d}-{months[value.month - 1]}-{value.year}"


def _normalize_dt_for_compare(value: datetime) -> datetime:
    if CHILE_TZ is None:
        if value.tzinfo is None:
            return value
        return value.astimezone().replace(tzinfo=None)

    if value.tzinfo is None:
        return value.replace(tzinfo=CHILE_TZ)
    return value.astimezone(CHILE_TZ)


def _message_is_recent(date_str: str, since_dt: datetime) -> bool:
    if not date_str:
        return True

    try:
        parsed = parsedate_to_datetime(date_str)
    except (TypeError, ValueError, IndexError, OverflowError):
        return True

    if parsed is None:
        return True

    try:
        return _normalize_dt_for_compare(parsed) >= _normalize_dt_for_compare(since_dt)
    except Exception:
        return True


def _extract_body_text(msg) -> str:
    """Extract a plain-text body to inspect forwarded metadata."""
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
    """Try to recover the original sender from a forwarded email."""
    if not body_text:
        return ""

    patterns = [
        r"^From:\s.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
        r"^De:\s.*?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, body_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip().lower()
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
    Connect to Gmail through IMAP and fetch unread emails with PDF attachments.

    Returns a list of (metadata_dict, temporary_pdf_path).
    """
    if not smtp_user or not smtp_password:
        raise ValueError("Se requieren credenciales SMTP/IMAP para conectar a Gmail.")

    resultados: List[Tuple[dict, str]] = []
    since_dt = _imap_since_dt()
    since_label = since_dt.strftime("%d/%m/%Y")
    search_since = _format_imap_search_date(since_dt)

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)

        status, data = mail.search(None, "UNSEEN", "SINCE", search_since, "FROM", filter_from)

        if status != "OK" or not data[0]:
            logger.info(
                "IMAP: no hay emails nuevos del remitente '%s' desde %s",
                filter_from,
                since_label,
            )
            mail.logout()
            return []

        message_ids = data[0].split()
        logger.info(
            "IMAP: %s email(s) encontrados del remitente '%s' desde %s",
            len(message_ids),
            filter_from,
            since_label,
        )

        for msg_id in message_ids:
            status, msg_data = mail.fetch(msg_id, "(UID RFC822)")
            if status != "OK":
                continue
            uid_value = _extract_uid_from_fetch_data(msg_data) or msg_id.decode(errors="ignore").strip()

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = _decode_str(msg.get("Subject", ""))
            from_addr = _decode_str(msg.get("From", ""))
            date_str = msg.get("Date", "")
            if not _message_is_recent(date_str, since_dt):
                logger.info(
                    "IMAP: email omitido por antiguedad fuera de ventana (%s)",
                    subject or str(msg_id),
                )
                continue

            message_id = msg.get("Message-ID", str(msg_id))
            body_text = _extract_body_text(msg)
            forwarded_from = _extract_forwarded_from(body_text)

            metadata = {
                "subject": subject,
                "from_addr": from_addr,
                "date": date_str,
                "message_id": message_id,
                "imap_uid": uid_value,
                "imap_folder": imap_folder,
                "body_text": body_text,
                "forwarded_from": forwarded_from,
            }

            pdfs_encontrados = []
            attachment_index = 0
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition", ""))

                if content_type == "application/pdf" or (
                    "attachment" in disposition and part.get_filename("").lower().endswith(".pdf")
                ):
                    attachment_index += 1
                    filename = _decode_str(part.get_filename("adjunto.pdf"))
                    payload = part.get_payload(decode=True)
                    if payload:
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".pdf",
                            prefix="redsalud_",
                            delete=False,
                        )
                        tmp.write(payload)
                        tmp.close()
                        pdf_meta = {
                            **metadata,
                            "attachment_filename": filename,
                            "attachment_index": attachment_index,
                            "attachment_sha256": hashlib.sha256(payload).hexdigest(),
                            "attachment_size_bytes": len(payload),
                        }
                        pdfs_encontrados.append((pdf_meta, tmp.name))
                        logger.info("  PDF descargado: %s -> %s", filename, tmp.name)

            for pdf_meta, pdf_path in pdfs_encontrados:
                resultados.append((pdf_meta, pdf_path))

            if marcar_leidos and pdfs_encontrados:
                mail.store(msg_id, "+FLAGS", "\\Seen")

        mail.logout()

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado en IMAP: {e}")

    return resultados


def limpiar_temporales(pdf_paths: List[str]) -> None:
    """Delete temporary files created during attachment download."""
    for path in pdf_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


def recuperar_pdf_adjunto_imap(
    smtp_user: str,
    smtp_password: str,
    *,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    imap_uid: str = "",
    message_id: str = "",
    attachment_index: int = 1,
    attachment_filename: str = "",
    attachment_sha256: str = "",
) -> Tuple[bytes, str]:
    """
    Recupera un PDF desde IMAP usando la referencia guardada en BD.

    No escribe el adjunto en disco: devuelve bytes y nombre sugerido.
    """
    if not smtp_user or not smtp_password:
        raise ValueError("Se requieren credenciales SMTP/IMAP para conectar a Gmail.")
    if not imap_uid and not message_id:
        raise ValueError("No hay UID ni Message-ID para ubicar el correo original.")

    mail: Optional[imaplib.IMAP4_SSL] = None
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)

        raw_email = _fetch_raw_email_by_uid_or_message_id(mail, imap_uid, message_id)
        if not raw_email:
            raise FileNotFoundError("No se encontro el correo original en la carpeta configurada.")

        msg = email.message_from_bytes(raw_email)
        result = _find_pdf_attachment(
            msg,
            attachment_index=attachment_index,
            attachment_filename=attachment_filename,
            attachment_sha256=attachment_sha256,
        )
        if not result:
            raise FileNotFoundError("No se encontro el PDF adjunto dentro del correo original.")
        return result

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP: {e}")
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


def _fetch_raw_email_by_uid_or_message_id(
    mail: imaplib.IMAP4_SSL,
    imap_uid: str,
    message_id: str,
) -> bytes:
    uid = (imap_uid or "").strip()
    if uid:
        status, data = mail.uid("fetch", uid, "(RFC822)")
        raw = _raw_email_from_fetch_data(status, data)
        if raw:
            return raw

    msgid = (message_id or "").strip()
    if msgid:
        status, data = mail.search(None, "HEADER", "Message-ID", f'"{msgid}"')
        if status == "OK" and data and data[0]:
            for msg_num in data[0].split():
                status, msg_data = mail.fetch(msg_num, "(RFC822)")
                raw = _raw_email_from_fetch_data(status, msg_data)
                if raw:
                    return raw
    return b""


def _raw_email_from_fetch_data(status: str, data) -> bytes:
    if status != "OK":
        return b""
    for part in data or []:
        if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], bytes):
            return part[1]
    return b""


def _find_pdf_attachment(
    msg: Message,
    *,
    attachment_index: int,
    attachment_filename: str,
    attachment_sha256: str,
) -> Optional[Tuple[bytes, str]]:
    expected_index = max(int(attachment_index or 1), 1)
    expected_filename = (attachment_filename or "").strip().lower()
    expected_hash = (attachment_sha256 or "").strip().lower()

    fallback: Optional[Tuple[bytes, str]] = None
    current_index = 0
    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        filename = _decode_str(part.get_filename("adjunto.pdf"))
        is_pdf = content_type == "application/pdf" or (
            "attachment" in disposition.lower() and filename.lower().endswith(".pdf")
        )
        if not is_pdf:
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        current_index += 1
        candidate = (payload, filename or "orden_compra.pdf")
        if fallback is None:
            fallback = candidate

        if expected_hash and hashlib.sha256(payload).hexdigest().lower() != expected_hash:
            continue
        if expected_filename and filename.lower() != expected_filename:
            continue
        if current_index == expected_index or expected_hash or expected_filename:
            return candidate

    return fallback if expected_index == 1 and not expected_hash and not expected_filename else None


def _extract_artikos_codigo(subject: str, body: str) -> str:
    candidates = [subject or "", body or ""]
    patterns = (
        r"N(?:u|\u00fa)mero\s+de\s+OC\s*[:#]?\s*(\d{5,})",
        r"Folio\s+de\s+OC\s*[:#]?\s*(\d{5,})",
        r"Orden\s+de\s+Compra\s*\(?\s*(\d{5,})\s*\)?",
        r"\b(\d{5,})\b",
    )
    for text in candidates:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return ""


def _store_seen_flag(mail: imaplib.IMAP4_SSL, imap_uid: str) -> bool:
    if not imap_uid:
        return False
    try:
        status, _ = mail.uid("store", imap_uid, "+FLAGS", "(\\Seen)")
        return status == "OK"
    except Exception:
        logger.exception("IMAP Artikos: no se pudo marcar UID %s como leido", imap_uid)
        return False


def marcar_artikos_email_leido_gmail(
    smtp_user: str,
    smtp_password: str,
    *,
    imap_uid: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
) -> bool:
    """Marca como leido un email Artikos usando su UID IMAP."""
    if not smtp_user or not smtp_password or not imap_uid:
        return False

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)
        return _store_seen_flag(mail, str(imap_uid).strip())
    except imaplib.IMAP4.error as e:
        logger.warning("IMAP Artikos: no se pudo marcar email como leido: %s", e)
        return False
    except Exception:
        logger.exception("IMAP Artikos: error inesperado marcando email como leido")
        return False
    finally:
        if mail is not None:
            try:
                mail.logout()
            except Exception:
                pass


def _extract_uid_from_fetch_data(msg_data) -> str:
    for part in msg_data or []:
        if not isinstance(part, tuple) or not part:
            continue
        header = part[0]
        if isinstance(header, bytes):
            match = re.search(rb"UID\s+(\d+)", header)
            if match:
                return match.group(1).decode("ascii", errors="ignore")
    return ""


def buscar_artikos_emails_gmail(
    smtp_user: str,
    smtp_password: str,
    imap_server: str = "imap.gmail.com",
    imap_port: int = 993,
    imap_folder: str = "INBOX",
    marcar_leidos: bool = False,
) -> List[Tuple[dict, str]]:
    """
    Search recent Artikos emails and extract the OC URL from the body.

    Returns a list of (metadata_dict, artkios_url).
    """
    artkos_url_re = re.compile(
        r'https?://art-p-ptk\.artikos\.cl/[^\s\'"<>\r\n]+Key2=[^\s\'"<>\r\n]+',
        re.IGNORECASE,
    )

    if not smtp_user or not smtp_password:
        raise ValueError("Se requieren credenciales SMTP/IMAP para conectar a Gmail.")

    resultados: List[Tuple[dict, str]] = []
    since_dt = _imap_since_dt()
    since_label = since_dt.strftime("%d/%m/%Y")
    search_since = _format_imap_search_date(since_dt)

    try:
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(smtp_user, smtp_password)
        mail.select(imap_folder)

        status, data = mail.search(
            None,
            "SINCE",
            search_since,
            "SUBJECT",
            '"Nueva Orden de Compra"',
        )
        if status != "OK" or not data[0]:
            logger.info(
                "IMAP Artikos: no hay emails con asunto 'Nueva Orden de Compra' desde %s",
                since_label,
            )
            mail.logout()
            return []

        message_ids = data[0].split()
        logger.info(
            "IMAP Artikos: %s email(s) encontrados desde %s",
            len(message_ids),
            since_label,
        )

        for msg_id in message_ids:
            msg_id_value = msg_id.decode(errors="ignore").strip()
            status, msg_data = mail.fetch(msg_id, "(UID RFC822)")
            if status != "OK":
                continue
            uid_value = _extract_uid_from_fetch_data(msg_data) or msg_id_value

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = _decode_str(msg.get("Subject", ""))
            from_addr = _decode_str(msg.get("From", ""))
            date_str = msg.get("Date", "")
            if not _message_is_recent(date_str, since_dt):
                logger.info(
                    "IMAP Artikos: email omitido por antiguedad fuera de ventana (%s)",
                    subject or uid_value,
                )
                continue

            message_id = msg.get("Message-ID", uid_value)
            body_parts: list[str] = []

            url = None
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type not in ("text/plain", "text/html"):
                    continue
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
                body_parts.append(body)
                match = artkos_url_re.search(body)
                if match:
                    url = html_module.unescape(match.group(0).strip())

            if not url:
                logger.warning("IMAP Artikos: email sin URL reconocible (asunto: %r)", subject)
                continue

            body_text = "\n".join(part for part in body_parts if part)

            metadata = {
                "subject": subject,
                "from_addr": from_addr,
                "date": date_str,
                "message_id": message_id,
                "imap_uid": uid_value,
                "body_text": body_text,
                "codigo_oc_hint": _extract_artikos_codigo(subject, body_text),
            }
            resultados.append((metadata, url))

            if marcar_leidos:
                _store_seen_flag(mail, uid_value)

        mail.logout()

    except imaplib.IMAP4.error as e:
        raise ConnectionError(f"Error IMAP Artikos: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado en IMAP Artikos: {e}")

    return resultados
