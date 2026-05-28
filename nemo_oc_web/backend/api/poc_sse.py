"""
POC-C: Validar que SSE largo no se corta en Railway.
Endpoint temporal — eliminar antes del deploy final a produccion.
"""
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import asyncio
import time

router = APIRouter(prefix="/api/v1/poc", tags=["poc"])


@router.get("/sse-test")
async def sse_test():
    """
    Envia 30 eventos, 1 cada 10 segundos (5 minutos total).
    Si se corta antes del evento 30, SSE no es confiable en este entorno.
    """
    start = time.time()

    async def generate():
        for i in range(30):
            elapsed = int(time.time() - start)
            yield {
                "event": "progreso",
                "data": f"evento {i + 1}/30 — {elapsed}s transcurridos",
            }
            await asyncio.sleep(10)
        yield {"event": "fin", "data": "COMPLETADO — SSE funciona correctamente en este entorno"}

    return EventSourceResponse(
        generate(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sse-rapido")
async def sse_rapido():
    """
    Version rapida: 10 eventos cada 3 segundos (30 segundos total).
    Para verificar que SSE funciona antes de correr el test largo.
    """
    start = time.time()

    async def generate():
        for i in range(10):
            elapsed = int(time.time() - start)
            yield {
                "event": "progreso",
                "data": f"evento {i + 1}/10 — {elapsed}s",
            }
            await asyncio.sleep(3)
        yield {"event": "fin", "data": "COMPLETADO"}

    return EventSourceResponse(
        generate(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
