# File: database/models.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Definición del Esquema Universal de datos (Modelado ER).
# Rol: Representación de entidades de negocio en PostgreSQL.
# ──────────────────────────────────────────────────────────────────────

from sqlalchemy import (
    Column, Integer, String, Boolean, Float, 
    DateTime, ForeignKey, JSON, BigInteger, Date
)
from sqlalchemy.orm import relationship
from database.connection import Base
from datetime import datetime

class Negocio(Base):
    __tablename__ = "negocios"

    id_negocio = Column(Integer, primary_key=True, index=True)
    nombre_comercial = Column(String(100), nullable=False)
    tipo_industria = Column(String(50))  # Ej: Barbería, Veterinaria, Clínica
    configuracion_json = Column(JSON, default={})  # Configuración específica del negocio

    # Relaciones
    recursos = relationship("Recurso", back_populates="negocio", cascade="all, delete-orphan")
    servicios = relationship("Servicio", back_populates="negocio", cascade="all, delete-orphan")
    citas = relationship("Cita", back_populates="negocio")

class Recurso(Base):
    __tablename__ = "recursos"

    id_recurso = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(Integer, ForeignKey("negocios.id_negocio"), nullable=False)
    nombre_recurso = Column(String(100), nullable=False)  # Ej: Nombre del barbero o habitación
    tipo_recurso = Column(String(50))  # Ej: Humano, Maquinaria, Espacio
    capacidad = Column(Integer, default=1)  # Cuántas citas simultáneas puede atender

    # Relaciones
    negocio = relationship("Negocio", back_populates="recursos")
    horarios = relationship("HorarioRecurso", back_populates="recurso", cascade="all, delete-orphan")
    excepciones = relationship("ExcepcionHorario", back_populates="recurso", cascade="all, delete-orphan")
    citas = relationship("Cita", back_populates="recurso")

class Servicio(Base):
    __tablename__ = "servicios"

    id_servicio = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(Integer, ForeignKey("negocios.id_negocio"), nullable=False)
    nombre_servicio = Column(String(100), nullable=False)
    duracion_minutos = Column(Integer, nullable=False)
    precio = Column(Float, default=0.0)
    activo = Column(Boolean, default=True)

    # Relaciones
    negocio = relationship("Negocio", back_populates="servicios")
    citas = relationship("Cita", back_populates="servicio")

class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True, index=True)
    id_telegram = Column(BigInteger, unique=True, index=True, nullable=False)
    nombre_usuario = Column(String(100))
    telefono = Column(String(20))
    correo_electronico = Column(String(100))
    
    # Privacidad y Términos (Habeas Data)
    acepta_privacidad = Column(Boolean, default=False)
    fecha_aceptacion_terminos = Column(DateTime)
    version_terminos_aceptada = Column(String(10))
    recibir_marketing = Column(Boolean, default=False)

    # Relaciones
    sujetos = relationship("EntidadSujeto", back_populates="usuario_dueno")
    citas = relationship("Cita", back_populates="usuario")

class EntidadSujeto(Base):
    __tablename__ = "entidades_sujetos"

    id_sujeto = Column(Integer, primary_key=True, index=True)
    id_usuario_dueno = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre_sujeto = Column(String(100), nullable=False)  # Ej: Paco (el perro) o Placas (el auto)
    metadatos_json = Column(JSON, default={})  # Flexibilidad absoluta por industria

    # Relaciones
    usuario_dueno = relationship("Usuario", back_populates="sujetos")
    citas = relationship("Cita", back_populates="sujeto")

class Cita(Base):
    __tablename__ = "citas"

    id_cita = Column(Integer, primary_key=True, index=True)
    id_negocio = Column(Integer, ForeignKey("negocios.id_negocio"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_sujeto = Column(Integer, ForeignKey("entidades_sujetos.id_sujeto"), nullable=False)
    id_recurso = Column(Integer, ForeignKey("recursos.id_recurso"), nullable=False)
    id_servicio = Column(Integer, ForeignKey("servicios.id_servicio"), nullable=False)
    
    # Tiempos
    fecha_hora_inicio = Column(DateTime, nullable=False)
    fecha_hora_fin = Column(DateTime, nullable=False)
    
    # Estado y Auditoría
    estado_cita = Column(String(20), default="pendiente")  # pendiente, confirmada, cancelada, completada
    precio_cobrado = Column(Float)  # Por si el precio cambió después del agendamiento
    
    # Notificaciones
    recordatorio_24h_enviado = Column(Boolean, default=False)
    recordatorio_2h_enviado = Column(Boolean, default=False)
    fecha_recordatorio_solicitado = Column(DateTime, nullable=True)

    # Relaciones
    negocio = relationship("Negocio", back_populates="citas")
    usuario = relationship("Usuario", back_populates="citas")
    sujeto = relationship("EntidadSujeto", back_populates="citas")
    recurso = relationship("Recurso", back_populates="citas")
    servicio = relationship("Servicio", back_populates="citas")

class HorarioRecurso(Base):
    __tablename__ = "horarios_recursos"

    id_horario = Column(Integer, primary_key=True, index=True)
    id_recurso = Column(Integer, ForeignKey("recursos.id_recurso"), nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    hora_inicio = Column(String(5), nullable=False)  # Formato "HH:MM"
    hora_fin = Column(String(5), nullable=False)

    # Relaciones
    recurso = relationship("Recurso", back_populates="horarios")

class ExcepcionHorario(Base):
    __tablename__ = "excepciones_horarios"

    id_excepcion = Column(Integer, primary_key=True, index=True)
    id_recurso = Column(Integer, ForeignKey("recursos.id_recurso"), nullable=False)
    fecha = Column(Date, nullable=False)
    hora_inicio = Column(String(5), nullable=False)
    hora_fin = Column(String(5), nullable=False)

    # Relaciones
    recurso = relationship("Recurso", back_populates="excepciones")

class DiaNoDisponible(Base):
    __tablename__ = "dias_no_disponibles"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    motivo = Column(String(255))
    creado_por = Column(Integer)  # ID del admin/sistema que bloqueó el día
