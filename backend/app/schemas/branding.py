import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re

class BrandingColors(BaseModel):
    primary: str = Field(default="#c62828", description="Color primario en formato HEX")
    secondary: str = Field(default="#1565c0", description="Color secundario en formato HEX")
    background: str = Field(default="#ffffff", description="Color de fondo en formato HEX")
    text: str = Field(default="#000000", description="Color de texto en formato HEX")

    @field_validator("primary", "secondary", "background", "text")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", value):
            raise ValueError("El color debe estar en formato HEX válido (ej: #ffffff o #fff)")
        return value

class ConfiguracionBrandingBase(BaseModel):
    nombre_comercio: str = Field(..., min_length=2, max_length=100)
    logo_url: str | None = Field(None, max_length=255)
    branding_colors: BrandingColors = Field(default_factory=BrandingColors)
    config_notificacion: int = Field(default=2, ge=1, le=10, description="Turnos de anticipación para alertas")
    tipo_publicidad: str = Field(default="ninguna", description="Tipo de publicidad: google_ads | propia | ninguna")
    publicidad_banner_url: str | None = Field(None, max_length=255)

    @field_validator("tipo_publicidad")
    @classmethod
    def validate_tipo_publicidad(cls, value: str) -> str:
        val_lower = value.lower()
        valid_types = {"google_ads", "propia", "ninguna"}
        if val_lower not in valid_types:
            raise ValueError(f"tipo_publicidad debe ser uno de: {', '.join(valid_types)}")
        return val_lower

class ConfiguracionBrandingUpdate(BaseModel):
    nombre_comercio: str | None = Field(None, min_length=2, max_length=100)
    logo_url: str | None = Field(None, max_length=255)
    branding_colors: BrandingColors | None = None
    config_notificacion: int | None = Field(None, ge=1, le=10)
    tipo_publicidad: str | None = Field(None)
    publicidad_banner_url: str | None = Field(None, max_length=255)

    @field_validator("tipo_publicidad")
    @classmethod
    def validate_tipo_publicidad_update(cls, value: str | None) -> str | None:
        if value is not None:
            val_lower = value.lower()
            valid_types = {"google_ads", "propia", "ninguna"}
            if val_lower not in valid_types:
                raise ValueError(f"tipo_publicidad debe ser uno de: {', '.join(valid_types)}")
            return val_lower
        return value

class ConfiguracionBrandingResponse(ConfiguracionBrandingBase):
    id: uuid.UUID
    comercio_id: uuid.UUID
    updated_at: datetime

    class Config:
        from_attributes = True
