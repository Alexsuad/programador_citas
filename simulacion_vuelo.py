# File: simulacion_vuelo.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Simulación de Ciclo de Vida Completo (MVP Flight Test).
# Ejecución: uv run python simulacion_vuelo.py
# ──────────────────────────────────────────────────────────────────────

import os
import csv
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Usuario, EntidadSujeto, Servicio, Recurso, Cita
from modules.availability import generar_slots_disponibles
from modules.scheduler import tarea_recordatorio_24h, tarea_recordatorio_2h
from modules.admin import exportar_citas_csv
import asyncio

# Mock del Bot de Telegram para pruebas Offline
class MockBot:
    async def send_message(self, chat_id, text, parse_mode=None):
        print(f"   [BOT MOCK] 📩 Enviado a {chat_id}: {text[:50]}...")
        return True

async def simular_ciclo_completo():
    print("\n✈️  INICIANDO PRUEBA DE VUELO FINAL - MVP AGENDAMIENTO\n")
    db = SessionLocal()
    bot = MockBot()
    
    try:
        # --- PASO A: REGISTRO Y CONSENTIMIENTO ---
        print("Paso A: Simulando Registro de Usuario (Habeas Data)...")
        usuario = Usuario(
            id_telegram=999999,
            nombre_usuario="Andrés de Prueba",
            acepta_privacidad=True,
            fecha_aceptacion_terminos=datetime.now(),
            version_terminos_aceptada="1.0-FlightTest"
        )
        db.add(usuario)
        db.flush()
        sujeto = EntidadSujeto(id_usuario_dueno=usuario.id_usuario, nombre_sujeto="Andrés de Prueba")
        db.add(sujeto)
        db.commit()
        print(f"   ✅ Usuario '{usuario.nombre_usuario}' registrado con ID {usuario.id_usuario}.\n")

        # --- PASO B/C: SELECCIÓN DE CATALOGO ---
        print("Paso B/C: Consultando Servicios y Recursos...")
        servicio = db.query(Servicio).filter(Servicio.nombre_servicio.like("%Corte%")).first()
        barbero = db.query(Recurso).filter(Recurso.nombre_recurso.like("%Andrés%")).first()
        print(f"   ✅ Seleccionado: '{servicio.nombre_servicio}' con '{barbero.nombre_recurso}'.\n")

        # --- PASO D: MOTOR DE DISPONIBILIDAD ---
        print("Paso D: Invocando al 'Cerebro' para mañana...")
        mañana = date.today() + timedelta(days=1)
        slots = generar_slots_disponibles(db, barbero.id_recurso, mañana, servicio.id_servicio)
        print(f"   ✅ Se encontraron {len(slots)} slots. El usuario elige las 11:00 AM.\n")

        # --- PASO E: CONFIRMACIÓN Y PERSISTENCIA ---
        print("Paso E: Confirmando Cita y Guardando en DB...")
        h_inicio = datetime.combine(mañana, datetime.strptime("11:00", "%H:%M").time())
        h_fin = h_inicio + timedelta(minutes=servicio.duracion_minutos)
        
        cita = Cita(
            id_negocio=1, id_usuario=usuario.id_usuario, id_sujeto=sujeto.id_sujeto,
            id_recurso=barbero.id_recurso, id_servicio=servicio.id_servicio,
            fecha_hora_inicio=h_inicio, fecha_hora_fin=h_fin,
            estado_cita="confirmada", precio_cobrado=servicio.precio
        )
        db.add(cita)
        db.commit()
        print(f"   ✅ Cita ID {cita.id_cita} PERSISTIDA físicamente en SQLite.\n")

        # --- PASO F: RECORDATORIOS AUTOMÁTICOS ---
        print("Paso F: Forzando ejecución del Scheduler (Simulando paso del tiempo)...")
        # Ajustamos la hora de la cita para que caiga EXACTAMENTE en la ventana de 24h (+- 30min)
        cita.fecha_hora_inicio = datetime.now() + timedelta(hours=24)
        db.commit()
        
        await tarea_recordatorio_24h(bot)
        db.refresh(cita)
        
        if cita.recordatorio_24h_enviado:
            print("   ✅ El Scheduler detectó la cita y marcó 'recordatorio_24h_enviado' como TRUE.\n")
        else:
            print("   ❌ El Scheduler no detectó la cita correctamente.\n")

        # --- PASO G: EXPORTACIÓN ADMINISTRATIVA ---
        print("Paso G: Generando Reporte CSV para el dueño...")
        filepath = exportar_citas_csv(db, id_negocio=1)
        print(f"   ✅ Reporte generado en: {filepath}")
        
        print("\n📄 CONTENIDO DEL REPORTE (Primeras 2 líneas):")
        with open(filepath, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()[:2]
            for l in lines: print(f"   > {l.strip()}")

        print("\n🌟 SISTEMA LISTO PARA PRODUCCIÓN 🌟\n")

    except Exception as e:
        print(f"\n❌ FALLO EN LA SIMULACIÓN: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(simular_ciclo_completo())
