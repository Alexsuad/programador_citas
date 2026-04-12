# File: tests/test_availability.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Pruebas automatizadas aisladas del Motor de Disponibilidad.
# ──────────────────────────────────────────────────────────────────────

import pytest
from datetime import date, timedelta, datetime
from database.connection import SessionLocal
from database.models import DiaNoDisponible, ExcepcionHorario, Cita, Usuario, EntidadSujeto
from modules.availability import generar_slots_disponibles

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_festivo_puro_devuelve_cero_slots(db_session):
    """Verifica que un día festivo bloqueado sin excepciones no retorne slots."""
    fecha = date.today() + timedelta(days=10) # Fecha lejana para estar limpia
    
    # Limpieza total para esta fecha
    db_session.query(DiaNoDisponible).filter(DiaNoDisponible.fecha == fecha).delete()
    db_session.query(ExcepcionHorario).filter(ExcepcionHorario.fecha == fecha).delete()
    
    # Crear Festivo
    festivo = DiaNoDisponible(id_negocio=1, fecha=fecha, motivo="Cierre Total")
    db_session.add(festivo)
    db_session.commit()
    
    slots = generar_slots_disponibles(db_session, id_recurso=1, fecha_busqueda=fecha, id_servicio=1)
    assert len(slots) == 0

def test_excepcion_permite_trabajar_en_festivo(db_session):
    """Verifica que una excepción habilite slots en un día festivo."""
    fecha = date.today() + timedelta(days=11)
    
    # Limpieza
    db_session.query(DiaNoDisponible).filter(DiaNoDisponible.fecha == fecha).delete()
    db_session.query(ExcepcionHorario).filter(ExcepcionHorario.fecha == fecha).delete()
    
    # Crear Festivo Y Excepción (La excepción debe ganar)
    festivo = DiaNoDisponible(id_negocio=1, fecha=fecha, motivo="Festivo")
    excep = ExcepcionHorario(
        id_negocio=1,
        id_recurso=1,
        fecha=fecha,
        hora_inicio="09:00",
        hora_fin="11:00"
    )
    db_session.add(festivo)
    db_session.add(excep)
    db_session.commit()
    
    slots = generar_slots_disponibles(db_session, id_recurso=1, fecha_busqueda=fecha, id_servicio=1)
    # 09:00 (Fin 09:55) -> OK
    # 09:30 (Fin 10:25) -> OK
    # 10:00 (Fin 10:55) -> OK
    # 10:30 (Fin 11:25) -> NO (excede 11:00)
    assert len(slots) == 3

def test_solapamiento_bloquea_correctamente(db_session):
    """Verifica que una cita bloquee su slot y los adyacentes según buffer."""
    # Buscamos un martes garantizado para tener horario laboral normal
    fecha = date.today() + timedelta(days=(1 - date.today().weekday() + 14) % 7 + 1)
    
    # Limpieza profunda
    db_session.query(Cita).filter(Cita.id_recurso == 1).delete() # Borramos todas para este test
    db_session.query(DiaNoDisponible).filter(DiaNoDisponible.fecha == fecha).delete()
    db_session.query(ExcepcionHorario).filter(ExcepcionHorario.fecha == fecha).delete()
    db_session.commit()
    
    # Insertar cita 10:00 - 10:30
    user = db_session.query(Usuario).first()
    sujeto = db_session.query(EntidadSujeto).first()
    h_inicio = datetime.combine(fecha, datetime.strptime("10:00", "%H:%M").time())
    h_fin = h_inicio + timedelta(minutes=30)
    
    cita = Cita(
        id_negocio=1, id_usuario=user.id_usuario, id_sujeto=sujeto.id_sujeto,
        id_recurso=1, id_servicio=1,
        fecha_hora_inicio=h_inicio, fecha_hora_fin=h_fin,
        estado_cita="confirmada"
    )
    db_session.add(cita)
    db_session.commit()
    
    slots = [s.strftime("%H:%M") for s in generar_slots_disponibles(db_session, 1, fecha, 1)]
    
    # Verificaciones
    assert "10:00" not in slots
    assert "09:30" not in slots # Porque 09:30 + 45 + 10 = 10:25 (Choca con inicio 10:00)
    assert "10:30" in slots    # Porque 10:30 >= Fin 10:30
