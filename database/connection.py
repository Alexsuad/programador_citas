# File: database/connection.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Gestión de la conexión a PostgreSQL y ciclo de vida de sesiones.
# Rol: Corazón del sistema de persistencia.
# ──────────────────────────────────────────────────────────────────────

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ El valor de DATABASE_URL no está configurado en el archivo .env")

# TODO: Entorno SQLite temporal. Las migraciones de Alembic actuales deberán ser 
# reiniciadas (borradas y recreadas) al migrar a PostgreSQL en producción.
connect_args = {}
if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Configuración dinámica de argumentos para el motor
engine_args = {
    "connect_args": connect_args,
    "pool_recycle": 3600,
    "pool_pre_ping": True
}

# Solo añadir pooling si NO es SQLite
if not DATABASE_URL.startswith("sqlite"):
    engine_args["pool_size"] = 5
    engine_args["max_overflow"] = 10

engine = create_engine(DATABASE_URL, **engine_args)

# Constructor de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para la creación de modelos
Base = declarative_base()

def obtener_bd():
    """
    Generador de sesiones de base de datos.
    Garantiza que la sesión se cierre siempre, incluso si ocurre una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
