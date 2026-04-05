# File: database/seeding.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Poblado inicial de datos de prueba para el MVP.
# Rol: Script de utilidad para desarrollo/pruebas.
# ──────────────────────────────────────────────────────────────────────

from database.connection import SessionLocal
from database.models import Negocio, Recurso, Servicio, HorarioRecurso
import sys

def poblar_datos_prueba():
    """Inserta registros base para una barbería de prueba."""
    db = SessionLocal()
    try:
        print("🌱 Iniciando proceso de seeding...")
        
        # 1. Crear el Negocio
        barberia = Negocio(
            nombre_comercial="Barbería Classic Pro",
            tipo_industria="Barbería",
            configuracion_json={"buffer_time": 10, "moneda": "USD"}
        )
        db.add(barberia)
        db.flush()  # Para obtener el id_negocio
        
        # 2. Crear el Recurso (Especialista)
        barbero = Recurso(
            id_negocio=barberia.id_negocio,
            nombre_recurso="Andrés el Maestro",
            tipo_recurso="Humano",
            capacidad=1
        )
        db.add(barbero)
        
        # 3. Crear Servicios
        servicios = [
            Servicio(
                id_negocio=barberia.id_negocio,
                nombre_servicio="Corte Clásico + Lavado",
                duracion_minutos=45,
                precio=15.0
            ),
            Servicio(
                id_negocio=barberia.id_negocio,
                nombre_servicio="Arreglo de Barba Royale",
                duracion_minutos=30,
                precio=10.0
            )
        ]
        db.add_all(servicios)
        db.flush()

        # 4. Crear Horarios (Lunes a Sábado, 09:00 a 18:00)
        horarios = []
        for dia in range(6):  # 0 a 5
            horarios.append(HorarioRecurso(
                id_recurso=barbero.id_recurso,
                dia_semana=dia,
                hora_inicio="09:00",
                hora_fin="18:00"
            ))
        db.add_all(horarios)
        
        db.commit()
        print("✅ Seeding completado exitosamente.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el seeding: {str(e)}")
        print("💡 TIP: Asegúrate de que PostgreSQL esté corriendo y el .env configurado.")
    finally:
        db.close()

if __name__ == "__main__":
    poblar_datos_prueba()
