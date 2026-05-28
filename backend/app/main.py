from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base
from app.routers import auth, comercios, branding, usuarios, turnos

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-seeding logic
async def seed_data_if_needed():
    from app.database import SessionLocal
    from app.models.usuario import Usuario
    from app.models.comercio import Comercio
    from app.models.branding import ConfiguracionBranding
    from app.security.hash import get_password_hash
    import uuid
    from sqlalchemy.future import select

    async with SessionLocal() as db:
        # Check if users already exist
        res = await db.execute(select(Usuario).limit(1))
        if res.scalars().first():
            print("[Startup] La base de datos ya está inicializada.")
            return

        print("[Startup] Base de datos vacía. Sembrando datos iniciales por defecto...")
        # 1. Crear Superadmin
        superadmin = Usuario(
            username="superadmin",
            email="superadmin@puntano.com",
            fullname="Super Administrador Global",
            role="superadmin",
            password_hash=get_password_hash("superadmin123"),
            activo=True
        )
        db.add(superadmin)

        # 2. Crear Comercio
        comercio = Comercio(
            id=uuid.UUID("d0d6bd90-2538-4b8e-871e-3913980e3452"),
            nombre="Carnicería El Puntano",
            slug="el-puntano",
            activo=True
        )
        db.add(comercio)
        await db.flush()

        # 3. Crear Branding
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

        await db.commit()
        print("[Startup] Datos de prueba sembrados con éxito.")

# Startup event to initialize DB tables
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        # Create all tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)
    # Run seed script if DB is uninitialized
    await seed_data_if_needed()

# Register routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(comercios.router, prefix=settings.API_V1_STR)
app.include_router(branding.router, prefix=settings.API_V1_STR)
app.include_router(usuarios.router, prefix=settings.API_V1_STR)
app.include_router(turnos.router, prefix=settings.API_V1_STR)

# Find public directory (support local running and container execution contexts)
public_path = "public"
if not os.path.exists(public_path):
    public_path = "../public"

if os.path.exists(public_path):
    print(f"[Startup] Servidor de estáticos sirviendo desde: {public_path}")
    app.mount("/", StaticFiles(directory=public_path, html=True), name="public")
else:
    print(f"[Warning] No se encontró el directorio de estáticos en: {public_path}")
