import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.core.auth import (
    complete_access_reset,
    count_users,
    create_user,
    get_current_user,
    get_user_by_username,
    is_auth_disabled,
    initiate_access_reset,
    list_users,
    _local_user,
    login_session,
    logout_session,
    require_admin,
    set_user_password,
    update_user,
    verify_password,
)

# Rate limiting: {username -> [timestamp, timestamp, ...]}
_login_attempts: dict[str, list[datetime]] = {}
from .schemas import (
    AuthBootstrapIn,
    AuthBootstrapStatusOut,
    AuthCompleteResetIn,
    AuthCreateUserIn,
    AuthLoginIn,
    AuthResetAccessOut,
    AuthResetPasswordIn,
    AuthUpdateUserIn,
    AuthUserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_LOGIN_ATTEMPTS = int(os.getenv("NEMOOC_LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_BLOCK_MINUTES = int(os.getenv("NEMOOC_LOGIN_BLOCK_MINUTES", "15"))

def _check_rate_limit(username: str) -> None:
    now = datetime.utcnow()
    if username not in _login_attempts:
        _login_attempts[username] = []

    attempts = _login_attempts[username]
    # Limpiar intentos más viejos que el bloqueo
    cutoff = now - timedelta(minutes=LOGIN_BLOCK_MINUTES)
    attempts[:] = [t for t in attempts if t > cutoff]

    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        oldest = attempts[0]
        unblock_time = oldest + timedelta(minutes=LOGIN_BLOCK_MINUTES)
        if now < unblock_time:
            wait_seconds = int((unblock_time - now).total_seconds())
            raise HTTPException(
                429,
                detail=f"Demasiados intentos fallidos. Intenta de nuevo en {wait_seconds} segundos.",
                headers={"Retry-After": str(wait_seconds)},
            )

def _record_failed_attempt(username: str) -> None:
    if username not in _login_attempts:
        _login_attempts[username] = []
    _login_attempts[username].append(datetime.utcnow())


@router.get("/bootstrap-status", response_model=AuthBootstrapStatusOut)
def bootstrap_status():
    if is_auth_disabled():
        return AuthBootstrapStatusOut(requires_setup=False, auth_disabled=True)
    return AuthBootstrapStatusOut(requires_setup=count_users() == 0, auth_disabled=False)


@router.post("/bootstrap", response_model=AuthUserOut)
def bootstrap(body: AuthBootstrapIn, request: Request):
    if is_auth_disabled():
        return AuthUserOut(**_local_user())
    if count_users() > 0:
        raise HTTPException(409, detail="La aplicación ya tiene usuarios creados.")

    _check_rate_limit(body.username)

    if body.password != body.password_confirm:
        _record_failed_attempt(body.username)
        raise HTTPException(400, detail="Las contraseñas no coinciden.")

    user = create_user(body.username, body.password, body.nombre_completo, "admin")
    _login_attempts.pop(body.username, None)
    session_user = login_session(request, user)
    return AuthUserOut(**session_user)


@router.post("/login", response_model=AuthUserOut)
def login(body: AuthLoginIn, request: Request):
    if is_auth_disabled():
        return AuthUserOut(**_local_user())
    if count_users() == 0:
        raise HTTPException(400, detail="Primero debes crear el usuario administrador inicial.")

    _check_rate_limit(body.username)

    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        _record_failed_attempt(body.username)
        raise HTTPException(401, detail="Usuario o contraseña incorrectos.")

    _login_attempts.pop(body.username, None)
    session_user = login_session(request, user)
    return AuthUserOut(**session_user)


@router.post("/complete-reset", response_model=AuthUserOut)
def complete_reset(body: AuthCompleteResetIn, request: Request):
    if is_auth_disabled():
        return AuthUserOut(**_local_user())

    _check_rate_limit(body.username)

    if body.password != body.password_confirm:
        _record_failed_attempt(body.username)
        raise HTTPException(400, detail="Las contraseñas no coinciden.")

    try:
        user = complete_access_reset(body.username, body.token, body.password)
        _login_attempts.pop(body.username, None)
    except HTTPException:
        _record_failed_attempt(body.username)
        raise

    session_user = login_session(request, user)
    return AuthUserOut(**session_user)


@router.post("/logout")
def logout(request: Request):
    logout_session(request)
    return {"ok": True}


@router.get("/me", response_model=AuthUserOut)
def me(request: Request):
    return AuthUserOut(**get_current_user(request))


@router.get("/users", response_model=list[AuthUserOut])
def get_users(_admin=Depends(require_admin)):
    return [AuthUserOut(**user) for user in list_users()]


@router.post("/users", response_model=AuthUserOut)
def create_user_route(body: AuthCreateUserIn, _admin=Depends(require_admin)):
    if body.password != body.password_confirm:
        raise HTTPException(400, detail="Las contraseñas no coinciden.")
    user = create_user(body.username, body.password, body.nombre_completo, body.rol)
    return AuthUserOut(**user)


@router.put("/users/{user_id}", response_model=AuthUserOut)
def update_user_route(user_id: int, body: AuthUpdateUserIn, admin=Depends(require_admin)):
    user = update_user(
        user_id=user_id,
        nombre_completo=body.nombre_completo,
        rol=body.rol,
        activo=body.activo,
        actor_user_id=admin["id"],
    )
    return AuthUserOut(**user)


@router.put("/users/{user_id}/password", response_model=AuthUserOut)
def reset_user_password(user_id: int, body: AuthResetPasswordIn, _admin=Depends(require_admin)):
    if body.password != body.password_confirm:
        raise HTTPException(400, detail="Las contraseñas no coinciden.")
    user = set_user_password(user_id, body.password)
    return AuthUserOut(**user)


@router.post("/users/{user_id}/reset-access", response_model=AuthResetAccessOut)
def restart_user_access(user_id: int, admin=Depends(require_admin)):
    token = initiate_access_reset(user_id, admin["id"])
    return AuthResetAccessOut(**token)
