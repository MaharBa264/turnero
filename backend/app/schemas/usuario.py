import uuid
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator

VALID_ROLES = {"superadmin", "admin", "vendedor"}

class UsuarioBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    fullname: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="vendedor", description="Rol del usuario: superadmin | admin | vendedor")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        val_lower = value.lower()
        if val_lower not in VALID_ROLES:
            raise ValueError(f"El rol debe ser uno de los siguientes: {', '.join(VALID_ROLES)}")
        return val_lower

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=6, max_length=100, description="Contraseña en texto plano")
    comercio_id: uuid.UUID | None = Field(None, description="UUID del comercio (obligatorio excepto para superadmin)")

    @field_validator("comercio_id")
    @classmethod
    def validate_tenant_association(cls, value: uuid.UUID | None, info) -> uuid.UUID | None:
        role = info.data.get("role")
        if role != "superadmin" and value is None:
            raise ValueError("comercio_id es requerido para usuarios con rol diferente a 'superadmin'")
        return value

class UsuarioUpdate(BaseModel):
    fullname: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None
    role: str | None = None
    password: str | None = Field(None, min_length=6, max_length=100)
    activo: bool | None = None

    @field_validator("role")
    @classmethod
    def validate_role_update(cls, value: str | None) -> str | None:
        if value is not None:
            val_lower = value.lower()
            if val_lower not in VALID_ROLES:
                raise ValueError(f"El rol debe ser uno de los siguientes: {', '.join(VALID_ROLES)}")
            return val_lower
        return value

class UsuarioResponse(BaseModel):
    id: uuid.UUID
    comercio_id: uuid.UUID | None
    username: str
    email: EmailStr | None
    fullname: str
    role: str
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None
    comercio_id: uuid.UUID | None = None
