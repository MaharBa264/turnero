import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.comercio import Comercio
from app.models.branding import ConfiguracionBranding
from app.models.usuario import Usuario
from app.schemas.comercio import ComercioCreate, ComercioUpdate, ComercioResponse
from app.dependencies.auth import RoleChecker

router = APIRouter(prefix="/comercios", tags=["Comercios (Superadmin)"])

# Proteger todo el router para Superadmins
superadmin_checker = Security(RoleChecker(["superadmin"]))


@router.post("", response_model=ComercioResponse, status_code=status.HTTP_201_CREATED, dependencies=[superadmin_checker])
async def create_comercio(
    comercio_in: ComercioCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo comercio (Tenant) y su configuración de branding predeterminada.
    """
    # Verificar si ya existe un comercio con el mismo slug
    res_exist = await db.execute(select(Comercio).filter(Comercio.slug == comercio_in.slug))
    if res_exist.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un comercio con este slug."
        )

    nuevo_comercio = Comercio(
        nombre=comercio_in.nombre,
        slug=comercio_in.slug
    )
    db.add(nuevo_comercio)
    await db.flush() # Flush to get the ID

    # Crear configuración de branding por defecto
    branding_defecto = ConfiguracionBranding(
        comercio_id=nuevo_comercio.id,
        nombre_comercio=nuevo_comercio.nombre,
        branding_colors={
            "primary": "#c62828",
            "secondary": "#1565c0",
            "background": "#ffffff",
            "text": "#000000"
        },
        config_notificacion=2
    )
    db.add(branding_defecto)
    await db.commit()
    await db.refresh(nuevo_comercio)

    return nuevo_comercio

@router.get("", response_model=list[ComercioResponse], dependencies=[superadmin_checker])
async def list_comercios(db: AsyncSession = Depends(get_db)):
    """
    Lista todos los comercios registrados.
    """
    result = await db.execute(select(Comercio))
    return result.scalars().all()

@router.get("/{comercio_id}", response_model=ComercioResponse, dependencies=[superadmin_checker])
async def get_comercio(comercio_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Obtiene los detalles de un comercio por ID.
    """
    result = await db.execute(select(Comercio).filter(Comercio.id == comercio_id))
    comercio = result.scalars().first()
    if not comercio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comercio no encontrado.")
    return comercio

@router.put("/{comercio_id}", response_model=ComercioResponse, dependencies=[superadmin_checker])
async def update_comercio(
    comercio_id: uuid.UUID,
    comercio_in: ComercioUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza la información de un comercio.
    """
    result = await db.execute(select(Comercio).filter(Comercio.id == comercio_id))
    comercio = result.scalars().first()
    if not comercio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comercio no encontrado.")
    
    if comercio_in.nombre is not None:
        comercio.nombre = comercio_in.nombre
    if comercio_in.activo is not None:
        comercio.activo = comercio_in.activo
        
    await db.commit()
    await db.refresh(comercio)
    return comercio
