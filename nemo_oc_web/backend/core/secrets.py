"""
Manejo seguro de credenciales sensibles: enmascaramiento y validación.
No estamos encriptando en disco (requeriría claves KMS), pero ocultamos
al devolver a frontend y validamos acceso.
"""

def mask_sensitive_field(value: str, show_chars: int = 0) -> str:
    if not value:
        return ""
    if len(value) <= show_chars:
        return "*" * len(value)
    return "*" * (len(value) - show_chars) + value[-show_chars:] if show_chars > 0 else "*" * len(value)

def mask_password(password: str) -> str:
    return mask_sensitive_field(password, show_chars=0)

def mask_api_ticket(ticket: str) -> str:
    return mask_sensitive_field(ticket, show_chars=4)

def mask_smtp_password(password: str) -> str:
    return mask_sensitive_field(password, show_chars=0)
