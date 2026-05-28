import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class TurnoBase(BaseModel):
    pass

class TurnoCreate(TurnoBase):
    pass

class TurnoResponse(BaseModel):
    id: uuid.UUID
    comercio_id: uuid.UUID
    numero: int
    status: str
    created_at: datetime
    called_at: datetime | None
    completed_at: datetime | None
    called_by_username: str | None

    class Config:
        from_attributes = True

class TurnoUpdate(BaseModel):
    status: str = Field(..., pattern="^(espera|llamado|atendido|cancelado)$")
    called_by_username: str | None = None
