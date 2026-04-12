# File: database/crud.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Consulta directa a la base de datos (DML/DQL).
# Rol: Intermediario entre modelos y lógica de negocio.
# ──────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_, func, or_, desc
from database.models import Negocio, Recurso, Servicio, RecursoServicio, Cita, HorarioRecurso, DiaNoDisponible, ExcepcionHorario
from datetime import date as d_date, datetime, timedelta
from typing import List, Optional, Tuple

def obtener_buffer_time(db: Session, id_negocio: int) -> int:
    """Retorna el buffer_time (minutos) del negocio desde configuracion_json."""
    negocio = db.query(Negocio).filter(Negocio.id_negocio == id_negocio).first()
    if negocio and negocio.configuracion_json:
        return negocio.configuracion_json.get("buffer_time", 0)
    return 0

def obtener_mensaje_bienvenida(db: Session, id_negocio: int) -> str:
    """
    Retorna el mensaje de bienvenida configurado para el negocio.
    Si no existe, devuelve un texto por defecto.
    """
    negocio = db.query(Negocio).filter(Negocio.id_negocio == id_negocio).first()

    if negocio and negocio.configuracion_json:
        mensaje = negocio.configuracion_json.get("mensaje_bienvenida")
        if mensaje:
            return mensaje

    return (
        "👋 ¡Bienvenido! Estás en el sistema inteligente de agendamiento.\n\n"
        "Aquí puedes reservar tu cita de forma rápida y sencilla."
    )

def guardar_mensaje_bienvenida(db: Session, id_negocio: int, mensaje: str) -> bool:
    """
    Guarda o actualiza el mensaje de bienvenida del negocio.
    """
    negocio = db.query(Negocio).filter(Negocio.id_negocio == id_negocio).first()

    if not negocio:
        return False

    configuracion_actual = negocio.configuracion_json or {}
    configuracion_actual["mensaje_bienvenida"] = mensaje.strip()
    negocio.configuracion_json = configuracion_actual
    flag_modified(negocio, "configuracion_json")

    db.commit()
    return True

def obtener_recurso_por_id(db: Session, id_recurso: int) -> Optional[Recurso]:
    return db.get(Recurso, id_recurso)

def obtener_recursos_del_negocio(db: Session, id_negocio: int) -> List[Recurso]:
    """
    Retorna los recursos del negocio ordenados por nombre.
    """
    return db.query(Recurso).filter(
        Recurso.id_negocio == id_negocio
    ).order_by(Recurso.nombre_recurso.asc()).all()

def obtener_servicios_habilitados_de_recurso(
    db: Session,
    id_negocio: int,
    id_recurso: int
) -> List[Servicio]:
    """
    Retorna los servicios habilitados para un recurso específico.
    """
    return db.query(Servicio).join(
        RecursoServicio,
        Servicio.id_servicio == RecursoServicio.id_servicio
    ).join(
        Recurso,
        Recurso.id_recurso == RecursoServicio.id_recurso
    ).filter(
        and_(
            Recurso.id_negocio == id_negocio,
            Recurso.id_recurso == id_recurso,
            Servicio.id_negocio == id_negocio
        )
    ).order_by(Servicio.nombre_servicio.asc()).all()

def obtener_servicios_no_habilitados_de_recurso(
    db: Session,
    id_negocio: int,
    id_recurso: int
) -> List[Servicio]:
    """
    Retorna los servicios del negocio que todavía NO están habilitados
    para el recurso indicado.
    """
    subquery_servicios_habilitados = db.query(
        RecursoServicio.id_servicio
    ).filter(
        RecursoServicio.id_recurso == id_recurso
    )

    return db.query(Servicio).filter(
        and_(
            Servicio.id_negocio == id_negocio,
            ~Servicio.id_servicio.in_(subquery_servicios_habilitados)
        )
    ).order_by(Servicio.nombre_servicio.asc()).all()

def agregar_habilidad_a_recurso(
    db: Session,
    id_negocio: int,
    id_recurso: int,
    id_servicio: int
) -> bool:
    """
    Agrega una relación recurso-servicio si no existe ya
    y si ambos pertenecen al mismo negocio.
    """
    recurso = db.query(Recurso).filter(
        and_(
            Recurso.id_recurso == id_recurso,
            Recurso.id_negocio == id_negocio
        )
    ).first()

    servicio = db.query(Servicio).filter(
        and_(
            Servicio.id_servicio == id_servicio,
            Servicio.id_negocio == id_negocio
        )
    ).first()

    if not recurso or not servicio:
        return False

    existente = db.query(RecursoServicio).filter(
        and_(
            RecursoServicio.id_recurso == id_recurso,
            RecursoServicio.id_servicio == id_servicio
        )
    ).first()

    if existente:
        return True

    nueva_relacion = RecursoServicio(
        id_recurso=id_recurso,
        id_servicio=id_servicio
    )
    db.add(nueva_relacion)
    db.commit()
    return True

def quitar_habilidad_a_recurso(
    db: Session,
    id_negocio: int,
    id_recurso: int,
    id_servicio: int
) -> bool:
    """
    Elimina una relación recurso-servicio si existe
    y si ambos pertenecen al mismo negocio.
    """
    recurso = db.query(Recurso).filter(
        and_(
            Recurso.id_recurso == id_recurso,
            Recurso.id_negocio == id_negocio
        )
    ).first()

    servicio = db.query(Servicio).filter(
        and_(
            Servicio.id_servicio == id_servicio,
            Servicio.id_negocio == id_negocio
        )
    ).first()

    if not recurso or not servicio:
        return False

    relacion = db.query(RecursoServicio).filter(
        and_(
            RecursoServicio.id_recurso == id_recurso,
            RecursoServicio.id_servicio == id_servicio
        )
    ).first()

    if not relacion:
        return True

    db.delete(relacion)
    db.commit()
    return True

def obtener_recursos_habilitados_para_servicio(
    db: Session,
    id_negocio: int,
    id_servicio: int,
    perfil_servicio: str
) -> List[Recurso]:
    """
    Retorna los recursos del negocio habilitados para un servicio exacto,
    respetando además el perfil del servicio.
    """
    query = db.query(Recurso).join(
        RecursoServicio,
        Recurso.id_recurso == RecursoServicio.id_recurso
    ).filter(
        Recurso.id_negocio == id_negocio,
        RecursoServicio.id_servicio == id_servicio
    )

    if perfil_servicio != "unisex":
        query = query.filter(
            Recurso.perfil_recurso.in_([perfil_servicio, "unisex"])
        )

    return query.all()

def obtener_primer_negocio_activo(db: Session) -> Optional[Negocio]:
    """
    Retorna el primer negocio disponible en la base de datos.
    Se usa como solución transitoria del MVP mientras no exista
    resolución dinámica completa de tenant por canal o instancia.
    """
    return db.query(Negocio).order_by(Negocio.id_negocio.asc()).first()

def obtener_negocio_por_id(db: Session, id_negocio: int) -> Optional[Negocio]:
    """Retorna un negocio por su ID."""
    return db.query(Negocio).filter(Negocio.id_negocio == id_negocio).first()

def verificar_dia_festivo(db: Session, id_negocio: int, fecha: d_date) -> bool:
    """
    Retorna True si la fecha está bloqueada para el negocio indicado.
    """
    festivo = db.query(DiaNoDisponible).filter(
        and_(
            DiaNoDisponible.id_negocio == id_negocio,
            DiaNoDisponible.fecha == fecha
        )
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

def obtener_excepcion_recurso(
    db: Session,
    id_negocio: int,
    id_recurso: int,
    fecha: d_date
) -> Optional[ExcepcionHorario]:
    """
    Busca si existe una excepción de horario para un recurso en una fecha,
    aislando siempre la consulta por negocio.
    """
    return db.query(ExcepcionHorario).filter(
        and_(
            ExcepcionHorario.id_negocio == id_negocio,
            ExcepcionHorario.id_recurso == id_recurso,
            ExcepcionHorario.fecha == fecha
        )
    ).first()

def obtener_citas_dia(db: Session, id_negocio: int, id_recurso: int, fecha_busqueda: d_date) -> List[Cita]:
    """Retorna las citas confirmadas para un recurso en un día específico, aisladas por negocio."""
    # Filtramos por negocio, recurso, fecha truncada y estado no cancelado
    return db.query(Cita).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.id_recurso == id_recurso,
            Cita.estado_cita == "confirmada",
            func.date(Cita.fecha_hora_inicio) == fecha_busqueda
        )
    ).all()

def obtener_citas_pendientes_cierre(db: Session, id_negocio: int) -> List[Cita]:
    """
    Retorna citas del negocio que ya debieron terminar y aún siguen
    en estado 'confirmada', por lo que requieren cierre manual.
    """
    ahora = datetime.now()

    return db.query(Cita).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.estado_cita == "confirmada",
            Cita.fecha_hora_fin < ahora
        )
    ).order_by(Cita.fecha_hora_inicio.asc()).all()

def cancelar_cita(db: Session, id_negocio: int, id_cita: int) -> bool:
    """
    Cambia el estado de una cita a cancelada, validando que pertenezca
    al negocio indicado.
    """
    cita = db.query(Cita).filter(
        and_(
            Cita.id_cita == id_cita,
            Cita.id_negocio == id_negocio
        )
    ).first()

    if cita:
        cita.estado_cita = "cancelada"
        db.commit()
        return True

    return False

def actualizar_estado_cita(
    db: Session,
    id_negocio: int,
    id_cita: int,
    nuevo_estado: str
) -> bool:
    """
    Actualiza el estado de una cita validando que pertenezca al negocio.
    Estados esperados en esta fase: completada, no_asistio.
    """
    estados_validos = {"completada", "no_asistio", "cancelada", "confirmada", "pendiente"}

    if nuevo_estado not in estados_validos:
        return False

    cita = db.query(Cita).filter(
        and_(
            Cita.id_cita == id_cita,
            Cita.id_negocio == id_negocio
        )
    ).first()

    if not cita:
        return False

    transiciones_validas = {
        "pendiente": {"confirmada", "cancelada"},
        "confirmada": {"completada", "no_asistio", "cancelada"},
        "completada": set(),
        "no_asistio": set(),
        "cancelada": set(),
    }

    estado_actual = cita.estado_cita or "pendiente"

    if nuevo_estado not in transiciones_validas.get(estado_actual, set()):
        return False

    cita.estado_cita = nuevo_estado
    db.commit()
    return True

def guardar_calificacion_cita(
    db: Session,
    id_negocio: int,
    id_cita: int,
    calificacion: int
) -> bool:
    """
    Guarda la calificación del servicio en una cita del negocio indicado.
    """
    if calificacion not in {1, 2, 3, 4, 5}:
        return False

    cita = db.query(Cita).filter(
        and_(
            Cita.id_cita == id_cita,
            Cita.id_negocio == id_negocio
        )
    ).first()

    if not cita:
        return False

    cita.calificacion_servicio = calificacion
    cita.fecha_calificacion = datetime.now()
    db.commit()
    return True

def guardar_periodicidad_cita(
    db: Session,
    id_negocio: int,
    id_cita: int,
    dias_recordatorio: int
) -> bool:
    """
    Guarda la preferencia de recordatorio futuro para una cita completada.
    """
    if dias_recordatorio not in {21, 30}:
        return False

    cita = db.query(Cita).filter(
        and_(
            Cita.id_cita == id_cita,
            Cita.id_negocio == id_negocio
        )
    ).first()

    if not cita:
        return False

    cita.dias_recordatorio_reagendamiento = dias_recordatorio
    cita.fecha_recordatorio_reagendamiento = datetime.now() + timedelta(days=dias_recordatorio)
    cita.recordatorio_reagendamiento_enviado = False
    db.commit()
    return True

def obtener_estadisticas_negocio(db: Session, id_negocio: int) -> dict:
    """
    Retorna estadísticas básicas del negocio para el panel admin.
    """
    total_citas = db.query(func.count(Cita.id_cita)).filter(
        Cita.id_negocio == id_negocio
    ).scalar() or 0

    citas_completadas = db.query(func.count(Cita.id_cita)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.estado_cita == "completada"
        )
    ).scalar() or 0

    citas_no_asistio = db.query(func.count(Cita.id_cita)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.estado_cita == "no_asistio"
        )
    ).scalar() or 0

    citas_canceladas = db.query(func.count(Cita.id_cita)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.estado_cita == "cancelada"
        )
    ).scalar() or 0

    promedio_calificacion = db.query(func.avg(Cita.calificacion_servicio)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.calificacion_servicio.isnot(None)
        )
    ).scalar()

    citas_con_periodicidad = db.query(func.count(Cita.id_cita)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.dias_recordatorio_reagendamiento.isnot(None)
        )
    ).scalar() or 0

    recordatorios_futuros_enviados = db.query(func.count(Cita.id_cita)).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.recordatorio_reagendamiento_enviado == True
        )
    ).scalar() or 0

    porcentaje_no_show = round((citas_no_asistio / total_citas) * 100, 2) if total_citas > 0 else 0.0

    return {
        "total_citas": total_citas,
        "citas_completadas": citas_completadas,
        "citas_no_asistio": citas_no_asistio,
        "citas_canceladas": citas_canceladas,
        "promedio_calificacion": round(float(promedio_calificacion), 2) if promedio_calificacion is not None else None,
        "citas_con_periodicidad": citas_con_periodicidad,
        "recordatorios_futuros_enviados": recordatorios_futuros_enviados,
        "porcentaje_no_show": porcentaje_no_show,
    }

def obtener_citas_detalladas_negocio(db: Session, id_negocio: int) -> List[Cita]:
    """
    Retorna todas las citas del negocio con sus relaciones principales
    cargadas para exportación administrativa.
    """
    return db.query(Cita).options(
        joinedload(Cita.negocio),
        joinedload(Cita.usuario),
        joinedload(Cita.recurso),
        joinedload(Cita.servicio),
    ).filter(
        Cita.id_negocio == id_negocio
    ).order_by(
        Cita.fecha_hora_inicio.desc()
    ).all()

def obtener_top_especialistas_por_citas(db: Session, id_negocio: int, limite: int = 5) -> List[dict]:
    """
    Retorna el top de especialistas por cantidad de citas completadas.
    """
    resultados = db.query(
        Recurso.nombre_recurso,
        func.count(Cita.id_cita).label("total")
    ).join(
        Cita, Recurso.id_recurso == Cita.id_recurso
    ).filter(
        and_(
            Recurso.id_negocio == id_negocio,
            Cita.estado_cita == "completada"
        )
    ).group_by(
        Recurso.id_recurso,
        Recurso.nombre_recurso
    ).order_by(
        desc("total")
    ).limit(limite).all()

    return [
        {"nombre": nombre, "total": total}
        for nombre, total in resultados
    ]

def obtener_top_especialistas_por_calificacion(db: Session, id_negocio: int, limite: int = 5) -> List[dict]:
    """
    Retorna el top de especialistas por calificación promedio,
    considerando solo citas con calificación registrada.
    """
    resultados = db.query(
        Recurso.nombre_recurso,
        func.avg(Cita.calificacion_servicio).label("promedio"),
        func.count(Cita.id_cita).label("total_calificadas")
    ).join(
        Cita, Recurso.id_recurso == Cita.id_recurso
    ).filter(
        and_(
            Recurso.id_negocio == id_negocio,
            Cita.calificacion_servicio.isnot(None)
        )
    ).group_by(
        Recurso.id_recurso,
        Recurso.nombre_recurso
    ).order_by(
        desc("promedio")
    ).limit(limite).all()

    return [
        {
            "nombre": nombre,
            "promedio": round(float(promedio), 2) if promedio is not None else None,
            "total_calificadas": total_calificadas,
        }
        for nombre, promedio, total_calificadas in resultados
    ]

def obtener_top_servicios_mas_reservados(db: Session, id_negocio: int, limite: int = 5) -> List[dict]:
    """
    Retorna los servicios más reservados del negocio.
    """
    resultados = db.query(
        Servicio.nombre_servicio,
        func.count(Cita.id_cita).label("total")
    ).join(
        Cita, Servicio.id_servicio == Cita.id_servicio
    ).filter(
        Servicio.id_negocio == id_negocio
    ).group_by(
        Servicio.id_servicio,
        Servicio.nombre_servicio
    ).order_by(
        desc("total")
    ).limit(limite).all()

    return [
        {"nombre": nombre, "total": total}
        for nombre, total in resultados
    ]

def obtener_servicios_con_mas_no_show(db: Session, id_negocio: int, limite: int = 5) -> List[dict]:
    """
    Retorna los servicios con mayor cantidad de inasistencias.
    """
    resultados = db.query(
        Servicio.nombre_servicio,
        func.count(Cita.id_cita).label("total_no_show")
    ).join(
        Cita, Servicio.id_servicio == Cita.id_servicio
    ).filter(
        and_(
            Servicio.id_negocio == id_negocio,
            Cita.estado_cita == "no_asistio"
        )
    ).group_by(
        Servicio.id_servicio,
        Servicio.nombre_servicio
    ).order_by(
        desc("total_no_show")
    ).limit(limite).all()

    return [
        {"nombre": nombre, "total_no_show": total_no_show}
        for nombre, total_no_show in resultados
    ]

def obtener_citas_con_recordatorio_pendiente(db: Session, id_negocio: int) -> List[Cita]:
    """
    Retorna citas que tienen configurado un recordatorio de reagendamiento
    y ya llegó la fecha de envío.
    """
    ahora = datetime.now()

    return db.query(Cita).filter(
        and_(
            Cita.id_negocio == id_negocio,
            Cita.dias_recordatorio_reagendamiento.isnot(None),
            Cita.fecha_recordatorio_reagendamiento.isnot(None),
            Cita.fecha_recordatorio_reagendamiento <= ahora,
            Cita.recordatorio_reagendamiento_enviado == False
        )
    ).order_by(Cita.fecha_recordatorio_reagendamiento.asc()).all()

def marcar_recordatorio_reagendamiento_enviado(
    db: Session,
    id_negocio: int,
    id_cita: int
) -> bool:
    """
    Marca como enviado el recordatorio futuro de una cita.
    """
    cita = db.query(Cita).filter(
        and_(
            Cita.id_cita == id_cita,
            Cita.id_negocio == id_negocio
        )
    ).first()

    if not cita:
        return False

    cita.recordatorio_reagendamiento_enviado = True
    db.commit()
    return True
