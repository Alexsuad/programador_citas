# File: modules/scheduler.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: El Vigilante - Ejecución de tareas programadas.
# Rol: Automatización de recordatorios y limpieza de agenda (Etapa 5).
# ──────────────────────────────────────────────────────────────────────

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Cita, Usuario
from modules.notifications import enviar_recordatorio_telegram
from datetime import datetime, timedelta
from typing import List

async def tarea_recordatorio_24h(bot):
    """Busca citas confirmadas para las próximas 24 horas y envía alertas."""
    db: Session = SessionLocal()
    try:
        ahora = datetime.now()
        inf = ahora + timedelta(hours=23, minutes=30)
        sup = ahora + timedelta(hours=24, minutes=30)
        
        # Consultar citas en la ventana de tiempo
        citas: List[Cita] = db.query(Cita).filter(
            Cita.estado_cita == "confirmada",
            Cita.recordatorio_24h_enviado == False,
            Cita.fecha_hora_inicio.between(inf, sup)
        ).all()
        
        for cita in citas:
            usuario = db.query(Usuario).get(cita.id_usuario)
            if usuario:
                msg = (
                    "⏰ *Recordatorio de Cita (24h)*\n\n"
                    f"Hola {usuario.nombre_usuario.split()[0] if usuario.nombre_usuario else 'Cliente'}! 👋\n"
                    f"Te recordamos que tienes una cita mañana:\n"
                    f"📅 *{cita.fecha_hora_inicio.strftime('%d/%m/%Y')}* a las "
                    f"🕒 *{cita.fecha_hora_inicio.strftime('%H:%M')}*.\n\n"
                    "¡Te esperamos con entusiasmo!"
                )
                exito = await enviar_recordatorio_telegram(bot, usuario.id_telegram, msg)
                if exito:
                    cita.recordatorio_24h_enviado = True
                    db.commit()
    finally:
        db.close()

async def tarea_recordatorio_2h(bot):
    """Busca citas confirmadas para las próximas 2 horas y envía alertas."""
    db: Session = SessionLocal()
    try:
        ahora = datetime.now()
        inf = ahora + timedelta(minutes=90)  # 1.5 horas
        sup = ahora + timedelta(minutes=150) # 2.5 horas
        
        citas: List[Cita] = db.query(Cita).filter(
            Cita.estado_cita == "confirmada",
            Cita.recordatorio_2h_enviado == False,
            Cita.fecha_hora_inicio.between(inf, sup)
        ).all()
        
        for cita in citas:
            usuario = db.query(Usuario).get(cita.id_usuario)
            if usuario:
                msg = (
                    "🚀 *¡Casi es tu Cita! (2h)*\n\n"
                    "¡Prepárate! Tu agenda inicia pronto:\n"
                    f"⏰ A las *{cita.fecha_hora_inicio.strftime('%H:%M')}*.\n\n"
                    "¡Nos vemos en un par de horas! ✨"
                )
                exito = await enviar_recordatorio_telegram(bot, usuario.id_telegram, msg)
                if exito:
                    cita.recordatorio_2h_enviado = True
                    db.commit()
    finally:
        db.close()

def iniciar_scheduler(bot):
    """Inicializa y arranca el programador asíncrono."""
    scheduler = AsyncIOScheduler()
    
    # Programar las tareas cada 30 minutos
    scheduler.add_job(tarea_recordatorio_24h, 'interval', minutes=30, args=[bot])
    scheduler.add_job(tarea_recordatorio_2h, 'interval', minutes=15, args=[bot])
    
    scheduler.start()
    print("🔔 Motor de Notificaciones (APScheduler) activado.")
