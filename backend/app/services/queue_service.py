import asyncio
import json
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from app.models.turno import Turno
from app.services.analytics_service import analytics_service

class QueueService:
    def __init__(self):
        # Maps comercio_id (uuid.UUID) -> set of (asyncio.Queue, ticket_numero)
        self._subscribers: dict[uuid.UUID, set[tuple[asyncio.Queue, int | None]]] = {}
        self._lock = asyncio.Lock()

    async def get_current_state(self, comercio_id: uuid.UUID, db: AsyncSession) -> dict:
        """
        Obtiene el estado actual de la cola para un comercio:
        - current: número del último turno llamado hoy.
        - last_number: número del último turno emitido hoy.
        - total_waiting: cantidad de turnos actualmente en espera.
        - history: lista de los últimos 5 turnos llamados.
        """
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # 1. Obtener el máximo número emitido hoy
        stmt_last = select(func.max(Turno.numero)).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day
            )
        )
        res_last = await db.execute(stmt_last)
        last_number = res_last.scalar() or 0

        # 2. Obtener el último número llamado hoy (máximo número con status 'llamado', 'atendido' o 'cancelado')
        stmt_current = select(func.max(Turno.numero)).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.status.in_(["llamado", "atendido", "cancelado"])
            )
        )
        res_current = await db.execute(stmt_current)
        current = res_current.scalar() or 0

        # 3. Contar los turnos en espera
        stmt_waiting = select(func.count(Turno.id)).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.status == "espera"
            )
        )
        res_waiting = await db.execute(stmt_waiting)
        total_waiting = res_waiting.scalar() or 0

        # 4. Obtener el historial de los últimos 5 llamados de hoy
        stmt_history = select(Turno).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.status == "llamado"
            )
        ).order_by(Turno.called_at.desc()).limit(5)
        res_history = await db.execute(stmt_history)
        history_records = res_history.scalars().all()

        history = [
            {
                "number": t.numero,
                "called_at": t.called_at.isoformat() if t.called_at else None,
                "called_by": t.called_by_username
            }
            for t in history_records
        ]

        return {
            "current": current,
            "last_number": last_number,
            "total_waiting": total_waiting,
            "history": history
        }

    async def create_ticket(self, comercio_id: uuid.UUID, db: AsyncSession) -> Turno:
        """
        Crea un nuevo ticket/turno para el comercio asignándole el número consecutivo diario.
        Notifica a los suscriptores del comercio vía SSE.
        """
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # Obtener el último número asignado hoy para este comercio
        stmt = select(func.max(Turno.numero)).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day
            )
        )
        result = await db.execute(stmt)
        max_num = result.scalar() or 0
        new_number = max_num + 1

        # Crear nuevo turno
        nuevo_turno = Turno(
            comercio_id=comercio_id,
            numero=new_number,
            status="espera",
            created_at=datetime.utcnow()
        )
        db.add(nuevo_turno)
        await db.commit()
        await db.refresh(nuevo_turno)

        # Notificar a los clientes conectados de este comercio
        state = await self.get_current_state(comercio_id, db)
        await self._broadcast(comercio_id, {"type": "update", "data": state}, db)

        return nuevo_turno

    async def call_next_ticket(self, comercio_id: uuid.UUID, vendedor_username: str, db: AsyncSession) -> Turno | None:
        """
        Llama al siguiente turno en espera. Cambia su estado a 'llamado',
        asigna 'called_at' y 'called_by_username' y notifica vía SSE.
        """
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())

        # Buscar el turno en espera más antiguo de hoy
        stmt = select(Turno).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.status == "espera"
            )
        ).order_by(Turno.created_at.asc()).limit(1)
        
        result = await db.execute(stmt)
        turno = result.scalars().first()

        if not turno:
            return None

        # Actualizar datos de llamado
        turno.status = "llamado"
        turno.called_at = datetime.utcnow()
        turno.called_by_username = vendedor_username
        
        await db.commit()
        await db.refresh(turno)

        # Broadcast del estado de cola completo e indicación de nuevo llamado (para el TV)
        state = await self.get_current_state(comercio_id, db)
        new_call_info = {
            "number": turno.numero,
            "called_at": turno.called_at.isoformat(),
            "called_by": turno.called_by_username
        }
        
        await self._broadcast(comercio_id, {
            "type": "new_call",
            "data": state,
            "new_call": new_call_info
        }, db)

        return turno

    async def _broadcast(self, comercio_id: uuid.UUID, message: dict, db: AsyncSession):
        """
        Envía un mensaje a todas las colas de eventos activas de un comercio,
        personalizando la información predictiva de tiempos si el suscriptor tiene ticket.
        """
        async with self._lock:
            subscribers = self._subscribers.get(comercio_id, set()).copy()
            
        if not subscribers:
            return

        for q, ticket_numero in subscribers:
            try:
                # Personalizar payload si el suscriptor está asociado a un ticket específico
                custom_message = message.copy()
                if ticket_numero and "data" in custom_message:
                    custom_data = custom_message["data"].copy()
                    wait_data = await analytics_service.get_estimated_wait_time(comercio_id, ticket_numero, db)
                    custom_data.update({
                        "current_turn": custom_data["current"],
                        "your_position": wait_data["your_position"],
                        "estimated_wait_seconds": wait_data["estimated_wait_seconds"]
                    })
                    custom_message["data"] = custom_data

                msg_str = f"data: {json.dumps(custom_message)}\n\n"
                q.put_nowait(msg_str)
            except Exception:
                # Si falla, se removerá en la iteración del generador
                pass

    async def subscribe_client(self, comercio_id: uuid.UUID, db: AsyncSession, ticket_numero: int | None = None):
        """
        Generador asíncrono que suscribe al cliente para recibir eventos SSE.
        Envía el estado inicial inmediatamente con estimaciones personalizadas si corresponde.
        """
        q = asyncio.Queue()
        sub_pair = (q, ticket_numero)
        
        async with self._lock:
            if comercio_id not in self._subscribers:
                self._subscribers[comercio_id] = set()
            self._subscribers[comercio_id].add(sub_pair)

        try:
            # Enviar el estado inicial inmediatamente al conectarse
            initial_state = await self.get_current_state(comercio_id, db)
            
            # Si hay un número de ticket, incluir estimaciones personalizadas en el estado inicial
            if ticket_numero:
                wait_data = await analytics_service.get_estimated_wait_time(comercio_id, ticket_numero, db)
                initial_state.update({
                    "current_turn": initial_state["current"],
                    "your_position": wait_data["your_position"],
                    "estimated_wait_seconds": wait_data["estimated_wait_seconds"]
                })

            yield f"data: {json.dumps({'type': 'initial', 'data': initial_state})}\n\n"

            # Mantener la conexión escuchando actualizaciones de la cola
            while True:
                try:
                    # Esperar por mensajes del despachador con timeout para enviar keep-alive
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            async with self._lock:
                if comercio_id in self._subscribers:
                    self._subscribers[comercio_id].discard(sub_pair)
                    if not self._subscribers[comercio_id]:
                        del self._subscribers[comercio_id]

# Singleton instance
queue_service = QueueService()
