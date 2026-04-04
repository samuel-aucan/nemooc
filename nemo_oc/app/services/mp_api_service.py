"""
Servicio de consumo de la API publica de Mercado Publico / ChileCompra.
Implementa retry exponencial y filtro de OCs tipo CM.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

BASE_URL_PUBLICO = "https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json"
TIMEOUT = 30  # segundos


class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class MercadoPublicoAPI:

    def __init__(self, ticket: str, codigo_empresa: str = "227926"):
        self.ticket = ticket
        self.codigo_empresa = codigo_empresa
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Endpoints publicos
    # ------------------------------------------------------------------

    def probar_conexion(self) -> tuple[bool, str]:
        """
        Verifica que el ticket sea valido consultando el dia de hoy.
        Retorna (ok, mensaje_error).
        """
        hoy = datetime.now()
        try:
            data = self._get(BASE_URL_PUBLICO, {
                "ticket": self.ticket,
                "CodigoProveedor": self.codigo_empresa,
                "fecha": hoy.strftime("%d%m%Y"),
            })
            ok = "Listado" in data or "Cantidad" in data
            return ok, "" if ok else f"Respuesta inesperada: {list(data.keys())}"
        except APIError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error inesperado: {e}"

    def probar_conexion_rapida(self, timeout_segundos: int = 6) -> tuple[bool, str]:
        """
        Prueba corta para UI: responde rapido si la API esta viva, lenta o con ticket invalido.
        No usa los reintentos largos de la sincronizacion real.
        """
        hoy = datetime.now()
        params = {
            "ticket": self.ticket,
            "CodigoProveedor": self.codigo_empresa,
            "fecha": hoy.strftime("%d%m%Y"),
        }
        try:
            resp = self.session.get(BASE_URL_PUBLICO, params=params, timeout=timeout_segundos)
            if resp.status_code == 401:
                return False, "Ticket invalido o sin permisos."
            if resp.status_code >= 500:
                return False, f"API con error de servidor ({resp.status_code})."

            resp.raise_for_status()
            data = resp.json()
            if (
                isinstance(data, dict)
                and "Mensaje" in data
                and not any(k in data for k in ("Listado", "Cantidad"))
            ):
                codigo = data.get("Codigo", resp.status_code)
                mensaje = str(data.get("Mensaje", "Error API")).strip()
                if "ticket" in mensaje.lower():
                    return False, f"{mensaje} ({codigo})"
                return False, f"API respondio con error: {mensaje} ({codigo})"

            if "Listado" in data or "Cantidad" in data:
                return True, "API operativa."

            return False, "API respondio, pero con una estructura inesperada."
        except requests.exceptions.Timeout:
            return False, "API lenta o sin respuesta en prueba rapida."
        except requests.exceptions.ConnectionError:
            return False, "Sin conexion a internet o API no accesible."
        except Exception as e:
            return False, f"Error inesperado: {e}"

    def obtener_lista_oc(
        self,
        fecha_desde: datetime,
        fecha_hasta: datetime,
        solo_cm: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene OCs para cada dia en el rango de fechas.
        El endpoint acepta una sola fecha por llamada.
        Si solo_cm=True, filtra solo las de tipo CM.
        """
        todas: Dict[str, Dict[str, Any]] = {}
        dias_exitosos = 0
        errores_por_dia: list[str] = []

        delta = (fecha_hasta - fecha_desde).days + 1
        for i in range(delta):
            fecha_dia = fecha_desde + timedelta(days=i)
            fecha_str = fecha_dia.strftime("%d%m%Y")
            try:
                data = self._get(BASE_URL_PUBLICO, {
                    "ticket": self.ticket,
                    "CodigoProveedor": self.codigo_empresa,
                    "fecha": fecha_str,
                })
                listado_dia = data.get("Listado", []) or []
                dias_exitosos += 1

                if listado_dia and not todas:
                    primer = listado_dia[0]
                    logger.info(f"  Campos disponibles en lista: {list(primer.keys())}")
                    logger.info(
                        "  Primer item: "
                        f"Codigo={primer.get('Codigo', '?')} "
                        f"CodigoOC={primer.get('CodigoOC', '?')} "
                        f"NumeroOC={primer.get('NumeroOC', '?')}"
                    )

                for oc in listado_dia:
                    codigo = (
                        oc.get("Codigo")
                        or oc.get("CodigoOC")
                        or oc.get("NumeroOC")
                        or oc.get("numero")
                        or ""
                    )
                    codigo = str(codigo).strip()
                    if codigo and codigo not in todas:
                        todas[codigo] = oc

                logger.debug(f"  {fecha_dia.strftime('%d/%m/%Y')}: {len(listado_dia)} OCs")
            except APIError as e:
                logger.warning(f"  Error en fecha {fecha_str}: {e}")
                errores_por_dia.append(f"{fecha_dia.strftime('%d/%m/%Y')}: {e}")
                continue

        if dias_exitosos == 0 and errores_por_dia:
            detalle = " | ".join(errores_por_dia[:3])
            raise APIError(
                "No se pudo consultar Mercado Publico en el rango solicitado. "
                f"La API fallo en todas las fechas. Detalle: {detalle}"
            )

        resultado = list(todas.values())
        if solo_cm:
            resultado = [oc for oc in resultado if self._es_cm(oc)]

        tipo_label = "CM" if solo_cm else "todas"
        logger.info(
            f"API: {len(resultado)} OCs ({tipo_label}) entre "
            f"{fecha_desde.strftime('%d/%m/%Y')} y {fecha_hasta.strftime('%d/%m/%Y')}"
        )
        if errores_por_dia:
            logger.warning(
                "API: consulta parcial con errores en algunas fechas: "
                + " | ".join(errores_por_dia[:5])
            )
        return resultado

    def obtener_detalle_oc(self, numero_oc: str) -> Dict[str, Any]:
        """
        Obtiene el detalle completo de una OC por su codigo.
        """
        logger.info(f"    Detalle: {BASE_URL_PUBLICO}?codigo={numero_oc}&ticket=***")
        data = self._get(BASE_URL_PUBLICO, {
            "codigo": numero_oc,
            "ticket": self.ticket,
        })
        listado = data.get("Listado", []) or []
        if not listado:
            raise APIError(f"Sin detalle para OC {numero_oc}", 0)
        return listado[0]

    # ------------------------------------------------------------------
    # HTTP con retry
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict) -> Dict[str, Any]:
        delays = [2, 5, 10]
        last_exc = None
        for attempt in range(len(delays) + 1):
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
                logger.debug(f"  HTTP {resp.status_code} - {resp.url}")

                if resp.status_code == 401:
                    raise APIError("Ticket invalido o sin permisos (401).", 401)

                if resp.status_code == 429:
                    wait = delays[min(attempt, len(delays) - 1)] * 2
                    logger.warning(f"  Rate limit 429, esperando {wait}s...")
                    last_exc = APIError("Demasiadas solicitudes (429). Espere un momento.", 429)
                    if attempt < len(delays):
                        time.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    last_exc = APIError(f"Error del servidor ({resp.status_code}).", resp.status_code)
                    if attempt < len(delays):
                        wait = delays[attempt]
                        logger.warning(
                            f"  Error {resp.status_code}, reintentando en {wait}s... "
                            f"(intento {attempt + 1}/{len(delays) + 1})"
                        )
                        time.sleep(wait)
                    continue

                resp.raise_for_status()
                data = resp.json()
                if (
                    isinstance(data, dict)
                    and "Mensaje" in data
                    and not any(k in data for k in ("Listado", "Cantidad"))
                ):
                    codigo = data.get("Codigo", resp.status_code)
                    raise APIError(f"{data.get('Mensaje', 'Error API')} ({codigo})", resp.status_code)
                return data

            except APIError:
                raise
            except requests.exceptions.ConnectionError:
                last_exc = APIError("Sin conexion a internet.", 0)
            except requests.exceptions.Timeout:
                last_exc = APIError("Tiempo de espera agotado.", 0)
            except requests.exceptions.JSONDecodeError as e:
                raise APIError(f"Respuesta inesperada de API (no es JSON): {e}", 0)
            except Exception as e:
                raise APIError(f"Error inesperado: {e}", 0)

            if attempt < len(delays):
                logger.warning(f"  Intento {attempt + 1} fallido, reintentando en {delays[attempt]}s...")
                time.sleep(delays[attempt])

        raise last_exc or APIError("Error desconocido.", 0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _es_cm(oc: dict) -> bool:
        """
        Determina si una OC es de tipo Convenio Marco.
        """
        tipo = oc.get("Tipo", "").upper()
        codigo_tipo = str(oc.get("CodigoTipo", ""))
        codigo = oc.get("Codigo", "")

        return (
            tipo == "CM"
            or codigo_tipo == "9"
            or "-CM" in codigo.upper()
            or "/CM" in codigo.upper()
        )
