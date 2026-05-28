from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.comercio import Comercio
from app.models.branding import ConfiguracionBranding
from app.models.usuario import Usuario
from app.schemas.branding import ConfiguracionBrandingResponse, ConfiguracionBrandingUpdate
from app.dependencies.auth import RoleChecker
from app.dependencies.tenant import get_current_tenant

router = APIRouter(prefix="/branding", tags=["Branding"])

@router.get("", response_model=ConfiguracionBrandingResponse)
async def get_branding_config(
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant)
):
    """
    Retorna la configuración visual y de branding del comercio resuelto (Acceso público).
    """
    result = await db.execute(select(ConfiguracionBranding).filter(ConfiguracionBranding.comercio_id == comercio.id))
    branding = result.scalars().first()
    if not branding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración de branding no encontrada para este comercio."
        )
    return branding

@router.put("", response_model=ConfiguracionBrandingResponse)
async def update_branding_config(
    branding_in: ConfiguracionBrandingUpdate,
    db: AsyncSession = Depends(get_db),
    comercio: Comercio = Depends(get_current_tenant),
    current_user: Usuario = Security(RoleChecker(["admin"]))
):
    """
    Actualiza la configuración de branding del comercio (Solo Admin de Comercio).
    """
    result = await db.execute(select(ConfiguracionBranding).filter(ConfiguracionBranding.comercio_id == comercio.id))
    branding = result.scalars().first()
    if not branding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración de branding no encontrada."
        )
    
    if branding_in.nombre_comercio is not None:
        branding.nombre_comercio = branding_in.nombre_comercio
    if branding_in.logo_url is not None:
        branding.logo_url = branding_in.logo_url
    if branding_in.branding_colors is not None:
        # Se guarda el modelo Pydantic serializado a dict
        branding.branding_colors = branding_in.branding_colors.model_dump()
    if branding_in.config_notificacion is not None:
        branding.config_notificacion = branding_in.config_notificacion
    if branding_in.tipo_publicidad is not None:
        branding.tipo_publicidad = branding_in.tipo_publicidad
    if branding_in.publicidad_banner_url is not None:
        branding.publicidad_banner_url = branding_in.publicidad_banner_url

    await db.commit()
    await db.refresh(branding)
    return branding

import io
import qrcode
from fastapi.responses import StreamingResponse

@router.get("/qr")
async def get_comercio_qr(
    comercio: Comercio = Depends(get_current_tenant),
    current_user: Usuario = Security(RoleChecker(["admin"]))
):
    """
    Genera dinámicamente un código QR (PNG) apuntando a la URL del cliente para el comercio actual.
    Restringido al Administrador de Comercio.
    """
    # Generar la URL basada en el slug del comercio
    public_url = f"https://tuplataforma.com/p/{comercio.slug}"
    
    # Crear código QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(public_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar en un buffer de bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")

