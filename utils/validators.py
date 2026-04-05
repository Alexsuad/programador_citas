# File: utils/validators.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Esquemas de validación de datos de entrada.
# Rol: Capa de seguridad y tipado (Pydantic).
# ──────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional

class UsuarioCreate(BaseModel):
    """Esquema para la creación de nuevos usuarios."""
    id_telegram: int = Field(..., description="ID único de Telegram del usuario")
    nombre_usuario: str = Field(..., min_length=3, max_length=50)
    telefono: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    correo_electronico: EmailStr
    acepta_privacidad: bool = Field(..., description="Debe aceptar términos y condiciones")
    
    @validator('nombre_usuario')
    def nombre_limpio(cls, v):
        return v.strip()

class CitaCreate(BaseModel):
    """Esquema para la creación de citas."""
    id_negocio: int
    id_usuario: int
    id_sujeto: int
    id_recurso: int
    id_servicio: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime

    @validator('fecha_hora_inicio')
    def fecha_futura(cls, v):
        if v < datetime.now():
            raise ValueError("La fecha de inicio debe ser en el futuro")
        return v

    @validator('fecha_hora_fin')
    def duracion_valida(cls, v, values):
        if 'fecha_hora_inicio' in values and v <= values['fecha_hora_inicio']:
            raise ValueError("La fecha de fin debe ser posterior a la de inicio")
        return v
