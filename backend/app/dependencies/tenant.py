import uuid
from fastapi import Depends, Header, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.comercio import Comercio
from app.models.usuario import Usuario
from app.dependencies.auth import get_current_user

async def get_current_tenant(
    x_tenant_slug: str | None = Header(None, alias="X-Tenant-Slug"),
    x_comercio_id: str | None = Header(None, alias="X-Comercio-ID"),
    slug: str | None = Query(None),
    comercio_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    # Optional authentication
    current_user: Usuario | None = Depends(get_current_user)
) -> Comercio:
    """
    Resuelve y retorna el Comercio (Tenant) activo de la petición.
    """
    resolved_id = None
    resolved_slug = None

    # 1. Si hay un usuario autenticado y no es superadmin, se asocia directamente a su comercio
    if current_user and current_user.role != "superadmin":
        resolved_id = current_user.comercio_id
    else:
        # 2. De lo contrario (cliente público o superadmin actuando sobre un tenant),
        #    se resuelve por headers o query parameters
        if x_comercio_id:
            resolved_id = x_comercio_id
        elif comercio_id:
            resolved_id = comercio_id
        elif x_tenant_slug:
            resolved_slug = x_tenant_slug
        elif slug:
            resolved_slug = slug

    if not resolved_id and not resolved_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de comercio (slug o ID) no proporcionado."
        )

    # Buscar en la base de datos
    comercio = None
    if resolved_id:
        try:
            comercio_uuid = uuid.UUID(str(resolved_id))
            result = await db.execute(select(Comercio).filter(Comercio.id == comercio_uuid))
            comercio = result.scalars().first()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de ID de comercio inválido."
            )
    elif resolved_slug:
        result = await db.execute(select(Comercio).filter(Comercio.slug == resolved_slug))
        comercio = result.scalars().first()

    if not comercio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El comercio especificado no existe."
        )

    if not comercio.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El comercio especificado se encuentra inactivo."
        )

    return comercio
