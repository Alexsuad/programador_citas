# File: modules/availability.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: El Cerebro - Calculador dinámico de agendas disponibles.
# Rol: Motor de lógica de negocio (Etapa 2).
# ──────────────────────────────────────────────────────────────────────

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from database.models import Servicio, Cita
from database import crud
from utils.date_utils import calcular_hora_fin
from typing import List, Dict

def generar_slots_disponibles(
    db: Session, 
    id_recurso: int, 
    fecha_busqueda: date, 
    id_servicio: int
) -> List[datetime]:
    """
    Función maestra para calcular slots de tiempo disponibles para un recurso.
    
    Lógica Matematica Estricta:
    1. Filtro Festivo.
    2. Filtro Horario Laboral.
    3. Loop de generación cada 30 minutos.
    4. Filtro de Solapamiento (Crucial).
    5. Filtro de Tiempo Real (Margen de 30m).
    """
    
    # 0. Preparación: Obtener duración del servicio y buffer time
    servicio = db.get(Servicio, id_servicio)
    if not servicio:
        return []
        
    id_negocio = servicio.id_negocio
    buffer_time = crud.obtener_buffer_time(db, id_negocio)
    
    # 0.1 Obtener zona horaria del negocio (reutilizamos objeto ya cargado)
    negocio = servicio.negocio
    tz_name = "America/Bogota"
    if negocio and negocio.configuracion_json:
        tz_name = negocio.configuracion_json.get("timezone", "America/Bogota")
    tz = ZoneInfo(tz_name)
    
    # 1. Prioridad Máxima: ¿Existe una excepción para este día?
    excepcion = crud.obtener_excepcion_recurso(db, id_recurso, fecha_busqueda)
    
    if excepcion:
        # Si hay excepción, usamos ese horario y nos saltamos el check de festivo
        h_entrada_str, h_salida_str = excepcion.hora_inicio, excepcion.hora_fin
    else:
        # 2. Si no hay excepción, verificamos si es día festivo/bloqueado
        if crud.verificar_dia_festivo(db, id_negocio, fecha_busqueda):
            return []
            
        # 3. Si no es festivo, usamos el horario normal
        horario = crud.obtener_horario_recurso(db, id_recurso, fecha_busqueda.weekday())
        if not horario:
            return []
        h_entrada_str, h_salida_str = horario
        
    # Convertir strings "HH:MM" a objetos datetime para cálculos
    inicio_laboral = datetime.combine(fecha_busqueda, datetime.strptime(h_entrada_str, "%H:%M").time())
    fin_laboral = datetime.combine(fecha_busqueda, datetime.strptime(h_salida_str, "%H:%M").time())
    
    # c. Obtener citas existentes para este dia
    citas_existentes = crud.obtener_citas_dia(db, id_recurso, fecha_busqueda)
    
    # d. Generar slots (Empezamos cada 30 minutos)
    slots_disponibles = []
    current_time = inicio_laboral
    intervalo_minutos = 30
    
    ahora_local = datetime.now(tz).replace(tzinfo=None) # Momento actual en el negocio
    limite_tiempo_real = ahora_local + timedelta(minutes=30)

    while current_time + timedelta(minutes=servicio.duracion_minutos) <= fin_laboral:
        # 1. Calcular fin proyectado de esta posible cita
        # Nota: El buffer se suma para asegurar que la SIGUIENTE cita no choque
        posible_fin = calcular_hora_fin(current_time, servicio.duracion_minutos, buffer_time)
        
        # 2. Filtro de Tiempo Real: Si es hoy, descartar slots pasados o muy proximos
        if fecha_busqueda == ahora_local.date() and current_time < limite_tiempo_real:
            current_time += timedelta(minutes=intervalo_minutos)
            continue

        # 3. Filtro de Solapamiento
        es_valido = True
        for cita in citas_existentes:
            # Condición de choque: inicio_nuevo < fin_existente Y fin_nuevo > inicio_existente
            if current_time < cita.fecha_hora_fin and posible_fin > cita.fecha_hora_inicio:
                es_valido = False
                break
        
        if es_valido:
            slots_disponibles.append(current_time)
            
        # Avanzar el puntero de tiempo
        current_time += timedelta(minutes=intervalo_minutos)
        
    return slots_disponibles
