# File: database/seeding.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Poblado inicial de datos de prueba para el MVP.
# Rol: Script de utilidad para desarrollo/pruebas.
# ──────────────────────────────────────────────────────────────────────

import logging

from database.connection import SessionLocal
from database.models import Negocio, Recurso, Servicio, HorarioRecurso, RecursoServicio

logger = logging.getLogger(__name__)

def poblar_datos_prueba():
    """Inserta registros base para una barbería de prueba (idempotente)."""
    db = SessionLocal()
    try:
        # 1. Crear o recuperar el Negocio
        barberia = db.query(Negocio).filter(
            Negocio.nombre_comercial == "Barbería Classic Pro"
        ).first()

        if not barberia:
            logger.info("Iniciando proceso de seeding.")
            barberia = Negocio(
                nombre_comercial="Barbería Classic Pro",
                tipo_industria="Barbería",
                configuracion_json={
                    "buffer_time": 15,
                    "moneda": "EUR",
                    "mensaje_bienvenida": "¡Bienvenido a Barbería Classic Pro!",
                    "zona_horaria": "Europe/Madrid",
                    "google_review_url": "https://g.page/r/example/review",
                    "support_contact_url": "https://t.me/soporte_demo"
                }
            )
            db.add(barberia)
            db.flush()
            logger.info(f"✅ Negocio creado: {barberia.nombre_comercial}")
        else:
            logger.info(f"Negocio '{barberia.nombre_comercial}' ya existe, verificando servicios y recursos...")
        
        # 2. Crear o recuperar Recursos (Especialistas)
        recursos_data = [
            {"nombre": "Andrés el Maestro", "perfil": "hombre"},
            {"nombre": "Valentina Style", "perfil": "mujer"},
            {"nombre": "Alex Unisex Pro", "perfil": "unisex"}
        ]
        
        recursos_creados = []
        for r_info in recursos_data:
            recurso = db.query(Recurso).filter(
                Recurso.id_negocio == barberia.id_negocio, 
                Recurso.nombre_recurso == r_info["nombre"]
            ).first()
            if not recurso:
                recurso = Recurso(
                    id_negocio=barberia.id_negocio,
                    nombre_recurso=r_info["nombre"],
                    perfil_recurso=r_info["perfil"],
                    tipo_recurso="Humano",
                    capacidad=1
                )
                db.add(recurso)
                logger.info(f"✅ Recurso creado: {recurso.nombre_recurso}")
            recursos_creados.append(recurso)
        
        db.flush()
        
        # 3. Crear Servicios si no existen
        servicios_data = [
            {"nombre": "Corte Clásico + Lavado", "perfil": "hombre", "duracion": 45, "precio": 15.0},
            {"nombre": "Arreglo de Barba Royale", "perfil": "hombre", "duracion": 30, "precio": 10.0},
            {"nombre": "Corte y Peinado", "perfil": "mujer", "duracion": 90, "precio": 28.0},
            {"nombre": "Lavado Capilar", "perfil": "unisex", "duracion": 20, "precio": 8.0}
        ]
        
        for s_info in servicios_data:
            existente = db.query(Servicio).filter(
                Servicio.id_negocio == barberia.id_negocio,
                Servicio.nombre_servicio == s_info["nombre"]
            ).first()
            if not existente:
                nuevo_s = Servicio(
                    id_negocio=barberia.id_negocio,
                    nombre_servicio=s_info["nombre"],
                    perfil_servicio=s_info["perfil"],
                    duracion_minutos=s_info["duracion"],
                    precio=s_info["precio"]
                )
                db.add(nuevo_s)
                logger.info(f"✅ Servicio creado: {s_info['nombre']}")
        
        db.flush()

        # 4. Crear Horarios si no existen (Lunes a Sábado, 09:00 a 18:00) para cada recurso
        for recurso in recursos_creados:
            for dia in range(6):  # 0 a 5
                existente = db.query(HorarioRecurso).filter(
                    HorarioRecurso.id_recurso == recurso.id_recurso,
                    HorarioRecurso.dia_semana == dia
                ).first()
                if not existente:
                    db.add(HorarioRecurso(
                        id_recurso=recurso.id_recurso,
                        dia_semana=dia,
                        hora_inicio="09:00",
                        hora_fin="18:00"
                    ))
        
        # 5. Crear asignaciones de habilidades si no existen
        andres = next(r for r in recursos_creados if r.nombre_recurso == "Andrés el Maestro")
        valentina = next(r for r in recursos_creados if r.nombre_recurso == "Valentina Style")
        alex_unisex = next(r for r in recursos_creados if r.nombre_recurso == "Alex Unisex Pro")

        servicios = db.query(Servicio).filter(Servicio.id_negocio == barberia.id_negocio).all()
        servicio_corte_hombre = next(s for s in servicios if s.nombre_servicio == "Corte Clásico + Lavado")
        servicio_barba = next(s for s in servicios if s.nombre_servicio == "Arreglo de Barba Royale")
        servicio_corte_mujer = next(s for s in servicios if s.nombre_servicio == "Corte y Peinado")
        servicio_lavado = next(s for s in servicios if s.nombre_servicio == "Lavado Capilar")

        asignaciones_data = [
            (andres.id_recurso, servicio_corte_hombre.id_servicio),
            (andres.id_recurso, servicio_barba.id_servicio),
            (valentina.id_recurso, servicio_corte_mujer.id_servicio),
            (valentina.id_recurso, servicio_lavado.id_servicio),
            (alex_unisex.id_recurso, servicio_corte_hombre.id_servicio),
            (alex_unisex.id_recurso, servicio_corte_mujer.id_servicio),
            (alex_unisex.id_recurso, servicio_lavado.id_servicio),
        ]

        for rid, sid in asignaciones_data:
            existente = db.query(RecursoServicio).filter(
                RecursoServicio.id_recurso == rid,
                RecursoServicio.id_servicio == sid
            ).first()
            if not existente:
                db.add(RecursoServicio(id_recurso=rid, id_servicio=sid))
                logger.info(f"✅ Habilidad asignada: Recurso {rid} -> Servicio {sid}")
        
        db.commit()
        logger.info("Seeding completado exitosamente.")
        
    except Exception as e:
        db.rollback()
        logger.exception("Error durante el seeding: %s", e)
        logger.warning(
            "Verifica que la base de datos esté accesible y que el archivo .env esté configurado correctamente."
        )
    finally:
        db.close()

if __name__ == "__main__":
    poblar_datos_prueba()
