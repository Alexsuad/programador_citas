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
from database.models import Usuario, Servicio, Recurso, Cita, EntidadSujeto, DiaNoDisponible
from modules.availability import generar_slots_disponibles
from modules import admin  # Importación del módulo administrativo
from typing import Optional, List
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

# Definición de Estados del Flujo
ESTADO_CONSENTIMIENTO = 1
ESTADO_MENU_PRINCIPAL = 2
ESTADO_SELECCION_SERVICIO = 3
ESTADO_SELECCION_RECURSO = 4
ESTADO_SELECCION_FECHA = 5
ESTADO_SELECCION_HORA = 6
ESTADO_CONFIRMACION_FINAL = 7
ESTADO_ADMIN_BLOQUEO = 8
ESTADO_ADMIN_SERVICIOS = 9

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
                    fecha_aceptacion_terminos=datetime.now(ZoneInfo("America/Bogota")),
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
            [InlineKeyboardButton("🛡️ Mis Datos (Privacidad)", callback_data="menu_privacidad")],
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
    
    db = SessionLocal()
    servicio = db.get(Servicio, int(query.data.split("_")[1]))
    db.close()
    
    if not servicio:
        return ESTADO_MENU_PRINCIPAL

    context.user_data["id_servicio"] = servicio.id_servicio
    context.user_data["id_negocio"] = servicio.id_negocio
    
    db = SessionLocal()
    barberos = db.query(Recurso).filter(
        Recurso.id_negocio == context.user_data["id_negocio"]
    ).all()
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
    try:
        slots = generar_slots_disponibles(
            db, 
            id_recurso=context.user_data["id_recurso"], 
            fecha_busqueda=fecha_busqueda, 
            id_servicio=context.user_data["id_servicio"]
        )
    finally:
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
    servicio = db.get(Servicio, context.user_data["id_servicio"])
    barbero = db.get(Recurso, context.user_data["id_recurso"])
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
            # 1. Validación de "Último Segundo" (Prevenir Race Condition)
            slots_frescos = generar_slots_disponibles(
                db, 
                id_recurso=context.user_data["id_recurso"], 
                fecha_busqueda=context.user_data["fecha"], 
                id_servicio=context.user_data["id_servicio"]
            )
            
            # Formatear el inicio de nuestra cita para comparar
            f_str_temp = f"{context.user_data['fecha']} {context.user_data['hora']}"
            h_inicio_valid = datetime.strptime(f_str_temp, "%Y-%m-%d %H:%M")
            
            if h_inicio_valid not in slots_frescos:
                await query.edit_message_text(
                    "⚠️ *¡Vaya! Alguien fue más rápido.*\n\n"
                    "El slot que seleccionaste acaba de ser ocupado. Por favor, selecciona otro.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Ver otros horarios", callback_data="menu_agendar")]])
                )
                return ESTADO_MENU_PRINCIPAL

            # 2. Grabación Definitiva
            f_str = f"{context.user_data['fecha']} {context.user_data['hora']}"
            h_inicio = h_inicio_valid
            
            # Buscamos el servicio para calcular hora_fin
            servicio = db.get(Servicio, context.user_data["id_servicio"])
            h_fin = h_inicio + timedelta(minutes=servicio.duracion_minutos)
            
            # Buscamos el sujeto del usuario (el titular por defecto)
            sujeto = db.query(EntidadSujeto).filter(EntidadSujeto.id_usuario_dueno == context.user_data["id_usuario"]).first()
            
            # 3. Validación de milisegundo (Check-then-Act) en base de datos
            solapamiento = db.query(Cita).filter(
                Cita.id_recurso == context.user_data["id_recurso"],
                Cita.estado_cita == "confirmada",
                Cita.fecha_hora_inicio < h_fin,
                Cita.fecha_hora_fin > h_inicio
            ).first()
            
            if solapamiento:
                db.rollback()
                await query.edit_message_text(
                    "⚠️ *¡Vaya! Alguien fue un milisegundo más rápido.*\n\n"
                    "El slot que seleccionaste acaba de ser ocupado. Por favor, selecciona otro.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Ver otros horarios", callback_data="menu_agendar")]])
                )
                return ESTADO_MENU_PRINCIPAL
                
            nueva_cita = Cita(
                id_negocio=servicio.id_negocio,
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
            
            logger.info(f"🎉 Cita creada: ID {nueva_cita.id_cita} para {h_inicio}")
            
            await query.edit_message_text(
                "🎉 ¡Enhorabuena! *Tu cita ha sido confirmada.*\n\n"
                "Te enviaremos un recordatorio 24 horas antes. ¡Te esperamos!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_volver_inicio")]])
            )
        except Exception as e:
            logger.error(f"❌ Error al crear cita: {e}")
            await query.edit_message_text("⚠️ Ocurrió un error al guardar tu cita. Por favor intenta de nuevo.")
        finally:
            db.close()
        
        return ESTADO_MENU_PRINCIPAL
    
    return ESTADO_MENU_PRINCIPAL

# --- INTERFAZ ADMINISTRATIVA ---

def es_admin(user_id: int) -> bool:
    """Verifica si un ID de Telegram tiene permisos de administrador."""
    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = [int(i.strip()) for i in admin_ids_raw.split(",") if i.strip().isdigit()]
    return user_id in admin_ids

async def menu_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el panel de control para administradores."""
    if not es_admin(update.effective_user.id): return

    msg = "🛠️ *Panel de Administración*\n\nBienvenido al panel de control. ¿Qué necesitas hoy?"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✂️ Gestionar Servicios", callback_data="admin_servicios")],
        [InlineKeyboardButton("🚫 Bloquear Día (Festivo)", callback_data="admin_bloqueo")],
        [InlineKeyboardButton("📊 Exportar Citas (CSV)", callback_data="admin_exportar_csv")]
    ])
    
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)

async def admin_gestionar_servicios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra lista de servicios para activar/desactivar."""
    if not es_admin(update.effective_user.id): return
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    servicios = db.query(Servicio).all()
    db.close()
    
    botones = []
    for s in servicios:
        status = "✅" if s.activo else "❌"
        botones.append([InlineKeyboardButton(f"{status} {s.nombre_servicio}", callback_data=f"adm_srv_tog_{s.id_servicio}")])
    
    botones.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver")])
    
    await query.edit_message_text(
        "✂️ *Gestión de Catálogo*\nPresiona un servicio para cambiar su disponibilidad:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_ADMIN_SERVICIOS

async def admin_toggle_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cambia el estado activo/inactivo de un servicio."""
    if not es_admin(update.effective_user.id): return
    query = update.callback_query
    await query.answer()
    
    id_srv = int(query.data.split("_")[-1])
    db = SessionLocal()
    try:
        srv = db.get(Servicio, id_srv)
        if srv:
            srv.activo = not srv.activo
            db.commit()
    finally:
        db.close()
    
    return await admin_gestionar_servicios(update, context)

async def admin_solicitar_bloqueo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pide al admin la fecha para bloquear."""
    if not es_admin(update.effective_user.id): return
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🚫 *Bloqueo de Día*\nPor favor, escribe la fecha que deseas bloquear en formato: `YYYY-MM-DD` (ej: 2024-12-25)\n\n"
        "*(Escribe 'cancelar' para abortar)*",
        parse_mode="Markdown"
    )
    return ESTADO_ADMIN_BLOQUEO

async def admin_confirmar_bloqueo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda el bloqueo en la DB."""
    if not es_admin(update.effective_user.id): return
    texto = update.message.text
    if texto.lower() == "cancelar":
        await update.message.reply_text("❌ Bloqueo cancelado.")
        return ConversationHandler.END

    try:
        fecha = datetime.strptime(texto, "%Y-%m-%d").date()
        db = SessionLocal()
        # Verificar si ya existe
        existente = db.query(DiaNoDisponible).filter(DiaNoDisponible.fecha == fecha).first()
        if not existente:
            bloqueo = DiaNoDisponible(fecha=fecha, motivo="Bloqueo Manual Admin")
            db.add(bloqueo)
            db.commit()
            await update.message.reply_text(f"✅ Día {fecha} bloqueado exitosamente.")
        else:
            await update.message.reply_text(f"⚠️ El día {fecha} ya estaba bloqueado.")
        db.close()
    except ValueError:
        await update.message.reply_text("❌ Formato de fecha inválido. Usa `YYYY-MM-DD`.")
        return ESTADO_ADMIN_BLOQUEO
    
    return ConversationHandler.END

# --- COMANDO MI PRIVACIDAD ---

async def menu_privacidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra los datos del usuario y opción de eliminación (Habeas Data)."""
    user_tg_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(Usuario).filter(Usuario.id_telegram == user_tg_id).first()
    db.close()

    if not user:
        return

    msg = (
        "🛡️ *Consulta de tus Datos (Habeas Data)*\n\n"
        "Tus datos están protegidos bajo nuestras políticas de privacidad.\n\n"
        f"👤 *Nombre*: {user.nombre_usuario}\n"
        f"📱 *Telegram ID*: {user.id_telegram}\n"
        f"✔️ *Consentimiento*: Aceptado el {user.fecha_aceptacion_terminos.strftime('%d/%m/%Y')}\n\n"
        "Bajo las leyes de protección de datos, tienes derecho a solicitar la eliminación de tu información."
    )
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Solicitar Eliminación de Datos", callback_data="priv_eliminar")],
        [InlineKeyboardButton("🏠 Menú Principal", callback_data="menu_volver_inicio")]
    ])

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.callback_query.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)

# --- COMANDOS Y CONFIGURACIÓN ---

async def ejecutar_eliminacion_privacidad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina o anonimiza los datos del usuario para cumplir con Habeas Data."""
    query = update.callback_query
    await query.answer()
    
    user_tg_id = update.effective_user.id
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id_telegram == user_tg_id).first()
        if usuario:
            usuario.nombre_usuario = "Usuario Eliminado"
            usuario.telefono = None
            usuario.correo_electronico = None
            usuario.acepta_privacidad = False
            db.commit()
            await query.edit_message_text("✅ Tus datos personales han sido anonimizados con éxito, cumpliendo con la política de Habeas Data.\nYa no recibirás comunicaciones nuestras.")
        else:
            await query.edit_message_text("⚠️ No encontramos datos asociados a tu usuario.")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error al eliminar privacidad: {e}")
        await query.edit_message_text("❌ Hubo un error al procesar la solicitud.")
    finally:
        db.close()
    
    return ConversationHandler.END

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú de categorías de ayuda con botones."""
    msg = (
        "❓ *Centro de Ayuda*\n\n"
        "Selecciona una categoría para obtener más información:"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Sobre mis Citas", callback_data="ayu_citas")],
        [InlineKeyboardButton("🛡️ Sobre mis Datos", callback_data="ayu_datos")],
        [InlineKeyboardButton("💈 Sobre el Negocio", callback_data="ayu_negocio")]
    ])
    
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.callback_query.message.edit_text(msg, parse_mode="Markdown", reply_markup=markup)

async def manejar_admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Genera y envía el reporte CSV al administrador."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not es_admin(user_id):
        await query.answer("⛔ No autorizado", show_alert=True)
        return

    await query.answer("⌛ Generando reporte...")
    db = SessionLocal()
    try:
        # Resolvemos hardcoding obteniendo el primer negocio o pasando dinámicamente si hay sesión
        negocio_export = db.query(Negocio).first()
        id_negocio_csv = negocio_export.id_negocio if negocio_export else 1
        filepath = admin.exportar_citas_csv(db, id_negocio=id_negocio_csv)
        
        # Enviar el archivo
        with open(filepath, "rb") as f:
            await query.message.reply_document(
                document=f,
                filename=os.path.basename(filepath),
                caption="📈 Aquí tienes el historial completo de citas actualizado."
            )
        
        # Limpieza (opcional: borrar el archivo local tras envío para seguridad)
        os.remove(filepath)
        
    except Exception as e:
        logger.error(f"❌ Error en exportación admin: {e}")
        await query.message.reply_text("⚠️ Error técnico al generar el reporte.")
    finally:
        db.close()


def configurar_bot(application: Application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESTADO_CONSENTIMIENTO: [CallbackQueryHandler(manejar_consentimiento)],
            ESTADO_MENU_PRINCIPAL: [
                CallbackQueryHandler(ayuda, pattern="^menu_ayuda$"),
                CallbackQueryHandler(mostrar_servicios, pattern="^menu_agendar$|^menu_volver_inicio$"),
                CallbackQueryHandler(menu_privacidad, pattern="^menu_privacidad$"),
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
            ESTADO_ADMIN_SERVICIOS: [
                CallbackQueryHandler(admin_toggle_servicio, pattern="^adm_srv_tog_"),
                CallbackQueryHandler(menu_admin, pattern="^admin_volver$"),
            ],
            ESTADO_ADMIN_BLOQUEO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirmar_bloqueo)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("admin", menu_admin))
    application.add_handler(CommandHandler("mi_privacidad", menu_privacidad))
    application.add_handler(CallbackQueryHandler(manejar_admin_export, pattern="^admin_exportar_csv$"))
    application.add_handler(CallbackQueryHandler(admin_gestionar_servicios, pattern="^admin_servicios$"))
    application.add_handler(CallbackQueryHandler(admin_solicitar_bloqueo, pattern="^admin_bloqueo$"))
    application.add_handler(CallbackQueryHandler(menu_admin, pattern="^admin_volver$"))
    application.add_handler(CallbackQueryHandler(ejecutar_eliminacion_privacidad, pattern="^priv_eliminar$"))
