# File: tests/test_admin_habilidades.py
import pytest
from database.connection import SessionLocal
from database import crud
from database.models import Recurso, Servicio

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_agregar_y_quitar_habilidad(db_session):
    negocio = crud.obtener_primer_negocio_activo(db_session)
    assert negocio is not None

    recurso = db_session.query(Recurso).filter(Recurso.id_negocio == negocio.id_negocio).first()
    servicio = db_session.query(Servicio).filter(Servicio.id_negocio == negocio.id_negocio).first()

    assert recurso is not None
    assert servicio is not None

    id_n = negocio.id_negocio
    id_r = recurso.id_recurso
    id_s = servicio.id_servicio

    # Ensure it's removed first for predictable environment
    crud.quitar_habilidad_a_recurso(db_session, id_n, id_r, id_s)

    habilitados = crud.obtener_servicios_habilitados_de_recurso(db_session, id_n, id_r)
    assert not any(s.id_servicio == id_s for s in habilitados)

    # Add ability
    resultado = crud.agregar_habilidad_a_recurso(db_session, id_n, id_r, id_s)
    assert resultado is True

    habilitados = crud.obtener_servicios_habilitados_de_recurso(db_session, id_n, id_r)
    assert any(s.id_servicio == id_s for s in habilitados)

    # Remove ability
    resultado = crud.quitar_habilidad_a_recurso(db_session, id_n, id_r, id_s)
    assert resultado is True

    habilitados = crud.obtener_servicios_habilitados_de_recurso(db_session, id_n, id_r)
    assert not any(s.id_servicio == id_s for s in habilitados)
