from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.comercio import Comercio
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.dependencies.auth import RoleChecker
from app.dependencies.tenant import get_current_tenant
from app.security.hash import get_password_hash

router = APIRouter(prefix="/usuarios", tags=["Usuarios (Admin de Comercio)"])

# Proteger el router para Administradores de Comercio
admin_checker = Security(RoleChecker(["admin"]))

@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED, dependencies=[admin_checker])
async def create_user(
    user_in: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Crea un nuevo usuario (vendedor u admin) dentro del comercio actual.
    """
    # Verificar si el usuario ya existe globalmente
    res_exist = await db.execute(select(Usuario).filter(Usuario.username == user_in.username))
    if res_exist.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )

    # El comercio_id se fuerza al del tenant resuelto para evitar inyecciones
    comercio_id_to_save = comercio.id
    if user_in.role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No se pueden crear usuarios superadmin a través de este endpoint."
        )

    nuevo_usuario = Usuario(
        comercio_id=comercio_id_to_save,
        username=user_in.username,
        email=user_in.email,
        fullname=user_in.fullname,
        role=user_in.role,
        password_hash=get_password_hash(user_in.password),
        activo=True
    )
    
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.get("", response_model=list[UsuarioResponse], dependencies=[admin_checker])
async def list_users(
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Lista todos los usuarios pertenecientes al comercio actual.
    """
    result = await db.execute(select(Usuario).filter(Usuario.comercio_id == comercio.id))
    return result.scalars().all()

@router.get("/{username}", response_model=UsuarioResponse, dependencies=[admin_checker])
async def get_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Obtiene los detalles de un usuario del comercio por su username.
    """
    result = await db.execute(
        select(Usuario).filter(
            Usuario.username == username,
            Usuario.comercio_id == comercio.id
        )
    )
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado en este comercio."
        )
    return usuario

@router.put("/{username}", response_model=UsuarioResponse, dependencies=[admin_checker])
async def update_user(
    username: str,
    user_in: UsuarioUpdate,
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Actualiza la información de un usuario del comercio.
    """
    result = await db.execute(
        select(Usuario).filter(
            Usuario.username == username,
            Usuario.comercio_id == comercio.id
        )
    )
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    if user_in.fullname is not None:
        usuario.fullname = user_in.fullname
    if user_in.email is not None:
        usuario.email = user_in.email
    if user_in.activo is not None:
        usuario.activo = user_in.activo
    if user_in.role is not None:
        if user_in.role == "superadmin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No es posible asignar el rol superadmin."
            )
        usuario.role = user_in.role
    if user_in.password is not None:
        usuario.password_hash = get_password_hash(user_in.password)

    await db.commit()
    await db.refresh(usuario)
    return usuario

@router.delete("/{username}", status_code=status.HTTP_200_OK, dependencies=[admin_checker])
async def delete_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Elimina un usuario del comercio.
    """
    result = await db.execute(
        select(Usuario).filter(
            Usuario.username == username,
            Usuario.comercio_id == comercio.id
        )
    )
    usuario = result.scalars().first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    await db.delete(usuario)
    await db.commit()
    return {"message": "Usuario eliminado correctamente"}
