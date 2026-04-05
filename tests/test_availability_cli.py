# File: tests/test_availability_cli.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Verificación del solapamiento con citas reales y buffer.
# Ejecución: uv run python -m tests.test_availability_cli
# ──────────────────────────────────────────────────────────────────────

from database.connection import SessionLocal
from database.models import Cita, Usuario, EntidadSujeto
from modules.availability import generar_slots_disponibles
from datetime import date, timedelta, datetime
import sys

def realizar_prueba():
    db = SessionLocal()
    try:
        # 1. Definir fecha de prueba (Mañana)
        mañana = date.today() + timedelta(days=1)
        # Andrés (ID 1) y Corte (ID 1 - 45min)
        id_recurso = 1
        id_servicio = 1
        
        print("\n🚀 INICIANDO PRUEBA DE SOLAPAMIENTO")
        
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
        h_inicio = datetime.combine(mañana, datetime.strptime("10:00", "%H:%M").time())
        h_fin = h_inicio + timedelta(minutes=30)
        
        # Primero limpiamos citas previas de prueba para este día
        db.query(Cita).filter(Cita.id_recurso == id_recurso, Cita.fecha_hora_inicio == h_inicio).delete()
        
        cita_prueba = Cita(
            id_negocio=1, id_usuario=usuario.id_usuario, id_sujeto=sujeto.id_sujeto,
            id_recurso=id_recurso, id_servicio=id_servicio,
            fecha_hora_inicio=h_inicio, fecha_hora_fin=h_fin,
            estado_cita="confirmada"
        )
        db.add(cita_prueba)
        db.commit()
        print(f"✅ Cita de prueba insertada: {h_inicio.strftime('%H:%M')} - {h_fin.strftime('%H:%M')}")

        # 4. Generar slots y verificar
        slots = generar_slots_disponibles(db, id_recurso=id_recurso, fecha_busqueda=mañana, id_servicio=id_servicio)
        
        print(f"📊 Resultados del Motor para el {mañana}:")
        print(f"   (Filtro esperado: 10:00 AM no debe aparecer)")
        
        encontrado_10am = False
        for slot in slots:
            print(f"   🕒 {slot.strftime('%H:%M')}")
            if slot.strftime('%H:%M') == "10:00":
                encontrado_10am = True
        
        if not encontrado_10am:
            print(f"\n✨ ¡ÉXITO! El motor eliminó correctamente el slot de las 10:00 AM.")
        else:
            print(f"\n❌ ERROR: El slot de las 10:00 AM sigue disponible.")

    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    realizar_prueba()
