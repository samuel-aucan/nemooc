"""
Servicio de notificaciones email para NemoOC.
Envía emails a vendedores cuando llegan OCs nuevas.
Usa smtplib (built-in), sin dependencias adicionales.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import openpyxl

logger = logging.getLogger(__name__)

# Columnas de CORREOS.xlsx (índice 0-based)
COL_CARTERA = 0
COL_NOMBRE  = 1
COL_CORREO  = 2

_instance: Optional["EmailService"] = None


def get_email_service() -> "EmailService":
    global _instance
    if _instance is None:
        _instance = EmailService()
    return _instance


class EmailService:

    def __init__(self):
        # {CARTERA_UPPER: [{"nombre": str, "email": str}]}
        self._vendedores: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Carga del archivo CORREOS.xlsx
    # ------------------------------------------------------------------

    def cargar_correos(self, path: str | Path) -> tuple[bool, str]:
        """
        Lee CORREOS.xlsx (CARTERA | NOMBRE | CORREO) y construye el dict interno.
        Retorna (ok, mensaje) para feedback en la UI.
        """
        try:
            path = Path(path)
            if not path.exists():
                return False, f"Archivo no encontrado: {path}"

            wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
            ws = wb.active

            mapping: dict[str, list[dict]] = {}
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
                if not row or len(row) < 3:
                    continue
                cartera_raw = row[COL_CARTERA]
                nombre_raw  = row[COL_NOMBRE]
                correo_raw  = row[COL_CORREO]

                if not cartera_raw or not correo_raw:
                    continue

                cartera = str(cartera_raw).strip().upper()
                nombre  = str(nombre_raw).strip() if nombre_raw else ""
                correo  = str(correo_raw).strip()

                mapping.setdefault(cartera, []).append({
                    "nombre": nombre,
                    "email":  correo,
                })

            wb.close()
            self._vendedores = mapping
            total = sum(len(v) for v in mapping.values())
            return True, f"{total} correo(s) cargados para {len(mapping)} cartera(s)"

        except Exception as e:
            logger.error(f"Error cargando CORREOS.xlsx: {e}")
            return False, str(e)

    # ------------------------------------------------------------------
    # Notificación de OC nueva
    # ------------------------------------------------------------------

    def enviar_notificacion_oc(self, oc, cliente_info) -> bool:
        """
        Envía email a los vendedores de la cartera cuando llega una OC nueva.
        oc: OrdenCompra
        cliente_info: CarteraCliente
        Retorna True si al menos un email fue enviado.
        Nunca lanza excepción.
        """
        try:
            from app.config import load_config
            cfg = load_config()

            if not cfg.smtp_enabled:
                return False

            cartera = (cliente_info.cartera or "").strip().upper()
            destinatarios = self._vendedores.get(cartera, [])

            if not destinatarios:
                logger.info(
                    f"Sin destinatarios para cartera '{cartera}' "
                    f"(OC {oc.codigo_oc})"
                )
                return False

            asunto = (
                f"Nueva OC CM — {oc.codigo_oc} | "
                f"{oc.nombre_organismo or cliente_info.razon} | "
                f"${oc.total:,.0f}"
            )
            cuerpo = self._construir_cuerpo(oc, cliente_info)

            sent_any = False
            for dest in destinatarios:
                ok = self._enviar_smtp(
                    cfg=cfg,
                    to_email=dest["email"],
                    to_nombre=dest["nombre"],
                    asunto=asunto,
                    cuerpo=cuerpo,
                )
                if ok:
                    sent_any = True

            return sent_any

        except Exception as e:
            logger.warning(f"Error inesperado en enviar_notificacion_oc: {e}")
            return False

    def _construir_cuerpo(self, oc, cliente_info) -> str:
        portal_url = (
            "https://www.mercadopublico.cl/PurchaseOrder/Modules/PO/"
            f"DetailsPurchaseOrder.aspx?codigoOC={oc.codigo_oc}"
        )
        organismo = oc.nombre_organismo or cliente_info.razon or ""
        return (
            f"Se ha recibido una nueva Orden de Compra de Mercado Público.\n\n"
            f"DATOS DE LA OC\n"
            f"--------------\n"
            f"Código OC   : {oc.codigo_oc}\n"
            f"Organismo   : {organismo}\n"
            f"Cartera     : {cliente_info.cartera}\n"
            f"Región      : {cliente_info.region_nombre}\n"
            f"Monto Total : ${oc.total:,.0f}\n"
            f"Fecha envío : {oc.fecha_envio[:10] if oc.fecha_envio else '—'}\n\n"
            f"Ver en portal:\n{portal_url}\n\n"
            f"---\n"
            f"Este mensaje fue generado automáticamente por NemoOC.\n"
        )

    # ------------------------------------------------------------------
    # Envío SMTP
    # ------------------------------------------------------------------

    def _enviar_smtp(self, cfg, to_email: str, to_nombre: str,
                     asunto: str, cuerpo: str) -> bool:
        """
        Envía un correo vía STARTTLS (port 587).
        Retorna True/False, nunca lanza.
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = asunto
            msg["From"]    = cfg.smtp_user
            msg["To"]      = f"{to_nombre} <{to_email}>" if to_nombre else to_email
            msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(cfg.smtp_user, cfg.smtp_password)
                server.sendmail(cfg.smtp_user, [to_email], msg.as_string())

            logger.info(f"Email enviado a {to_email}: {asunto[:60]}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.warning(
                f"SMTP auth fallida para {cfg.smtp_user}. "
                "Verifique usuario/contraseña en Configuración."
            )
            return False
        except smtplib.SMTPException as e:
            logger.warning(f"SMTP error enviando a {to_email}: {e}")
            return False
        except OSError as e:
            logger.warning(f"Error de red SMTP ({cfg.smtp_host}:{cfg.smtp_port}): {e}")
            return False
        except Exception as e:
            logger.warning(f"Error inesperado en _enviar_smtp: {e}")
            return False

    def enviar_prueba(self, cfg, to_email: str = "") -> tuple[bool, str]:
        """Envía un email de prueba. Retorna (ok, mensaje)."""
        if not cfg.smtp_user:
            return False, "Configure el usuario/email primero."
        destino = to_email.strip() or cfg.smtp_user
        ok = self._enviar_smtp(
            cfg=cfg,
            to_email=destino,
            to_nombre="",
            asunto="NemoOC — Prueba de notificación",
            cuerpo=(
                "Este es un correo de prueba de NemoOC.\n"
                "Si lo recibe, la configuración SMTP es correcta.\n"
            ),
        )
        if ok:
            return True, f"Email de prueba enviado a {destino}"
        return False, "Envío fallido. Revise credenciales y conectividad."
