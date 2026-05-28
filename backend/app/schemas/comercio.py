import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re

class ComercioBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100, description="Slug URL del comercio (letras, números y guiones)")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not re.match(r"^[a-z0-9-]+$", value):
            raise ValueError("El slug sólo debe contener letras minúsculas, números y guiones medios")
        return value

class ComercioCreate(ComercioBase):
    pass

class ComercioUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=2, max_length=100)
    activo: bool | None = None

class ComercioResponse(ComercioBase):
    id: uuid.UUID
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True
