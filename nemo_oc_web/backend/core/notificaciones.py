"""
Notificaciones de OC: campanita (oc_notificaciones) + Web Push.
Escribe a Supabase via Management API (raw SQL), igual que supabase_write_service.
Errores silenciosos para no interrumpir el flujo de sync.
"""
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

FRONTEND_URL = os.environ.get("FRONTEND_VENDEDORES_URL", "https://nemo-vendedores.vercel.app")


def _raw_sql(sql: str, params: list | None = None) -> list[dict]:
    import requests

    pat = os.environ.get("SUPABASE_PAT", "")
    project = os.environ.get("SUPABASE_PROJECT", "")
    if not pat or not project:
        raise RuntimeError("SUPABASE_PAT y SUPABASE_PROJECT requeridos")

    url = f"https://api.supabase.com/v1/projects/{project}/database/query"
    headers = {"Authorization": f"Bearer {pat}", "Content-Type": "application/json"}

    if params:
        for p in params:
            if p is None:
                replacement = "NULL"
            elif isinstance(p, str):
                safe = p.replace("'", "''")
                replacement = f"'{safe}'"
            elif isinstance(p, bool):
                replacement = "TRUE" if p else "FALSE"
            else:
                replacement = str(p)
            sql = sql.replace("%s", replacement, 1)

    r = requests.post(url, headers=headers, json={"query": sql}, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"SQL raw error {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data if isinstance(data, list) else []


def _vendedor_de_cartera(cartera_id: str) -> Optional[str]:
    try:
        rows = _raw_sql("SELECT vendedor_id FROM carteras WHERE id = %s LIMIT 1", [cartera_id])
        return rows[0].get("vendedor_id") if rows else None
    except Exception:
        return None


def _admins() -> list[str]:
    try:
        rows = _raw_sql("SELECT id FROM profiles WHERE rol = 'admin' AND activo = TRUE")
        return [r["id"] for r in rows]
    except Exception:
        return []


def _ya_notificado(oc_id: str, usuario_id: str, tipo: str) -> bool:
    try:
        rows = _raw_sql(
            "SELECT 1 FROM oc_notificaciones WHERE oc_id = %s AND usuario_id = %s AND tipo = %s LIMIT 1",
            [oc_id, usuario_id, tipo],
        )
        return bool(rows)
    except Exception:
        return False


def _crear_notificacion(oc_id: str, usuario_id: str, titulo: str, mensaje: str, tipo: str) -> None:
    _raw_sql(
        "INSERT INTO oc_notificaciones (oc_id, usuario_id, titulo, mensaje, tipo, leida) "
        "VALUES (%s, %s, %s, %s, %s, FALSE)",
        [oc_id, usuario_id, titulo, mensaje, tipo],
    )


def _enviar_push(usuario_id: str, titulo: str, mensaje: str, url: str) -> None:
    """Envía Web Push a todas las suscripciones del usuario."""
    public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
    subject = os.environ.get("VAPID_SUBJECT", "mailto:ordenesdecompra@nemochile.cl")
    if not public_key or not private_key:
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("[notif] pywebpush no instalado")
        return

    try:
        subs = _raw_sql(
            "SELECT endpoint, subscription FROM push_subscriptions WHERE usuario_id = %s",
            [usuario_id],
        )
    except Exception:
        return

    payload = json.dumps({"titulo": titulo, "mensaje": mensaje, "url": url})

    for sub in subs:
        sub_info = sub.get("subscription")
        if isinstance(sub_info, str):
            try:
                sub_info = json.loads(sub_info)
            except Exception:
                continue
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
            )
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                try:
                    _raw_sql("DELETE FROM push_subscriptions WHERE endpoint = %s", [sub["endpoint"]])
                except Exception:
                    pass
            else:
                logger.debug(f"[notif] push error: {e}")
        except Exception as e:
            logger.debug(f"[notif] push error: {e}")


def notificar(oc_id: str, usuario_id: str, titulo: str, mensaje: str, tipo: str, dedup: bool = True) -> None:
    """Crea notificación in-app + push. Si dedup, evita repetir misma OC+usuario+tipo."""
    try:
        if dedup and _ya_notificado(oc_id, usuario_id, tipo):
            return
        _crear_notificacion(oc_id, usuario_id, titulo, mensaje, tipo)
        _enviar_push(usuario_id, titulo, mensaje, f"{FRONTEND_URL}/oc")
    except Exception as e:
        logger.warning(f"[notif] error notificando {tipo} oc={oc_id}: {e}")


def notificar_oc_nueva(oc_id: str, codigo_oc: str, cartera_id: Optional[str]) -> None:
    """Notifica al vendedor de la cartera que llegó una OC nueva."""
    if not cartera_id:
        return
    vendedor_id = _vendedor_de_cartera(cartera_id)
    if not vendedor_id:
        return
    notificar(
        oc_id, vendedor_id,
        "Nueva OC en tu cartera",
        f"Llegó la orden de compra {codigo_oc}",
        "nueva_oc",
        dedup=True,
    )


def revisar_ocs_pendientes() -> dict:
    """Chequeo periódico: OC sin ingresar (12h → vendedor) y sin atender (3d → admin)."""
    resultado = {"sin_ingresar": 0, "sin_atender": 0}

    # A) Sin ingresar 12h → vendedor
    try:
        rows = _raw_sql(
            "SELECT c.id, c.codigo_oc, c.cartera_id "
            "FROM oc_cabecera c "
            "WHERE c.estado_interno NOT IN ('Ingresada','Rechazada','Anulada') "
            "AND c.cartera_id IS NOT NULL "
            "AND c.created_at < NOW() - INTERVAL '12 hours'"
        )
        for oc in rows:
            vendedor_id = _vendedor_de_cartera(oc["cartera_id"])
            if not vendedor_id:
                continue
            if _ya_notificado(oc["id"], vendedor_id, "oc_sin_ingresar"):
                continue
            notificar(
                oc["id"], vendedor_id,
                "OC pendiente de ingresar",
                f"La OC {oc['codigo_oc']} lleva más de 12 horas sin ingresarse",
                "oc_sin_ingresar",
                dedup=False,
            )
            resultado["sin_ingresar"] += 1
    except Exception as e:
        logger.warning(f"[notif] revisar sin_ingresar: {e}")

    # B) Sin atender 3 días → admins
    try:
        rows = _raw_sql(
            "SELECT id, codigo_oc FROM oc_cabecera "
            "WHERE estado_interno = 'Nueva' "
            "AND created_at < NOW() - INTERVAL '3 days'"
        )
        admins = _admins()
        for oc in rows:
            for admin_id in admins:
                if _ya_notificado(oc["id"], admin_id, "oc_sin_atender"):
                    continue
                notificar(
                    oc["id"], admin_id,
                    "OC sin atender hace 3 días",
                    f"La OC {oc['codigo_oc']} sigue en estado Nueva",
                    "oc_sin_atender",
                    dedup=False,
                )
                resultado["sin_atender"] += 1
    except Exception as e:
        logger.warning(f"[notif] revisar sin_atender: {e}")

    return resultado
