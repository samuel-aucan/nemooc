import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, Request

from app.config import get_data_dir
from app.db import get_connection

SESSION_COOKIE_NAME = "nemooc_session"
SESSION_MAX_AGE = 60 * 60 * 12
PBKDF2_ITERATIONS = 210_000
RESET_TOKEN_HOURS = 24


def get_session_secret() -> str:
    env_secret = os.getenv("NEMOOC_SESSION_SECRET", "").strip()
    if env_secret:
        return env_secret

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
    }


def login_session(request: Request, user: dict[str, Any]) -> dict[str, Any]:
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
    request.session.clear()


def get_current_user(request: Request) -> dict[str, Any]:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, detail="No autenticado.")

    user = get_user_by_id(int(user_id))
    if not user or not user.get("activo", 1):
        request.session.clear()
        raise HTTPException(401, detail="Sesión inválida.")

    return serialize_user(user)


def require_auth(request: Request) -> dict[str, Any]:
    return get_current_user(request)


def require_admin(request: Request) -> dict[str, Any]:
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
