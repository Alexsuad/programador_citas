# File: modules/scheduler.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: El Vigilante - Ejecución de tareas programadas.
# Rol: Automatización de recordatorios y limpieza de agenda (Etapa 5).
# ──────────────────────────────────────────────────────────────────────

import logging
from datetime import datetime, timedelta
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Negocio, Cita, Usuario
from database import crud
from modules.notifications import enviar_recordatorio_telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

def obtener_tz_negocio(db: Session, id_negocio: int) -> ZoneInfo:
    """Obtiene la zona horaria del negocio desde su configuración JSON."""
    negocio = db.get(Negocio, id_negocio)
    tz_name = "Europe/Madrid"
    if negocio and negocio.configuracion_json:
        tz_name = negocio.configuracion_json.get("timezone", "Europe/Madrid")
    return ZoneInfo(tz_name)

async def tarea_recordatorio_24h(bot):
    """Busca citas confirmadas para las próximas 24 horas y envía alertas."""
    db: Session = SessionLocal()
    try:
        negocios = db.query(Negocio).all()
        for negocio in negocios:
            tz = obtener_tz_negocio(db, negocio.id_negocio)
            ahora = datetime.now(tz).replace(tzinfo=None) # Volvemos a naive para comparar con SQLite
            inf = ahora + timedelta(hours=23, minutes=30)
            sup = ahora + timedelta(hours=24, minutes=30)
            
            # Consultar citas en la ventana de tiempo
            citas: List[Cita] = db.query(Cita).filter(
                Cita.id_negocio == negocio.id_negocio,
                Cita.estado_cita == "confirmada",
                Cita.recordatorio_24h_enviado == False,
                Cita.fecha_hora_inicio.between(inf, sup)
            ).all()
            
            logger.info("Scheduler 24h: %s citas encontradas para recordatorio.", len(citas))
            
            for cita in citas:
                usuario = db.get(Usuario, cita.id_usuario)
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
                        logger.info(
                            "Recordatorio 24h enviado. id_cita=%s, id_usuario=%s",
                            cita.id_cita,
                            cita.id_usuario,
                        )
            
            # Commit por negocio para ser más eficiente y reducir bloqueos de DB
            db.commit()
    except Exception:
        logger.exception("Error en tarea_recordatorio_24h")
        db.rollback()
    finally:
        db.close()

async def tarea_recordatorio_2h(bot):
    """Busca citas confirmadas para las próximas 2 horas y envía alertas."""
    db: Session = SessionLocal()
    try:
        negocios = db.query(Negocio).all()
        for negocio in negocios:
            tz = obtener_tz_negocio(db, negocio.id_negocio)
            ahora = datetime.now(tz).replace(tzinfo=None)
            inf = ahora + timedelta(minutes=90)  # 1.5 horas
            sup = ahora + timedelta(minutes=150) # 2.5 horas
            
            citas: List[Cita] = db.query(Cita).filter(
                Cita.id_negocio == negocio.id_negocio,
                Cita.estado_cita == "confirmada",
                Cita.recordatorio_2h_enviado == False,
                Cita.fecha_hora_inicio.between(inf, sup)
            ).all()
            
            logger.info("Scheduler 2h: %s citas encontradas para recordatorio.", len(citas))
            
            for cita in citas:
                usuario = db.get(Usuario, cita.id_usuario)
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
                        logger.info(
                            "Recordatorio 2h enviado. id_cita=%s, id_usuario=%s",
                            cita.id_cita,
                            cita.id_usuario,
                        )
            
            db.commit()
    except Exception:
        logger.exception("Error en tarea_recordatorio_2h")
        db.rollback()
    finally:
        db.close()

async def tarea_recordatorio_reagendamiento(bot):
    """
    Busca citas con recordatorio futuro vencido y envía una invitación
    para volver a reservar.
    """
    db: Session = SessionLocal()
    try:
        negocio = crud.obtener_primer_negocio_activo(db)
        if not negocio:
            logger.warning("No existe negocio activo para procesar recordatorios de reagendamiento.")
            return

        id_negocio = negocio.id_negocio
        citas = crud.obtener_citas_con_recordatorio_pendiente(db, id_negocio)

        logger.info(
            "Scheduler reagendamiento: %s citas encontradas para recordatorio futuro.",
            len(citas)
        )

        for cita in citas:
            try:
                if not cita.usuario or not cita.usuario.id_telegram:
                    continue

                nombre_cliente = cita.usuario.nombre_usuario or "Cliente"

                await bot.send_message(
                    chat_id=cita.usuario.id_telegram,
                    text=(
                        "📅 *Ya va siendo hora de tu próxima cita*\n\n"
                        f"Hola {nombre_cliente}, te escribimos para recordarte que puedes reservar nuevamente cuando quieras."
                    ),
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📅 Reservar ahora", callback_data="reagendar_si")],
                        [InlineKeyboardButton("❌ Ahora no", callback_data="reagendar_no")],
                    ])
                )

                crud.marcar_recordatorio_reagendamiento_enviado(
                    db=db,
                    id_negocio=id_negocio,
                    id_cita=cita.id_cita
                )

                logger.info(
                    "Recordatorio futuro enviado. id_cita=%s, id_usuario=%s",
                    cita.id_cita,
                    cita.id_usuario,
                )
            except Exception as e:
                logger.error(f"⚠️ Error enviando recordatorio futuro id_cita={cita.id_cita}: {e}")
                continue

    except Exception:
        logger.exception("Error en tarea_recordatorio_reagendamiento")
        db.rollback()
async def tarea_limpiar_temporales():
    """Limpia archivos CSV del directorio tmp/ que tengan más de 24 horas."""
    path_tmp = "tmp"
    if not os.path.exists(path_tmp):
        return

    ahora = datetime.now().timestamp()
    limite = 24 * 3600  # 24 horas

    eliminados = 0
    for f in os.listdir(path_tmp):
        if f.endswith(".csv"):
            f_path = os.path.join(path_tmp, f)
            if ahora - os.path.getmtime(f_path) > limite:
                os.remove(f_path)
                eliminados += 1

    if eliminados > 0:
        logger.info(f"Higiene operativa: {eliminados} archivos CSV temporales eliminados.")

def iniciar_scheduler(bot):
    """Inicializa y arranca el programador asíncrono."""
    scheduler = AsyncIOScheduler()
    
    # Programar las tareas cada 30 minutos
    scheduler.add_job(tarea_recordatorio_24h, 'interval', minutes=30, args=[bot])
    scheduler.add_job(tarea_recordatorio_2h, 'interval', minutes=15, args=[bot])
    scheduler.add_job(tarea_recordatorio_reagendamiento, 'interval', minutes=60, args=[bot])
    scheduler.add_job(tarea_limpiar_temporales, 'cron', hour=3)  # Cada madrugada a las 3:00 am
    
    scheduler.start()
    logger.info("Motor de notificaciones APScheduler activado.")
