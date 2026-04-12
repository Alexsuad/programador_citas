# File: tests/test_exportacion_csv.py
import os
import pytest
from database.connection import SessionLocal
from database import crud
from modules.admin import exportar_citas_csv, exportar_citas_detalle_csv

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_exportacion_csv_crea_archivo(db_session):
    negocio = crud.obtener_primer_negocio_activo(db_session)
    assert negocio is not None
    
    filepath = exportar_citas_csv(db_session, negocio.id_negocio)
    assert os.path.exists(filepath)
    assert filepath.endswith('.csv')
    
    # Check that file can be read
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        assert "ID Cita" in content
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)

def test_exportacion_citas_detalle_csv_crea_archivo(db_session):
    negocio = crud.obtener_primer_negocio_activo(db_session)
    assert negocio is not None
    
    filepath = exportar_citas_detalle_csv(db_session, negocio.id_negocio)
    assert os.path.exists(filepath)
    assert filepath.endswith('.csv')
    
    # Check that file can be read
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        assert "id_cita" in content
    
    # Cleanup
    if os.path.exists(filepath):
        os.remove(filepath)
