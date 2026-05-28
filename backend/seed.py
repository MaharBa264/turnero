import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import SessionLocal, engine, Base
from app.models.comercio import Comercio
from app.models.branding import ConfiguracionBranding
from app.models.usuario import Usuario
from app.security.hash import get_password_hash

async def seed_data():
    print("[Seed] Inicializando tablas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # 1. Crear Superadmin global
        stmt = select(Usuario).filter(Usuario.username == "superadmin")
        res = await db.execute(stmt)
        if not res.scalars().first():
            superadmin = Usuario(
                username="superadmin",
                email="superadmin@puntano.com",
                fullname="Super Administrador Global",
                role="superadmin",
                password_hash=get_password_hash("superadmin123"),
                activo=True
            )
            db.add(superadmin)
            print("[Seed] Creado usuario: superadmin / superadmin123")
        else:
            print("[Seed] El usuario superadmin ya existe.")

        # 2. Crear Comercio por defecto: "Carnicería El Puntano"
        stmt_comercio = select(Comercio).filter(Comercio.slug == "el-puntano")
        res_comercio = await db.execute(stmt_comercio)
        comercio = res_comercio.scalars().first()

        if not comercio:
            comercio = Comercio(
                id=uuid.UUID("d0d6bd90-2538-4b8e-871e-3913980e3452"), # Use a stable UUID
                nombre="Carnicería El Puntano",
                slug="el-puntano",
                activo=True
            )
            db.add(comercio)
            await db.flush() # flush to assign ID
            print("[Seed] Creado comercio: Carnicería El Puntano (slug: el-puntano)")

            # 3. Crear Branding para "Carnicería El Puntano"
            branding = ConfiguracionBranding(
                comercio_id=comercio.id,
                nombre_comercio="Carnicería El Puntano",
                logo_url=None,
                branding_colors={
                    "primary": "#c62828",
                    "secondary": "#1565c0",
                    "background": "#ffffff",
                    "text": "#000000"
                },
                config_notificacion=2
            )
            db.add(branding)
            print("[Seed] Creada configuración de branding predeterminada.")

            # 4. Crear Admin de Comercio
            admin_comercio = Usuario(
                comercio_id=comercio.id,
                username="admin_puntano",
                email="admin@elpuntano.com",
                fullname="Administrador El Puntano",
                role="admin",
                password_hash=get_password_hash("admin123"),
                activo=True
            )
            db.add(admin_comercio)
            print("[Seed] Creado usuario administrador de comercio: admin_puntano / admin123")

            # 5. Crear Vendedor de Comercio
            vendedor_comercio = Usuario(
                comercio_id=comercio.id,
                username="vendedor_puntano",
                email="vendedor@elpuntano.com",
                fullname="Vendedor El Puntano",
                role="vendedor",
                password_hash=get_password_hash("vendedor123"),
                activo=True
            )
            db.add(vendedor_comercio)
            print("[Seed] Creado usuario vendedor de comercio: vendedor_puntano / vendedor123")
        else:
            print("[Seed] El comercio el-puntano ya existe.")

        await db.commit()
        print("[Seed] Población de datos finalizada con éxito.")

if __name__ == "__main__":
    asyncio.run(seed_data())
