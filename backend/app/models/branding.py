import uuid
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class ConfiguracionBranding(Base):
    __tablename__ = "configuraciones_branding"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comercio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comercios.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    nombre_comercio: Mapped[str] = mapped_column(String(100), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Store branding colors as JSON (primary, secondary, background)
    branding_colors: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Configuración de cantidad de turnos antes para enviar alerta
    config_notificacion: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    
    # Publicidad y monetización
    tipo_publicidad: Mapped[str] = mapped_column(String(20), default="ninguna", nullable=False)
    publicidad_banner_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationship
    comercio: Mapped["Comercio"] = relationship("Comercio", back_populates="branding")
