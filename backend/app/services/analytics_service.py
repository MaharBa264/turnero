import uuid
from datetime import datetime, combine, min as time_min
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from app.models.turno import Turno

class AnalyticsService:
    async def get_average_service_time(self, comercio_id: uuid.UUID, db: AsyncSession) -> float:
        """
        Calcula el Tiempo Promedio de Atención (en segundos) de los últimos 5 llamados del día.
        Retorna 180 segundos (3 minutos) por defecto si no hay suficientes datos del día.
        """
        today = datetime.utcnow().date()
        start_of_day = combine(today, time_min)

        # Obtener los últimos 6 turnos llamados/atendidos hoy en orden cronológico de llamado
        # Necesitamos 6 turnos para poder calcular 5 deltas de tiempo consecutivos
        stmt = select(Turno).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.called_at.isnot(None),
                Turno.status.in_(["llamado", "atendido"])
            )
        ).order_by(Turno.called_at.asc())

        result = await db.execute(stmt)
        turnos = result.scalars().all()

        if len(turnos) < 2:
            return 180.0  # 3 minutos base por defecto

        # Calcular deltas de tiempo consecutivos entre llamados (en segundos)
        deltas = []
        for i in range(len(turnos) - 1):
            t1 = turnos[i].called_at
            t2 = turnos[i + 1].called_at
            if t1 and t2:
                delta = (t2 - t1).total_seconds()
                # Filtrar deltas atípicos negativos o extremadamente largos (> 1 hora)
                if 0 <= delta <= 3600:
                    deltas.append(delta)

        # Aplicar media móvil de los últimos 5 deltas disponibles
        recent_deltas = deltas[-5:]
        if not recent_deltas:
            return 180.0

        return sum(recent_deltas) / len(recent_deltas)

    async def get_estimated_wait_time(
        self, comercio_id: uuid.UUID, ticket_numero: int, db: AsyncSession
    ) -> dict:
        """
        Calcula la posición en la fila y el tiempo de espera estimado (en segundos)
        para un turno específico en base al número de personas adelante.
        """
        today = datetime.utcnow().date()
        start_of_day = combine(today, time_min)

        # Contar cuántos turnos activos de hoy están antes en la cola (status 'espera' y número menor)
        stmt_ahead = select(Turno).filter(
            and_(
                Turno.comercio_id == comercio_id,
                Turno.created_at >= start_of_day,
                Turno.status == "espera",
                Turno.numero < ticket_numero
            )
        )
        res_ahead = await db.execute(stmt_ahead)
        people_ahead = len(res_ahead.scalars().all())

        # Obtener la demora promedio por turno
        avg_service_time = await self.get_average_service_time(comercio_id, db)
        
        # Tiempo estimado en segundos
        estimated_seconds = people_ahead * avg_service_time

        return {
            "your_position": people_ahead,
            "estimated_wait_seconds": int(estimated_seconds),
            "average_service_time_seconds": int(avg_service_time)
        }

# Singleton instance
analytics_service = AnalyticsService()
