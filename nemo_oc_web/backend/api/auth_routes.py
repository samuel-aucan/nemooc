from fastapi import APIRouter, Depends, HTTPException, Request

from backend.core.auth import (
    complete_access_reset,
    count_users,
    create_user,
    get_current_user,
    get_user_by_username,
    initiate_access_reset,
    list_users,
    login_session,
    logout_session,
    require_admin,
    set_user_password,
    update_user,
    verify_password,
)
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


@router.get("/bootstrap-status", response_model=AuthBootstrapStatusOut)
def bootstrap_status():
    return AuthBootstrapStatusOut(requires_setup=count_users() == 0)


@router.post("/bootstrap", response_model=AuthUserOut)
def bootstrap(body: AuthBootstrapIn, request: Request):
    if count_users() > 0:
        raise HTTPException(409, detail="La aplicación ya tiene usuarios creados.")
    if body.password != body.password_confirm:
        raise HTTPException(400, detail="Las contraseñas no coinciden.")

    user = create_user(body.username, body.password, body.nombre_completo, "admin")
    session_user = login_session(request, user)
    return AuthUserOut(**session_user)


@router.post("/login", response_model=AuthUserOut)
def login(body: AuthLoginIn, request: Request):
    if count_users() == 0:
        raise HTTPException(400, detail="Primero debes crear el usuario administrador inicial.")

    user = get_user_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, detail="Usuario o contraseña incorrectos.")

    session_user = login_session(request, user)
    return AuthUserOut(**session_user)


@router.post("/complete-reset", response_model=AuthUserOut)
def complete_reset(body: AuthCompleteResetIn, request: Request):
    if body.password != body.password_confirm:
        raise HTTPException(400, detail="Las contraseñas no coinciden.")
    user = complete_access_reset(body.username, body.token, body.password)
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
