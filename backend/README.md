# Carnicería El Puntano - Backend SaaS Multi-Tenant

Este directorio contiene el backend asíncrono y multi-comercio para el sistema de turnos de **Carnicería El Puntano**, desarrollado utilizando Python, FastAPI, SQLAlchemy 2.0 y SQLite (a través de aiosqlite).

## Características Implementadas
- **Aislamiento Multi-Tenant:** Base de datos relacional compartida con aislamiento lógico mediante la columna `comercio_id` (Tenant ID).
- **Control de Acceso basado en Roles (RBAC):** Cuatro perfiles implementados: `superadmin` (global), `admin` (administrador del comercio), `vendedor` (consola de carnicero) y `cliente` (público anónimo).
- **Eventos en Tiempo Real (SSE):** Canales independientes Server-Sent Events por cada comercio para actualizar la pantalla pública y los clientes móviles instantáneamente sin mezclar datos.
- **Analítica de Tiempos:** Captura exacta de timestamps UTC para cálculo de demoras promedio.

---

## Estructura de Archivos del Proyecto

```
backend/
├── seed.py                  # Script para poblar la base de datos con datos de prueba
├── requirements.txt         # Dependencias del proyecto
├── app/
│   ├── main.py              # Punto de entrada de FastAPI y registro de routers
│   ├── config.py            # Configuración de entornos y variables con Pydantic Settings
│   ├── database.py          # Configuración y sesión asíncrona de SQLAlchemy
│   ├── dependencies/        # Inyección de dependencias (Auth JWT, resolución de Tenant)
│   │   ├── auth.py
│   │   └── tenant.py
│   ├── models/              # Modelos relacionales de base de datos
│   │   ├── comercio.py
│   │   ├── branding.py
│   │   ├── usuario.py
│   │   └── turno.py
│   ├── routers/             # Controladores y endpoints HTTP / SSE
│   │   ├── auth.py
│   │   ├── comercios.py
│   │   ├── branding.py
│   │   ├── usuarios.py
│   │   └── turnos.py
│   ├── schemas/             # Esquemas de validación Pydantic V2
│   │   ├── comercio.py
│   │   ├── branding.py
│   │   ├── usuario.py
│   │   └── turno.py
│   ├── services/            # Servicios de negocio (cola de turnos)
│   │   └── queue_service.py
│   └── security/            # Utilidades de hashing de contraseñas
│       └── hash.py
```

---

## Configuración y Ejecución del Entorno

### 1. Requisitos Previos
Asegúrate de contar con Python 3.10+ instalado en tu máquina.

### 2. Configuración del Entorno Virtual e Instalación
Crea un entorno virtual e instala las dependencias necesarias:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Linux/macOS)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configuración de Variables de Entorno
Crea un archivo `.env` en la raíz del directorio `backend/` para configurar la base de datos y la llave secreta para la firma de tokens JWT:

```env
PROJECT_NAME="SaaS Queue System"
API_V1_STR="/api"
SECRET_KEY="SUPER_SECRET_JWT_KEY_FOR_EL_PUNTANO_SAAS_12345"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL="sqlite+aiosqlite:///./database.db"
```

### 4. Población Inicial de la Base de Datos
Ejecuta el script de semilla `seed.py` para crear de forma automática las tablas de la base de datos y registrar las cuentas de prueba iniciales:

```bash
python seed.py
```

Este script registrará las siguientes credenciales en la base de datos local `database.db`:

| Rol | Username | Password | Comercio (Tenant) |
| :--- | :--- | :--- | :--- |
| **Superadmin** | `superadmin` | `superadmin123` | *N/A (Global)* |
| **Admin de Comercio** | `admin_puntano` | `admin123` | Carnicería El Puntano |
| **Vendedor** | `vendedor_puntano` | `vendedor123` | Carnicería El Puntano |
| **Cliente** | *Anónimo (Sin Login)* | *N/A* | Carnicería El Puntano |

### 5. Iniciar el Servidor de Desarrollo
Para arrancar el backend en modo de desarrollo con recarga automática, ejecuta:

```bash
uvicorn app.main:app --reload --port 8000
```

El servidor estará operativo en: `http://localhost:8000`

---

## Pruebas de Endpoints con Swagger UI

FastAPI genera automáticamente documentación interactiva. Una vez que el servidor esté corriendo, abre en tu navegador la URL:
👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Flujo de Pruebas Recomendado en Swagger:
1. **Autenticación:**
   - Despliega el endpoint `POST /api/auth/login`.
   - Utiliza el botón **Authorize** en la parte superior de la página de Swagger e introduce el `username` y `password` de cualquiera de los usuarios de prueba.
2. **Creación de Comercios (Superadmin):**
   - Autentícate como `superadmin`.
   - Llama a `POST /api/comercios` para dar de alta un nuevo comercio (ej: Carnicería San Luis).
3. **Personalización de Branding (Admin):**
   - Autentícate como `admin_puntano` pasándole el header `X-Tenant-Slug: el-puntano`.
   - Llama a `PUT /api/branding` para cambiar el logo, colores o número de turnos antes de disparar la alerta de notificación.
4. **Operación de la Cola:**
   - **Cliente:** Llama a `POST /api/turns/take` enviando el header `X-Tenant-Slug: el-puntano` para generar un ticket nuevo.
   - **Televisor / Cliente:** Conéctate a `GET /api/turns/live` para abrir la transmisión SSE de eventos en tiempo real.
   - **Vendedor:** Autentícate como `vendedor_puntano` con el header `X-Tenant-Slug: el-puntano` y llama a `POST /api/turns/next` para llamar al siguiente turno de la cola. Verás cómo la actualización se propaga de inmediato en la conexión de streaming SSE abierta.
