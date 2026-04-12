import logging
from database.connection import SessionLocal
from database.models import Cita, Usuario, EntidadSujeto, Negocio
from modules.availability import generar_slots_disponibles
from datetime import date, timedelta, datetime

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def realizar_prueba():
    db = SessionLocal()
    try:
        # 0. Obtener negocio y recurso base
        negocio = db.query(Negocio).first()
        if not negocio:
            logger.error("❌ No hay negocios. Corre el seeding primero.")
            return
        
        id_negocio = negocio.id_negocio
        # Asumimos que el recurso 1 existe por el seeding, o lo buscamos
        recurso = negocio.recursos[0] if negocio.recursos else None
        servicio = negocio.servicios[0] if negocio.servicios else None
        
        if not recurso or not servicio:
            logger.error("❌ No hay recursos o servicios para el negocio.")
            return

        # 1. Definir fecha de prueba (Mañana)
        manana = date.today() + timedelta(days=1)
        
        logger.info(f"🚀 INICIANDO PRUEBA DE SOLAPAMIENTO para {negocio.nombre_comercial}")
        
        # 2. Asegurar que existe un Usuario y un Sujeto para la cita
        usuario = db.query(Usuario).first()
        if not usuario:
            usuario = Usuario(id_telegram=12345, nombre_usuario="Cliente Prueba", acepta_privacidad=True)
            db.add(usuario)
            db.flush()
            
        sujeto = db.query(EntidadSujeto).filter(EntidadSujeto.id_usuario_dueno == usuario.id_usuario).first()
        if not sujeto:
            sujeto = EntidadSujeto(id_usuario_dueno=usuario.id_usuario, nombre_sujeto="Paco (Perro)")
            db.add(sujeto)
            db.flush()

        # 3. Insertar una cita REAL a las 10:00 AM de 30 minutos
        h_inicio = datetime.combine(manana, datetime.strptime("10:00", "%H:%M").time())
        h_fin = h_inicio + timedelta(minutes=30)
        
        id_negocio = 1 # O usar recurso.id_negocio si se desea

        # Primero limpiamos citas previas de prueba para este día y recurso
        db.query(Cita).filter(
            Cita.id_recurso == recurso.id_recurso, 
            Cita.fecha_hora_inicio == h_inicio
        ).delete()
        
        cita_prueba = Cita(
            id_negocio=id_negocio, 
            id_usuario=usuario.id_usuario, 
            id_sujeto=sujeto.id_sujeto,
            id_recurso=recurso.id_recurso, 
            id_servicio=servicio.id_servicio,
            fecha_hora_inicio=h_inicio, 
            fecha_hora_fin=h_fin,
            estado_cita="confirmada"
        )
        db.add(cita_prueba)
        db.commit()
        logger.info(f"✅ Cita de prueba insertada: {h_inicio.strftime('%H:%M')} - {h_fin.strftime('%H:%M')}")

        # 4. Generar slots y verificar
        slots = generar_slots_disponibles(db, id_recurso=recurso.id_recurso, fecha_busqueda=manana, id_servicio=servicio.id_servicio)
        
        logger.info(f"📊 Resultados del Motor para el {manana}:")
        logger.info(f"   (Filtro esperado: 10:00 AM no debe aparecer)")
        
        encontrado_10am = False
        for slot in slots:
            h_str = slot.strftime('%H:%M')
            # logger.info(f"   🕒 {h_str}")
            if h_str == "10:00":
                encontrado_10am = True
        
        if not encontrado_10am:
            logger.info("✨ ¡ÉXITO! El motor eliminó correctamente el slot de las 10:00 AM.")
        else:
            logger.error("❌ ERROR: El slot de las 10:00 AM sigue disponible.")

    except Exception as e:
        logger.error(f"❌ Error en la prueba: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    realizar_prueba()
