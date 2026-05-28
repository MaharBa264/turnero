# Documento de Entrega (Handoff) - Sistema de Turnos "Carnicería El Puntano"

Este documento resume la arquitectura actual del sistema de turnos web para **Carnicería El Puntano** (ubicada en San Luis, Argentina), las decisiones técnicas tomadas durante el desarrollo y los lineamientos para la futura implementación de la aplicación nativa Android.

---

## 1. Resumen del Proyecto

El sistema permite la gestión simplificada de turnos del día para una carnicería típica. Consiste en una aplicación web autohospedada que separa las interfaces por roles (clientes móviles, pantalla de TV en local y administración de carniceros).

### Características Clave:
- **Cliente Móvil:** Obtención de turnos de manera anónima (un solo clic) con almacenamiento local del ticket, estimación de tiempo de espera y simulación de alertas.
- **Pantalla Pública:** Interfaz optimizada para televisores, equipada con síntesis de voz (TTS) en español para llamar a los clientes en voz alta.
- **Consola del Carnicero:** Gestión de cola (siguiente, llamar de nuevo, reiniciar contador) y administración de personal para registrar/eliminar usuarios autorizados.

---

## 2. Decisiones de Código y Arquitectura

### A. Lenguaje del Servidor: Python Standard Library
- **Decisión:** Desarrollar el servidor backend usando el módulo integrado de Python `http.server` y `socketserver.ThreadingTCPServer`.
- **Razón:** El entorno de desarrollo no contaba con Node.js ni con gestores de paquetes como `pip`. Una implementación pura en Python nativo garantiza que el servidor corra instantáneamente en cualquier máquina con Python 3 instalado, sin dependencias externas ni compilaciones.

### B. Tiempo Real: Server-Sent Events (SSE)
- **Decisión:** Utilizar un flujo de eventos unidireccional vía HTTP (`text/event-stream`).
- **Razón:** SSE es más ligero que WebSockets, es nativo de la web y no requiere librerías complejas. Además, es muy fácil de escuchar desde una aplicación nativa de Android mediante librerías estándar como `OkHttp`.

### C. Almacenamiento: Base de Datos JSON Local
- **Decisión:** Los turnos, sesiones y usuarios se guardan en un archivo local `database.json`.
- **Razón:** Elimina la necesidad de instalar motores de base de datos relacionales o NoSQL. Al estar protegido con un `threading.Lock` en Python, previene condiciones de carrera durante la atención o solicitud de turnos de manera segura y concurrente.

### D. Seguridad de Accesos: Criptografía Nativa PBKDF2
- **Decisión:** Utilizar `hashlib.pbkdf2_hmac` con sal (salt) aleatoria de 16 bytes y 100.000 iteraciones para guardar contraseñas.
- **Razón:** Brinda un nivel de seguridad robusto alineado con estándares modernos, sin requerir la compilación binaria de bibliotecas como `bcrypt`.

---

## 3. Mapa del Proyecto

Los archivos se ubican en `/home/abraham/.gemini/antigravity/scratch/carniceria-turnos/`:

- **[server.py](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/server.py):** Archivo de servidor único (Rutas API, SSE, base de datos en memoria, persistencia en archivo y servidor de estáticos).
- **[database.json](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/database.json):** Almacenamiento generado automáticamente.
- **`public/`:** Directorio de recursos estáticos.
  - [index.html](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/index.html): Selector principal de rol.
  - [cliente.html](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/cliente.html) / [cliente.js](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/js/cliente.js): Interfaz de ticket de cliente.
  - [pantalla.html](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/pantalla.html) / [pantalla.js](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/js/pantalla.js): Interfaz de televisión para llamadas por voz.
  - [admin.html](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/admin.html) / [admin.js](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/js/admin.js): Consola de carnicero y gestión de usuarios.
  - [style.css](file:///home/abraham/.gemini/antigravity/scratch/carniceria-turnos/public/css/style.css): Hoja de estilos compartida.

---

## 4. Plan de Trabajo Pendiente / Siguientes Pasos

### Fase 1: Despliegue y Pruebas Físicas (Web)
- [ ] Configurar un túnel local o hosting básico (por ejemplo, Ngrok o una VPS simple) para que los clientes puedan escanear un código QR en la carnicería y acceder a la URL local del servidor.
- [ ] Imprimir un QR en la entrada que apunte directamente a `/cliente.html`.

### Fase 2: Desarrollo de la App Nativa Android
El backend ya está diseñado para que la transición a una app nativa Android sea directa:
- **Obtener Turno:** La app de Android realizará una llamada REST:
  `POST http://<server-ip>:8000/api/turns/take`
  Y guardará el ID y número del ticket retornado en los `SharedPreferences` de Android.
- **Sincronización:** Para rastrear la fila en segundo plano, la app de Android establecerá una conexión SSE usando OkHttp:
  ```kotlin
  val request = Request.Builder().url("http://<server-ip>:8000/api/turns/live").build()
  val sseListener = object : EventSourceListener() {
      override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
          // Parsear JSON del estado de la cola
      }
  }
  EventSources.createFactory(okHttpClient).newEventSource(request, sseListener)
  ```
- **Notificación en Segundo Plano (Background Services):** La app de Android utilizará un `Foreground Service` o `WorkManager` para mantener la conexión SSE abierta. Cuando el JSON de la cola indique que `ticket.number - data.current == 2`, la app disparará una notificación push local con `NotificationCompat.Builder` para alertar al usuario (ej: *"¡Tu turno está cerca! Faltan 2 personas"*), incluso si tiene el celular bloqueado o guardado en el bolsillo.
