from datetime import datetime, timedelta
from database.connection import SessionLocal
from database.models import Cita
from database import crud

def test_actualizar_estado_cita_confirmada_a_completada():
    """Prueba la transición válida de una cita a estado completada."""
    db = SessionLocal()
    try:
        # Buscamos una cita confirmada para probar
        cita = db.query(Cita).filter(Cita.estado_cita == "confirmada").first()
        if not cita:
            print("SKIPPED: No hay citas confirmadas para testear.")
            return

        exito = crud.actualizar_estado_cita(
            db=db,
            id_negocio=cita.id_negocio,
            id_cita=cita.id_cita,
            nuevo_estado="completada"
        )

        assert exito is True
        
        # Verificar que quedó guardado
        db.refresh(cita)
        assert cita.estado_cita == "completada"
    finally:
        db.close()

def test_transicion_invalida_cancelada_a_completada():
    """Prueba que no se permitan saltos de estado ilógicos."""
    db = SessionLocal()
    try:
        # Creamos o buscamos una cita cancelada
        cita = db.query(Cita).filter(Cita.estado_cita == "cancelada").first()
        if not cita:
            return

        exito = crud.actualizar_estado_cita(
            db=db,
            id_negocio=cita.id_negocio,
            id_cita=cita.id_cita,
            nuevo_estado="completada"
        )

        assert exito is False
    finally:
        db.close()

def test_guardar_calificacion_cita():
    """Prueba el registro de calificación CSAT."""
    db = SessionLocal()
    try:
        cita = db.query(Cita).filter(Cita.estado_cita == "completada").first()
        if not cita:
            return

        exito = crud.guardar_calificacion_cita(
            db=db,
            id_negocio=cita.id_negocio,
            id_cita=cita.id_cita,
            calificacion=5
        )

        assert exito is True
        db.refresh(cita)
        assert cita.calificacion_servicio == 5
        assert cita.fecha_calificacion is not None
    finally:
        db.close()

def test_guardar_periodicidad_cita():
    """Prueba el registro de intención de re-agendamiento."""
    db = SessionLocal()
    try:
        cita = db.query(Cita).filter(Cita.estado_cita == "completada").first()
        if not cita:
            return

        exito = crud.guardar_periodicidad_cita(
            db=db,
            id_negocio=cita.id_negocio,
            id_cita=cita.id_cita,
            dias_recordatorio=21
        )

        assert exito is True
        db.refresh(cita)
        assert cita.dias_recordatorio_reagendamiento == 21
        assert cita.fecha_recordatorio_reagendamiento is not None
        assert cita.recordatorio_reagendamiento_enviado is False
    finally:
        db.close()
