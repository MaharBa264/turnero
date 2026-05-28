import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comercio_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comercios.id", ondelete="CASCADE"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    fullname: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # role: superadmin | admin | vendedor
    role: Mapped[str] = mapped_column(String(20), default="vendedor", nullable=False)
    
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    comercio: Mapped["Comercio | None"] = relationship("Comercio", back_populates="usuarios")
