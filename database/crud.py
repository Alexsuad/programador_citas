# File: database/crud.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Consulta directa a la base de datos (DML/DQL).
# Rol: Intermediario entre modelos y lógica de negocio.
# ──────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from database.models import Negocio, Recurso, Servicio, Cita, HorarioRecurso, DiaNoDisponible, ExcepcionHorario
from datetime import date as d_date, datetime
from typing import List, Optional, Tuple

def obtener_buffer_time(db: Session, id_negocio: int) -> int:
    """Extrae el tiempo de limpieza configurado del negocio."""
    negocio = db.query(Negocio).filter(Negocio.id_negocio == id_negocio).first()
    if negocio and negocio.configuracion_json:
        return negocio.configuracion_json.get("buffer_time", 10)
    return 10

def verificar_dia_festivo(db: Session, id_negocio: int, fecha: d_date) -> bool:
    """Retorna True si la fecha es un día bloqueado o festivo."""
    festivo = db.query(DiaNoDisponible).filter(
        and_(DiaNoDisponible.id_negocio == id_negocio, DiaNoDisponible.fecha == fecha)
    ).first()
    return festivo is not None

def obtener_horario_recurso(db: Session, id_recurso: int, dia_semana: int) -> Optional[Tuple[str, str]]:
    """Retorna la ventana laboral (inicio, fin) del recurso para ese día."""
    horario = db.query(HorarioRecurso).filter(
        and_(HorarioRecurso.id_recurso == id_recurso, HorarioRecurso.dia_semana == dia_semana)
    ).first()
    if horario:
        return (horario.hora_inicio, horario.hora_fin)
    return None

def obtener_excepcion_recurso(db: Session, id_recurso: int, fecha: d_date) -> Optional[ExcepcionHorario]:
    """Busca si existe una excepción de horario para un recurso en una fecha."""
    return db.query(ExcepcionHorario).filter(
        and_(ExcepcionHorario.id_recurso == id_recurso, ExcepcionHorario.fecha == fecha)
    ).first()

def obtener_citas_dia(db: Session, id_recurso: int, fecha_busqueda: d_date) -> List[Cita]:
    """Retorna las citas confirmadas para un recurso en un día específico."""
    # Filtramos por fecha truncada y estado no cancelado
    return db.query(Cita).filter(
        and_(
            Cita.id_recurso == id_recurso,
            Cita.estado_cita == "confirmada",
            func.date(Cita.fecha_hora_inicio) == fecha_busqueda
        )
    ).all()

def cancelar_cita(db: Session, id_cita: int) -> bool:
    """Cambia el estado de una cita a cancelada."""
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if cita:
        cita.estado_cita = "cancelada"
        db.commit()
        return True
    return False
