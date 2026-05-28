import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Turno(Base):
    __tablename__ = "turnos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comercio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comercios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # status: espera | llamado | atendido | cancelado
    status: Mapped[str] = mapped_column(String(20), default="espera", nullable=False)
    
    # Timestamps (stored in UTC)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    called_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    called_by_username: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationship
    comercio: Mapped["Comercio"] = relationship("Comercio", back_populates="turnos")
