"""Servicios locales de administracion de usuarios para la desktop."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any

from app.db import get_connection

PBKDF2_ITERATIONS = 210_000
RESET_TOKEN_HOURS = 24


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise ValueError("El usuario debe tener al menos 3 caracteres.")
    return normalized


def _hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

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


def _serialize_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "nombre_completo": row.get("nombre_completo") or "",
        "rol": row.get("rol") or "operador",
        "activo": bool(row.get("activo", 1)),
        "last_login_at": row.get("last_login_at") or "",
        "must_reset_password": bool(row.get("must_reset_password", 0)),
    }


def count_users() -> int:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM usuarios").fetchone()
        return int(row["cnt"] or 0)
    finally:
        conn.close()


def bootstrap_required() -> bool:
    return count_users() == 0


def get_preview_autologin_user() -> dict[str, Any] | None:
    """Retorna un usuario activo para bypass temporal del login en la preview Qt."""
    users = [user for user in list_users() if user["activo"]]
    if not users:
        return None

    admins = [user for user in users if user["rol"] == "admin"]
    return admins[0] if admins else users[0]


def list_users() -> list[dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, last_login_at, must_reset_password
            FROM usuarios
            ORDER BY username COLLATE NOCASE ASC
            """
        ).fetchall()
        return [_serialize_user(dict(row)) for row in rows]
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, last_login_at,
                   must_reset_password, reset_token_hash, reset_token_expires_at, password_hash
            FROM usuarios
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data.update(_serialize_user(data))
        return data
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict[str, Any] | None:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT id, username, nombre_completo, rol, activo, last_login_at,
                   must_reset_password, reset_token_hash, reset_token_expires_at, password_hash
            FROM usuarios
            WHERE username = ?
            """,
            (_normalize_username(username),),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data.update(_serialize_user(data))
        return data
    finally:
        conn.close()


def _count_other_active_admins(exclude_user_id: int) -> int:
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM usuarios
            WHERE id != ? AND activo = 1 AND LOWER(rol) = 'admin'
            """,
            (exclude_user_id,),
        ).fetchone()
        return int(row["cnt"] or 0)
    finally:
        conn.close()


def create_user(username: str, password: str, password_confirm: str, nombre_completo: str = "", rol: str = "operador") -> dict[str, Any]:
    if password != password_confirm:
        raise ValueError("Las contraseñas no coinciden.")

    normalized = _normalize_username(username)
    role = rol.strip().lower()
    if role not in {"admin", "operador"}:
        raise ValueError("Rol inválido.")

    now = datetime.now().isoformat()
    password_hash = _hash_password(password)

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
        if "unique" in str(exc).lower():
            raise ValueError("Ese usuario ya existe.")
        raise
    finally:
        conn.close()

    user = get_user_by_username(normalized)
    if not user:
        raise RuntimeError("No se pudo crear el usuario.")
    return user


def update_user(user_id: int, nombre_completo: str, rol: str, activo: bool) -> dict[str, Any]:
    role = rol.strip().lower()
    if role not in {"admin", "operador"}:
        raise ValueError("Rol inválido.")

    current = get_user_by_id(user_id)
    if not current:
        raise ValueError("Usuario no encontrado.")

    if current["rol"] == "admin" and (not activo or role != "admin") and _count_other_active_admins(user_id) == 0:
        raise ValueError("No puedes dejar el sistema sin un administrador activo.")

    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE usuarios
            SET nombre_completo = ?, rol = ?, activo = ?, updated_at = ?
            WHERE id = ?
            """,
            (nombre_completo.strip(), role, 1 if activo else 0, now, user_id),
        )
        conn.commit()
    finally:
        conn.close()

    updated = get_user_by_id(user_id)
    if not updated:
        raise ValueError("Usuario no encontrado.")
    return updated


def set_user_password(user_id: int, password: str, password_confirm: str) -> dict[str, Any]:
    if password != password_confirm:
        raise ValueError("Las contraseñas no coinciden.")

    now = datetime.now().isoformat()
    password_hash = _hash_password(password)

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE usuarios
            SET password_hash = ?, must_reset_password = 0, reset_token_hash = NULL,
                reset_token_expires_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (password_hash, now, user_id),
        )
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")
    return user


def register_login(user_id: int) -> dict[str, Any]:
    now = datetime.now().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE usuarios
            SET last_login_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, user_id),
        )
        conn.commit()
    finally:
        conn.close()

    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")
    return user


def authenticate_user(username: str, password: str) -> dict[str, Any]:
    normalized = _normalize_username(username)
    user = get_user_by_username(normalized)
    if not user:
        raise ValueError("Usuario o contraseña incorrectos.")
    if not user["activo"]:
        raise ValueError("Este usuario está desactivado.")
    if user["must_reset_password"]:
        raise ValueError("Este usuario debe activar acceso antes de ingresar.")
    if not verify_password(password, user.get("password_hash") or ""):
        raise ValueError("Usuario o contraseña incorrectos.")
    return register_login(int(user["id"]))


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def initiate_access_reset(user_id: int) -> dict[str, str]:
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Usuario no encontrado.")
    if not user["activo"]:
        raise ValueError("No puedes reiniciar el acceso de un usuario desactivado.")

    raw_token = secrets.token_urlsafe(24)
    token_hash = _hash_reset_token(raw_token)
    expires_at = datetime.now() + timedelta(hours=RESET_TOKEN_HOURS)
    now = datetime.now().isoformat()

    conn = get_connection()
    try:
        conn.execute(
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
        conn.commit()
    finally:
        conn.close()

    return {
        "reset_token": raw_token,
        "expires_at": expires_at.isoformat(),
    }


def complete_access_reset(username: str, token: str, password: str, password_confirm: str) -> dict[str, Any]:
    if password != password_confirm:
        raise ValueError("Las contraseñas no coinciden.")

    user = get_user_by_username(username)
    if not user:
        raise ValueError("Usuario no encontrado.")
    if not user["activo"]:
        raise ValueError("Este usuario está desactivado.")
    if not user["must_reset_password"]:
        raise ValueError("Este usuario no tiene un reinicio de acceso pendiente.")

    expected_hash = user.get("reset_token_hash") or ""
    expires_raw = user.get("reset_token_expires_at") or ""
    if not expected_hash or not expires_raw:
        raise ValueError("No existe un token activo para este usuario.")

    try:
        expires_at = datetime.fromisoformat(expires_raw)
    except Exception as exc:
        raise ValueError("El token de acceso es inválido.") from exc

    if expires_at < datetime.now():
        raise ValueError("El token ya venció. Pide a un administrador reiniciar tu acceso nuevamente.")

    if not hmac.compare_digest(expected_hash, _hash_reset_token(token.strip())):
        raise ValueError("El token de acceso no es válido.")

    return set_user_password(int(user["id"]), password, password_confirm)
