from fastapi import APIRouter, Depends, HTTPException, status, Security, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.comercio import Comercio
from app.models.usuario import Usuario
from app.dependencies.auth import get_current_user, RoleChecker
from app.dependencies.tenant import get_current_tenant
from app.schemas.turno import TurnoResponse
from app.services.queue_service import queue_service

router = APIRouter(prefix="/turns", tags=["Turnos"])

@router.post("/take", response_model=TurnoResponse, status_code=status.HTTP_201_CREATED)
async def take_turn(
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Genera un nuevo ticket para el comercio indicado (acceso anónimo).
    """
    nuevo_turno = await queue_service.create_ticket(comercio.id, db)
    return nuevo_turno

@router.post("/next", response_model=TurnoResponse)
async def call_next(
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant),
    current_user: Usuario = Security(RoleChecker(["admin", "vendedor"]))
):
    """
    Llama al siguiente turno de la fila (Vendedor o Admin de Comercio).
    """
    turno = await queue_service.call_next_ticket(comercio.id, current_user.username, db)
    if not turno:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay más clientes en espera para este comercio."
        )
    return turno

@router.get("/live")
async def live_turns_stream(
    ticket: int | None = Query(None, description="Número de ticket opcional para estimaciones personalizadas"),
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Establece una conexión Server-Sent Events (SSE) para recibir actualizaciones
    de la cola del comercio en tiempo real.
    """
    generator = queue_service.subscribe_client(comercio.id, db, ticket_numero=ticket)
    return StreamingResponse(generator, media_type="text/event-stream")
