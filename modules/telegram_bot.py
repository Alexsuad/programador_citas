# File: modules/telegram_bot.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Manejo del flujo completo de agendamiento y UI de Telegram.
# Rol: Interfaz de usuario dinámica y control de estados.
# ──────────────────────────────────────────────────────────────────────

import os
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from database.connection import SessionLocal
from database.models import Usuario, Servicio, Recurso, Cita, EntidadSujeto
from modules.availability import generar_slots_disponibles
from typing import Optional

# Definición de Estados del Flujo
ESTADO_CONSENTIMIENTO = 1
ESTADO_MENU_PRINCIPAL = 2
ESTADO_SELECCION_SERVICIO = 3
ESTADO_SELECCION_RECURSO = 4
ESTADO_SELECCION_FECHA = 5
ESTADO_SELECCION_HORA = 6
ESTADO_CONFIRMACION_FINAL = 7

# Aviso de Privacidad Express
AVISO_PRIVACIDAD = (
    "🛡️ *Aviso de Privacidad Express*\n\n"
    "Para procesar tu agendamiento inteligente, necesitamos tratar tus datos "
    "de contacto (Nombre, Teléfono) conforme a nuestra política de Habeas Data.\n\n"
    "Al continuar, aceptas que el negocio gestione tus citas y te envíe recordatorios automáticos."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saludo inicial y solicitud de consentimiento."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 ¡Hola {user.first_name}! Bienvenido al sistema Inteligente de Agendamiento 🚀\n\n"
        f"{AVISO_PRIVACIDAD}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Acepto y quiero agendar", callback_data="acepto")],
            [InlineKeyboardButton("❌ No acepto", callback_data="no_acepto")]
        ])
    )
    return ESTADO_CONSENTIMIENTO

async def manejar_consentimiento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la respuesta del usuario al aviso de privacidad."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "acepto":
        db = SessionLocal()
        try:
            tg_user = query.from_user
            usuario = db.query(Usuario).filter(Usuario.id_telegram == tg_user.id).first()
            if not usuario:
                usuario = Usuario(
                    id_telegram=tg_user.id,
                    nombre_usuario=tg_user.full_name,
                    acepta_privacidad=True,
                    fecha_aceptacion_terminos=datetime.now(),
                    version_terminos_aceptada="1.0-MVP"
                )
                db.add(usuario)
                db.flush()
                # Crear EntidadSujeto por defecto (él mismo)
                sujeto = EntidadSujeto(id_usuario_dueno=usuario.id_usuario, nombre_sujeto=tg_user.full_name)
                db.add(sujeto)
            else:
                usuario.acepta_privacidad = True
            db.commit()
            context.user_data["id_usuario"] = usuario.id_usuario
        finally:
            db.close()
            
        return await mostrar_menu_principal(query)
    else:
        await query.edit_message_text(
            "😔 Sin tu consentimiento no podemos procesar reservas automáticas.\n\n"
            "📞 Llama al: **+57 (Negocio)** para atención manual.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def mostrar_menu_principal(query) -> int:
    """Invoca el menú principal con botones dinámicos."""
    await query.edit_message_text(
        "✨ *Menú Principal*\n\n¿Qué deseas hacer hoy?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Agendar Cita", callback_data="menu_agendar")],
            [InlineKeyboardButton("📋 Mis Citas", callback_data="menu_mis_citas")],
            [InlineKeyboardButton("🙋‍♂️ Ayuda", callback_data="menu_ayuda")]
        ])
    )
    return ESTADO_MENU_PRINCIPAL

# --- ETAPA 4: FLUJO DE AGENDAMIENTO ---

async def mostrar_servicios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Extrae servicios de la DB y genera botones."""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    servicios = db.query(Servicio).filter(Servicio.activo == True).all()
    db.close()
    
    botones = []
    for s in servicios:
        botones.append([InlineKeyboardButton(f"{s.nombre_servicio} - ${s.precio:.2f}", callback_data=f"srv_{s.id_servicio}")])
    
    await query.edit_message_text(
        "💈 *Selecciona el servicio* que deseas:\n(Duración estimada: 30-45 min)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_SERVICIO

async def mostrar_recursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los especialistas/barberos disponibles."""
    query = update.callback_query
    await query.answer()
    
    context.user_data["id_servicio"] = int(query.data.split("_")[1])
    
    db = SessionLocal()
    barberos = db.query(Recurso).all()
    db.close()
    
    botones = []
    for b in barberos:
        botones.append([InlineKeyboardButton(f"👤 {b.nombre_recurso}", callback_data=f"res_{b.id_recurso}")])
    
    await query.edit_message_text(
        "👥 *¿Con quién deseas agendar?*\nSelecciona a tu especialista favorito:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_RECURSO

async def mostrar_fechas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Genera botones para los próximos 3 días hábiles."""
    query = update.callback_query
    await query.answer()
    
    context.user_data["id_recurso"] = int(query.data.split("_")[1])
    
    botones = []
    hoy = date.today()
    for i in range(1, 4):  # Mañana, pasado mañana, etc.
        d = hoy + timedelta(days=i)
        dia_nombre = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
        botones.append([InlineKeyboardButton(f"📅 {dia_nombre} {d.day}/{d.month}", callback_data=f"fec_{d.isoformat()}")])
    
    await query.edit_message_text(
        "🗓️ *¿Cuándo deseas venir?*\nSelecciona una fecha disponible:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_FECHA

async def mostrar_horas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Invoca al CEREBRO para calcular slots reales."""
    query = update.callback_query
    await query.answer()
    
    fecha_str = query.data.split("_")[1]
    fecha_busqueda = date.fromisoformat(fecha_str)
    context.user_data["fecha"] = fecha_busqueda
    
    db = SessionLocal()
    slots = generar_slots_disponibles(
        db, 
        id_recurso=context.user_data["id_recurso"], 
        fecha_busqueda=fecha_busqueda, 
        id_servicio=context.user_data["id_servicio"]
    )
    db.close()
    
    if not slots:
        await query.edit_message_text(
            "⚠️ Lo sentimos, no hay horas disponibles para este día. Por favor elige otra fecha.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Volver a Fechas", callback_data="menu_agendar")]])
        )
        return ESTADO_SELECCION_FECHA

    botones = []
    # Generar botones de 2 en 2 para mejor UX
    row = []
    for s in slots:
        hora_str = s.strftime("%H:%M")
        row.append(InlineKeyboardButton(hora_str, callback_data=f"hor_{hora_str}"))
        if len(row) == 2:
            botones.append(row)
            row = []
    if row: botones.append(row)
    
    await query.edit_message_text(
        f"⏰ *Horas disponibles para el {fecha_busqueda.day}/{fecha_busqueda.month}*:\n"
        "Selecciona el horario que más te convenga:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_HORA

async def mostrar_confirmacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra resumen final antes de grabar en DB."""
    query = update.callback_query
    await query.answer()
    
    hora_str = query.data.split("_")[1]
    context.user_data["hora"] = hora_str
    
    db = SessionLocal()
    servicio = db.query(Servicio).get(context.user_data["id_servicio"])
    barbero = db.query(Recurso).get(context.user_data["id_recurso"])
    db.close()
    
    resumen = (
        "🏁 *RESUMEN DE TU CITA*\n\n"
        f"💈 *Servicio*: {servicio.nombre_servicio}\n"
        f"👤 *Especialista*: {barbero.nombre_recurso}\n"
        f"📅 *Fecha*: {context.user_data['fecha']}\n"
        f"⏰ *Hora*: {hora_str}\n\n"
        "¿Deseas confirmar este agendamiento?"
    )
    
    await query.edit_message_text(
        resumen,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirmar Reserva", callback_data="conf_si")],
            [InlineKeyboardButton("🔄 Reiniciar", callback_data="menu_agendar")]
        ])
    )
    return ESTADO_CONFIRMACION_FINAL

async def finalizar_reserva(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Graba la cita definitiva en la BD."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "conf_si":
        db = SessionLocal()
        try:
            # Obtener datos para el insert
            f_str = f"{context.user_data['fecha']} {context.user_data['hora']}"
            h_inicio = datetime.strptime(f_str, "%Y-%m-%d %H:%M")
            
            # Buscamos el servicio para calcular hora_fin
            servicio = db.query(Servicio).get(context.user_data["id_servicio"])
            h_fin = h_inicio + timedelta(minutes=servicio.duracion_minutos)
            
            # Buscamos el sujeto del usuario (el titular por defecto)
            sujeto = db.query(EntidadSujeto).filter(EntidadSujeto.id_usuario_dueno == context.user_data["id_usuario"]).first()
            
            nueva_cita = Cita(
                id_negocio=1,
                id_usuario=context.user_data["id_usuario"],
                id_sujeto=sujeto.id_sujeto,
                id_recurso=context.user_data["id_recurso"],
                id_servicio=context.user_data["id_servicio"],
                fecha_hora_inicio=h_inicio,
                fecha_hora_fin=h_fin,
                estado_cita="confirmada",
                precio_cobrado=servicio.precio
            )
            db.add(nueva_cita)
            db.commit()
            
            print(f"🎉 Cita creada: ID {nueva_cita.id_cita} para {h_inicio}")
            
            await query.edit_message_text(
                "🎉 ¡Enhorabuena! *Tu cita ha sido confirmada.*\n\n"
                "Te enviaremos un recordatorio 24 horas antes. ¡Te esperamos!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_volver_inicio")]])
            )
        except Exception as e:
            print(f"❌ Error al crear cita: {e}")
            await query.edit_message_text("⚠️ Ocurrió un error al guardar tu cita. Por favor intenta de nuevo.")
        finally:
            db.close()
        
        return ESTADO_MENU_PRINCIPAL
    
    return ESTADO_MENU_PRINCIPAL

# --- COMANDOS Y CONFIGURACIÓN ---

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "❓ *Centro de Ayuda*\n\nCategorías: *Citas*, *Mi Perfil*, *El Negocio*."
    if update.message: await update.message.reply_text(msg, parse_mode="Markdown")
    else: await update.callback_query.message.reply_text(msg, parse_mode="Markdown")

def configurar_bot(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESTADO_CONSENTIMIENTO: [CallbackQueryHandler(manejar_consentimiento)],
            ESTADO_MENU_PRINCIPAL: [
                CallbackQueryHandler(ayuda, pattern="^menu_ayuda$"),
                CallbackQueryHandler(mostrar_servicios, pattern="^menu_agendar$|^menu_volver_inicio$"),
            ],
            ESTADO_SELECCION_SERVICIO: [CallbackQueryHandler(mostrar_recursos, pattern="^srv_")],
            ESTADO_SELECCION_RECURSO: [CallbackQueryHandler(mostrar_fechas, pattern="^res_")],
            ESTADO_SELECCION_FECHA: [
                CallbackQueryHandler(mostrar_horas, pattern="^fec_"),
                CallbackQueryHandler(mostrar_servicios, pattern="^menu_agendar$"),
            ],
            ESTADO_SELECCION_HORA: [CallbackQueryHandler(mostrar_confirmacion, pattern="^hor_")],
            ESTADO_CONFIRMACION_FINAL: [
                CallbackQueryHandler(finalizar_reserva, pattern="^conf_si$"),
                CallbackQueryHandler(mostrar_servicios, pattern="^menu_agendar$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("ayuda", ayuda))
