import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, Request
from backend.core.paths import ensure_nemo_oc_in_path

ensure_nemo_oc_in_path()

from app.config import get_data_dir, load_config
from app.db import get_connection

SESSION_COOKIE_NAME = "nemooc_session"
SESSION_MAX_AGE = 60 * 60 * 12
PBKDF2_ITERATIONS = 210_000
RESET_TOKEN_HOURS = 24


def is_auth_disabled() -> bool:
    env_value = os.getenv("NEMOOC_DISABLE_AUTH", "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False

    try:
        return not load_config().auth_enabled
    except Exception:
        return True


def _local_user() -> dict[str, Any]:
    return {
        "id": 0,
        "username": "local",
        "nombre_completo": "Uso local",
        "rol": "admin",
        "activo": True,
        "last_login_at": "",
        "must_reset_password": False,
        "auth_disabled": True,
    }


def get_session_secret() -> str:
    env_secret = os.getenv("NEMOOC_SESSION_SECRET", "").strip()
    if env_secret:
        return env_secret

    # En producción, session_secret DEBE venir de .env
    if os.getenv("NEMOOC_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "CRÍTICO: NEMOOC_SESSION_SECRET no está configurado en .env. "
            "En producción, debe establecerse una clave aleatoria segura."
        )

    # En desarrollo, generar y cachear en disco
    secret_path = get_data_dir() / "session_secret.txt"
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()

    secret = secrets.token_urlsafe(48)
    secret_path.write_text(secret, encoding="utf-8")
    return secret


def should_secure_cookies() -> bool:
    raw = os.getenv("NEMOOC_SECURE_COOKIES", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise HTTPException(400, detail="La contraseña debe tener al menos 8 caracteres.")

    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_str, salt_b64, digest_b64 = password_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
    except Exception:
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise HTTPException(400, detail="El usuario debe tener al menos 3 caracteres.")
    return normalized


def count_users() -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM usuarios").fetchone()
        return int(row["cnt"] or 0)
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, password_hash, last_login_at,
                   must_reset_password, reset_token_hash, reset_token_expires_at
            FROM usuarios
            WHERE username = ?
            """,
            (normalize_username(username),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, password_hash, last_login_at,
                   must_reset_password, reset_token_hash, reset_token_expires_at
            FROM usuarios
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_user(username: str, password: str, nombre_completo: str = "", rol: str = "admin") -> dict[str, Any]:
    now = datetime.now().isoformat()
    normalized = normalize_username(username)
    password_hash = hash_password(password)
    role = rol.strip().lower()
    if role not in {"admin", "operador"}:
        raise HTTPException(400, detail="Rol inválido.")

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (normalized, password_hash, nombre_completo.strip(), role, now, now),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        message = str(exc).lower()
        if "unique" in message:
            raise HTTPException(409, detail="Ese usuario ya existe.")
        raise
    finally:
        conn.close()

    user = get_user_by_username(normalized)
    if not user:
        raise HTTPException(500, detail="No se pudo crear el usuario.")
    return user


def update_last_login(user_id: int) -> None:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE usuarios SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(user["id"]),
        "username": user["username"],
        "nombre_completo": user.get("nombre_completo") or "",
        "rol": user.get("rol") or "admin",
        "activo": bool(user.get("activo", 1)),
        "last_login_at": user.get("last_login_at") or "",
        "must_reset_password": bool(user.get("must_reset_password", 0)),
        "auth_disabled": False,
    }


def login_session(request: Request, user: dict[str, Any]) -> dict[str, Any]:
    if is_auth_disabled():
        return _local_user()
    if not user.get("activo", 1):
        raise HTTPException(403, detail="Este usuario está desactivado.")
    if user.get("must_reset_password", 0):
        raise HTTPException(403, detail="Este usuario debe activar nuevamente su acceso con un token temporal.")

    serialized = serialize_user(user)
    request.session.clear()
    request.session.update(
        {
            "user_id": serialized["id"],
            "username": serialized["username"],
            "rol": serialized["rol"],
        }
    )
    update_last_login(serialized["id"])
    serialized["last_login_at"] = datetime.now().isoformat()
    return serialized


def logout_session(request: Request) -> None:
    if is_auth_disabled():
        return
    request.session.clear()


def get_current_user(request: Request) -> dict[str, Any]:
    if is_auth_disabled():
        return _local_user()
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, detail="No autenticado.")

    user = get_user_by_id(int(user_id))
    if not user or not user.get("activo", 1):
        request.session.clear()
        raise HTTPException(401, detail="Sesión inválida.")

    return serialize_user(user)


def require_auth(request: Request) -> dict[str, Any]:
    if is_auth_disabled():
        return _local_user()
    return get_current_user(request)


def require_admin(request: Request) -> dict[str, Any]:
    if is_auth_disabled():
        return _local_user()
    user = get_current_user(request)
    if user.get("rol") != "admin":
        raise HTTPException(403, detail="Solo un administrador puede realizar esta acción.")
    return user


def list_users() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, last_login_at
            FROM usuarios
            ORDER BY username COLLATE NOCASE ASC
            """
        ).fetchall()
        return [serialize_user(dict(row)) for row in rows]
    finally:
        conn.close()


def update_user(user_id: int, nombre_completo: str, rol: str, activo: bool, actor_user_id: int) -> dict[str, Any]:
    role = rol.strip().lower()
    if role not in {"admin", "operador"}:
        raise HTTPException(400, detail="Rol inválido.")
    if user_id == actor_user_id and not activo:
        raise HTTPException(400, detail="No puedes desactivar tu propio usuario.")

    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE usuarios
            SET nombre_completo = ?, rol = ?, activo = ?, updated_at = ?
            WHERE id = ?
            """,
            (nombre_completo.strip(), role, 1 if activo else 0, now, user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, detail="Usuario no encontrado.")
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail="Usuario no encontrado.")
    return user


def set_user_password(user_id: int, password: str) -> dict[str, Any]:
    now = datetime.now().isoformat()
    password_hash = hash_password(password)

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE usuarios
            SET password_hash = ?, must_reset_password = 0, reset_token_hash = NULL,
                reset_token_expires_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (password_hash, now, user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, detail="Usuario no encontrado.")
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, detail="Usuario no encontrado.")
    return user


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def initiate_access_reset(user_id: int, actor_user_id: int) -> dict[str, str]:
    if user_id == actor_user_id:
        raise HTTPException(400, detail="No puedes reiniciar tu propio acceso desde aquí.")

    raw_token = secrets.token_urlsafe(24)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now() + timedelta(hours=RESET_TOKEN_HOURS)
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            UPDATE usuarios
            SET must_reset_password = 1,
                reset_token_hash = ?,
                reset_token_expires_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (token_hash, expires_at.isoformat(), now, user_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, detail="Usuario no encontrado.")
        conn.commit()
    finally:
        conn.close()

    return {
        "reset_token": raw_token,
        "expires_at": expires_at.isoformat(),
    }


def complete_access_reset(username: str, token: str, password: str) -> dict[str, Any]:
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(404, detail="Usuario no encontrado.")
    if not user.get("activo", 1):
        raise HTTPException(403, detail="Este usuario está desactivado.")
    if not user.get("must_reset_password", 0):
        raise HTTPException(400, detail="Este usuario no tiene un reinicio de acceso pendiente.")

    expected_hash = user.get("reset_token_hash") or ""
    expires_raw = user.get("reset_token_expires_at") or ""
    if not expected_hash or not expires_raw:
        raise HTTPException(400, detail="No existe un token activo para este usuario.")

    try:
        expires_at = datetime.fromisoformat(expires_raw)
    except Exception:
        raise HTTPException(400, detail="El token de acceso es inválido.")

    if expires_at < datetime.now():
        raise HTTPException(400, detail="El token ya venció. Pide a un administrador reiniciar tu acceso nuevamente.")

    if not hmac.compare_digest(expected_hash, _hash_reset_token(token.strip())):
        raise HTTPException(401, detail="El token de acceso no es válido.")

    return set_user_password(int(user["id"]), password)


# ── Supabase Auth Integration ───────────────────────────────────────────────

_sb_auth_logger = logging.getLogger("nemokey.supabase_auth")


def verify_supabase_credentials(email: str, password: str) -> Optional[dict[str, Any]]:
    """Verifica credenciales contra Supabase GoTrue. Retorna user data o None."""
    import requests

    supabase_url = os.environ.get("SUPABASE_URL", "")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    if not supabase_url or not anon_key:
        _sb_auth_logger.warning("SUPABASE_URL o SUPABASE_ANON_KEY no configurados")
        return None

    try:
        resp = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        user = data.get("user", {})
        return {
            "supabase_id": user.get("id"),
            "email": user.get("email"),
            "nombre_completo": (user.get("user_metadata") or {}).get("nombre_completo", ""),
        }
    except Exception as e:
        _sb_auth_logger.error(f"Error verificando Supabase: {e}")
        return None


def get_supabase_profile_rol(supabase_user_id: str) -> str:
    """Obtiene el rol del usuario desde la tabla profiles de Supabase."""
    from backend.supabase_oc_repository import _raw_sql

    try:
        rows = _raw_sql(
            "SELECT rol FROM profiles WHERE id = %s LIMIT 1",
            [supabase_user_id],
        )
        if rows:
            rol = rows[0].get("rol", "operador")
            return rol if rol in ("admin", "operador") else "operador"
        return "operador"
    except Exception as e:
        _sb_auth_logger.error(f"Error obteniendo rol Supabase: {e}")
        return "operador"


def sync_supabase_user_to_local(email: str, nombre_completo: str, rol: str) -> dict[str, Any]:
    """Crea o actualiza usuario local SQLite desde datos Supabase."""
    now = datetime.now().isoformat()
    normalized = email.strip().lower()
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM usuarios WHERE username = ?", (normalized,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE usuarios SET nombre_completo = ?, rol = ?, activo = 1, updated_at = ? WHERE username = ?",
                (nombre_completo, rol, now, normalized),
            )
            conn.commit()
        else:
            placeholder_hash = hash_password(secrets.token_urlsafe(32))
            conn.execute(
                "INSERT INTO usuarios (username, password_hash, nombre_completo, rol, activo, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
                (normalized, placeholder_hash, nombre_completo, rol, now, now),
            )
            conn.commit()
    finally:
        conn.close()

    user = get_user_by_username(normalized)
    if not user:
        raise HTTPException(500, detail="Error sincronizando usuario.")
    return user
