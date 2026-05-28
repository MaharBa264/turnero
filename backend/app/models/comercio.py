import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Comercio(Base):
    __tablename__ = "comercios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    branding: Mapped["ConfiguracionBranding"] = relationship(
        "ConfiguracionBranding", back_populates="comercio", cascade="all, delete-orphan", uselist=False
    )
    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario", back_populates="comercio", cascade="all, delete-orphan"
    )
    turnos: Mapped[list["Turno"]] = relationship(
        "Turno", back_populates="comercio", cascade="all, delete-orphan"
    )
