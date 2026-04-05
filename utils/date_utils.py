# File: utils/date_utils.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Utilidades para cálculos matemáticos con fechas y horas.
# Rol: Aritmética de tiempo (Etapa 2).
# ──────────────────────────────────────────────────────────────────────

from datetime import datetime, timedelta

def calcular_hora_fin(hora_inicio: datetime, duracion_minutos: int, buffer_time: int = 10) -> datetime:
    """
    Calcula la hora de finalización de una cita sumando la duración 
    del servicio y el tiempo de buffer (limpieza/preparación).
    
    Args:
        hora_inicio (datetime): Fecha y hora de inicio de la cita.
        duracion_minutos (int): Tiempo que dura el servicio.
        buffer_time (int): Tiempo de margen posterior.
        
    Returns:
        datetime: El momento exacto en que el recurso vuelve a estar libre.
    """
    total_minutos = duracion_minutos + buffer_time
    return hora_inicio + timedelta(minutes=total_minutos)
