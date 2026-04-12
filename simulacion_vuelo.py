import asyncio
import logging
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from database.connection import SessionLocal
from database.models import Usuario, EntidadSujeto, Servicio, Recurso, Cita, Negocio
from modules.admin import exportar_citas_csv
from modules.availability import generar_slots_disponibles
from modules.scheduler import tarea_recordatorio_24h

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock del Bot de Telegram para pruebas Offline
class MockBot:
    async def send_message(self, chat_id, text, parse_mode=None):
        logger.info("[BOT MOCK] Enviado a %s: %s...", chat_id, text[:50])
        return True

async def simular_ciclo_completo():
    logger.info("✈️  INICIANDO PRUEBA DE VUELO FINAL - MVP AGENDAMIENTO")
    db = SessionLocal()
    bot = MockBot()
    
    try:
        # --- PASO PREVIO: OBTENER NEGOCIO ---
        negocio = db.query(Negocio).first()
        if not negocio:
            logger.error("❌ No hay negocios en la BD. Ejecuta el seeding primero.")
            return
        
        id_negocio = negocio.id_negocio
        tz_name = negocio.configuracion_json.get("timezone", "America/Bogota")
        tz = ZoneInfo(tz_name)

        # --- PASO A: REGISTRO Y CONSENTIMIENTO ---
        logger.info("Paso A: Simulando Registro de Usuario (Habeas Data)...")
        usuario = db.query(Usuario).filter(Usuario.id_telegram == 999999).first()
        if not usuario:
            usuario = Usuario(
                id_telegram=999999,
                nombre_usuario="Andrés de Prueba",
                acepta_privacidad=True,
                fecha_aceptacion_terminos=datetime.now(tz),
                version_terminos_aceptada="1.0-FlightTest"
            )
            db.add(usuario)
            db.flush()
        
        sujeto = db.query(EntidadSujeto).filter(EntidadSujeto.id_usuario_dueno == usuario.id_usuario).first()
        if not sujeto:
            sujeto = EntidadSujeto(id_usuario_dueno=usuario.id_usuario, nombre_sujeto="Andrés de Prueba")
            db.add(sujeto)
        
        db.commit()
        logger.info(f"   ✅ Usuario '{usuario.nombre_usuario}' listo con ID {usuario.id_usuario}.")

        # --- PASO B/C: SELECCIÓN DE CATALOGO ---
        logger.info("Paso B/C: Consultando Servicios y Recursos...")
        servicio = db.query(Servicio).filter(Servicio.id_negocio == id_negocio).first()
        barbero = db.query(Recurso).filter(Recurso.id_negocio == id_negocio).first()
        
        if not servicio or not barbero:
            logger.error("❌ No se encontró servicio o recurso para el negocio.")
            return
            
        logger.info(f"   ✅ Seleccionado: '{servicio.nombre_servicio}' con '{barbero.nombre_recurso}'.")

        # --- PASO D: MOTOR DE DISPONIBILIDAD ---
        logger.info("Paso D: Invocando al 'Cerebro' para mañana...")
        manana = date.today() + timedelta(days=1)
        slots = generar_slots_disponibles(db, barbero.id_recurso, manana, servicio.id_servicio)
        logger.info(f"   ✅ Se encontraron {len(slots)} slots.")

        # --- PASO E: CONFIRMACIÓN Y PERSISTENCIA ---
        logger.info("Paso E: Confirmando Cita y Guardando en DB...")
        if not slots:
            logger.warning("⚠️ No hay slots disponibles para la prueba.")
            return

        h_inicio = slots[0] # Tomamos el primer slot disponible
        h_fin = h_inicio + timedelta(minutes=servicio.duracion_minutos)
        
        # Limpiar citas previas de prueba idénticas
        db.query(Cita).filter(
            Cita.id_recurso == barbero.id_recurso, 
            Cita.fecha_hora_inicio == h_inicio
        ).delete()
        
        cita = Cita(
            id_negocio=id_negocio, 
            id_usuario=usuario.id_usuario, 
            id_sujeto=sujeto.id_sujeto,
            id_recurso=barbero.id_recurso, 
            id_servicio=servicio.id_servicio,
            fecha_hora_inicio=h_inicio, 
            fecha_hora_fin=h_fin,
            estado_cita="confirmada", 
            precio_cobrado=servicio.precio
        )
        db.add(cita)
        db.commit()
        logger.info(f"   ✅ Cita ID {cita.id_cita} PERSISTIDA en la base de datos.")

        # --- PASO F: RECORDATORIOS AUTOMÁTICOS ---
        logger.info("Paso F: Forzando ejecución del Scheduler...")
        # Forzamos que la cita esté en la ventana de 24h para la prueba
        cita.fecha_hora_inicio = datetime.now(tz).replace(tzinfo=None) + timedelta(hours=24)
        db.commit()
        
        await tarea_recordatorio_24h(bot)
        db.refresh(cita)
        
        if cita.recordatorio_24h_enviado:
            logger.info("   ✅ El Scheduler detectó la cita y marcó recordatorio como enviado.")
        else:
            logger.warning("   ⚠️ El Scheduler no procesó la cita (verificar ventanas de tiempo).")

        # --- PASO G: EXPORTACIÓN ADMINISTRATIVA ---
        logger.info("Paso G: Generando Reporte CSV para el dueño...")
        filepath = exportar_citas_csv(db, id_negocio=id_negocio)
        logger.info(f"   ✅ Reporte generado en: {filepath}")
        
        logger.info("🌟 SIMULACIÓN COMPLETADA EXITOSAMENTE 🌟")

    except Exception as e:
        logger.exception("Fallo en la simulación: %s", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(simular_ciclo_completo())
