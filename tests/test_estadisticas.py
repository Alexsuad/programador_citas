# File: tests/test_estadisticas.py
import pytest
from database.connection import SessionLocal
from database import crud

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_estadisticas_basicas_negocio(db_session):
    negocio = crud.obtener_primer_negocio_activo(db_session)
    assert negocio is not None

    estadisticas = crud.obtener_estadisticas_negocio(db_session, negocio.id_negocio)
    
    assert "total_citas" in estadisticas
    assert "citas_completadas" in estadisticas
    assert "citas_no_asistio" in estadisticas
    assert "citas_canceladas" in estadisticas
    assert "promedio_calificacion" in estadisticas
    assert "porcentaje_no_show" in estadisticas

def test_top_especialistas_y_servicios(db_session):
    negocio = crud.obtener_primer_negocio_activo(db_session)
    assert negocio is not None

    top_citas = crud.obtener_top_especialistas_por_citas(db_session, negocio.id_negocio)
    top_calificacion = crud.obtener_top_especialistas_por_calificacion(db_session, negocio.id_negocio)
    top_servicios = crud.obtener_top_servicios_mas_reservados(db_session, negocio.id_negocio)

    assert isinstance(top_citas, list)
    assert isinstance(top_calificacion, list)
    assert isinstance(top_servicios, list)
