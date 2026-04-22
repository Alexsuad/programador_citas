# File: modules/telegram_bot.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Manejo del flujo completo de agendamiento y UI de Telegram.
# Rol: Interfaz de usuario dinámica y control de estados.
# ──────────────────────────────────────────────────────────────────────

import logging
import os
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from database.connection import SessionLocal
from database.models import Usuario, Servicio, Recurso, Cita, EntidadSujeto, DiaNoDisponible
from database import crud
from modules.availability import generar_slots_disponibles
from modules.notifications import enviar_reactivacion_no_asistencia
from modules import admin  # Importación del módulo administrativo
from typing import List
from sqlalchemy import and_, select
from zoneinfo import ZoneInfo
logger = logging.getLogger(__name__)

def obtener_id_negocio_activo() -> int:
    """
    Retorna el negocio activo del MVP.
    Por ahora usa el primer negocio disponible en base de datos.
    Más adelante se reemplazará por una resolución dinámica por bot, canal o tenant.
    """
    db = SessionLocal()
    try:
        negocio = db.query(Recurso.id_negocio).first()
        if not negocio:
            raise ValueError("No existe ningún negocio configurado en la base de datos.")
        return negocio[0]
    finally:
        db.close()

def limpiar_contexto_reserva(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Limpia las claves del contexto relacionadas con el flujo de reserva
    para evitar arrastre de estados entre sesiones o caminos distintos.
    """
    claves_reserva = {
        "perfil_servicio",
        "id_servicio",
        "modo_busqueda",
        "id_recurso",
        "fecha",
        "hora",
        "jornada",
        "seleccion_automatica",
    }

    for clave in claves_reserva:
        context.user_data.pop(clave, None)

def formatear_ranking(titulo: str, filas: list, campo_valor: str, sufijo: str = "") -> str:
    """
    Construye un bloque de texto simple para rankings administrativos.
    """
    if not filas:
        return f"{titulo}\nSin datos disponibles.\n"

    lineas = [titulo]
    for indice, fila in enumerate(filas, start=1):
        nombre = fila.get("nombre", "Sin nombre")
        valor = fila.get(campo_valor, 0)
        lineas.append(f"{indice}. {nombre} — {valor}{sufijo}")

    return "\n".join(lineas) + "\n"

def formatear_lista_servicios(servicios: list) -> str:
    """
    Convierte una lista de servicios en texto legible.
    """
    if not servicios:
        return "Sin servicios."

    return "\n".join(f"• {servicio.nombre_servicio}" for servicio in servicios)

def es_admin(id_telegram: int) -> bool:
    """
    Validación administrativa simple para el MVP.
    Lee los IDs permitidos desde la variable de entorno ADMIN_TELEGRAM_IDS.
    Formato esperado: "12345,67890"
    """
    import os

    raw_ids = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
    if not raw_ids:
        # Intentamos también con ADMIN_IDS por compatibilidad
        raw_ids = os.getenv("ADMIN_IDS", "").strip()
        if not raw_ids:
            return False

    ids_permitidos = {
        int(valor.strip())
        for valor in raw_ids.split(",")
        if valor.strip().isdigit()
    }

    return id_telegram in ids_permitidos

# Definición de Estados del Flujo
ESTADO_CONSENTIMIENTO = 1
ESTADO_MENU_PRINCIPAL = 2
ESTADO_SELECCION_PERFIL = 3
ESTADO_SELECCION_SERVICIO = 4
ESTADO_MODO_BUSQUEDA = 5
ESTADO_SELECCION_RECURSO = 6
ESTADO_SELECCION_FECHA = 7
ESTADO_SELECCION_JORNADA = 8
ESTADO_SELECCION_HORA = 9
ESTADO_SELECCION_RECURSO_POR_HORA = 10
ESTADO_CONFIRMACION_FINAL = 11
ESTADO_CIERRES_PENDIENTES = 12
ESTADO_CONFIRMAR_CIERRE = 13
ESTADO_REACTIVACION_NO_ASISTIO = 14
ESTADO_CALIFICACION_POST_CITA = 15
ESTADO_PERIODICIDAD_POST_CITA = 16
ESTADO_RECORDATORIO_REAGENDAMIENTO = 17
ESTADO_HABILIDADES_RECURSO = 18
ESTADO_HABILIDADES_ACCION = 19
ESTADO_EDITAR_BIENVENIDA = 20
ESTADO_ADMIN_BLOQUEO = 21
ESTADO_ADMIN_SERVICIOS = 22

# Aviso de Privacidad Express
AVISO_PRIVACIDAD = (
    "🛡️ *Aviso de Privacidad Express*\n\n"
    "Para procesar tu agendamiento inteligente, necesitamos tratar tus datos "
    "de contacto (Nombre, Teléfono) conforme a nuestra política de Habeas Data.\n\n"
    "En cumplimiento de la Ley 1581 de 2012 (Colombia) y el GDPR, "
    "tus datos serán usados exclusivamente para la gestión de citas."
)

MENSAJE_REACTIVACION_NO_ASISTIO = (
    "😔 *No pudimos verte hoy*\n\n"
    "Notamos que no pudiste asistir a tu cita.\n\n"
    "¿Te gustaría agendar una nueva fecha ahora mismo?"
)

MENSAJE_RECORDATORIO_REAGENDAMIENTO = (
    "📅 *Ya va siendo hora de tu próxima cita*\n\n"
    "Te escribimos para recordarte que puedes reservar nuevamente cuando quieras."
)

MENSAJE_SOLICITUD_CALIFICACION = (
    "✨ *Gracias por visitarnos*\n\n"
    "¿Cómo calificarías tu experiencia de hoy?"
)

MENSAJE_SOLICITUD_PERIODICIDAD = (
    "🔁 *¿Quieres que te lo recordemos?*\n\n"
    "Si quieres, podemos avisarte para tu próxima cita."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saludo inicial y solicitud de consentimiento."""
    user = update.effective_user
    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        mensaje_bienvenida = crud.obtener_mensaje_bienvenida(db, id_negocio)
    finally:
        db.close()

    await update.message.reply_text(
        f"{mensaje_bienvenida}\n\n{AVISO_PRIVACIDAD}",
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
                    fecha_aceptacion_terminos=datetime.now(ZoneInfo("Europe/Madrid")),
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
            context.user_data["id_negocio"] = obtener_id_negocio_activo()
        finally:
            db.close()
            
        return await mostrar_menu_principal(query)
    else:
        await query.edit_message_text(
            "😔 Sin tu consentimiento no podemos procesar reservas automáticas.\n\n"
            "📞 Contacta directamente al negocio para atención manual.",
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

async def mostrar_perfiles_servicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Primer filtro funcional del servicio.
    Permite saber para quién es el servicio antes de mostrar el catálogo.
    """
    query = update.callback_query
    await query.answer()

    limpiar_contexto_reserva(context)

    await query.edit_message_text(
        "👤 *Antes de continuar*, indícanos:\n\n"
        "¿El servicio es para un hombre o una mujer?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👨 Hombre", callback_data="perfil_hombre")],
            [InlineKeyboardButton("👩 Mujer", callback_data="perfil_mujer")],
            [InlineKeyboardButton("🔄 Me da igual / Unisex", callback_data="perfil_unisex")],
        ])
    )
    return ESTADO_SELECCION_PERFIL

async def mostrar_servicios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Extrae servicios válidos para el negocio y el perfil seleccionado.
    """
    query = update.callback_query
    await query.answer()

    perfil_callback = query.data
    perfil_servicio = perfil_callback.replace("perfil_", "")
    context.user_data["perfil_servicio"] = perfil_servicio

    db = SessionLocal()
    try:
        id_negocio = context.user_data.get("id_negocio")

        if perfil_servicio == "unisex":
            servicios = db.query(Servicio).filter(
                Servicio.id_negocio == id_negocio,
                Servicio.activo == True
            ).all()
        else:
            servicios = db.query(Servicio).filter(
                Servicio.id_negocio == id_negocio,
                Servicio.activo == True,
                Servicio.perfil_servicio.in_([perfil_servicio, "unisex"])
            ).all()
    finally:
        db.close()

    if not servicios:
        await query.edit_message_text(
            "⚠️ No hay servicios disponibles para la selección realizada."
        )
        return ESTADO_MENU_PRINCIPAL

    botones = []
    for s in servicios:
        botones.append([InlineKeyboardButton(f"{s.nombre_servicio} - ${s.precio:.2f}", callback_data=f"srv_{s.id_servicio}")])
    
    await query.edit_message_text(
        "💈 *Selecciona el servicio* que deseas:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_SERVICIO

async def mostrar_modo_busqueda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Permite al usuario decidir si quiere elegir especialista
    o si prefiere buscar por horario disponible.
    """
    query = update.callback_query
    await query.answer()

    context.user_data["id_servicio"] = int(query.data.split("_")[1])

    await query.edit_message_text(
        "🔎 *¿Cómo prefieres buscar tu cita?*\n\n"
        "Puedes elegir un especialista específico o buscar primero por horario.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Elegir especialista", callback_data="modo_especialista")],
            [InlineKeyboardButton("⏰ Buscar por horario", callback_data="modo_horario")],
        ])
    )
    return ESTADO_MODO_BUSQUEDA

async def redirigir_a_especialistas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Activa la ruta clásica de selección por especialista.
    """
    query = update.callback_query
    context.user_data["modo_busqueda"] = "especialista"
    # No respondemos answer acá porque ya se respondió en mostrar_modo_busqueda o se responderá en mostrar_recursos
    return await mostrar_recursos(update, context)

async def redirigir_a_fechas_por_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Activa la ruta de búsqueda por horario.
    En esta primera versión, el usuario escoge fecha antes de ver horas generales.
    """
    query = update.callback_query
    await query.answer()

    context.user_data["modo_busqueda"] = "horario"

    botones = []
    hoy = date.today()
    for i in range(1, 4):
        d = hoy + timedelta(days=i)
        dia_nombre = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()]
        botones.append([
            InlineKeyboardButton(
                f"📅 {dia_nombre} {d.day}/{d.month}",
                callback_data=f"fec_hor_{d.isoformat()}"
            )
        ])

    await query.edit_message_text(
        "🗓️ *¿Qué día prefieres?*\nSelecciona una fecha para buscar horarios disponibles:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_FECHA

async def mostrar_jornadas_por_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Después de elegir una fecha en modo horario, el usuario selecciona
    si quiere ver horarios de mañana o de tarde.
    """
    query = update.callback_query
    await query.answer()

    fecha_str = query.data.replace("fec_hor_", "")
    fecha_busqueda = date.fromisoformat(fecha_str)
    context.user_data["fecha"] = fecha_busqueda

    await query.edit_message_text(
        f"🕓 *¿Qué jornada prefieres para el {fecha_busqueda.day}/{fecha_busqueda.month}?*\n\n"
        "Selecciona una opción para ver horarios disponibles.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌅 Mañana", callback_data="jor_manana")],
            [InlineKeyboardButton("🌇 Tarde", callback_data="jor_tarde")],
        ])
    )
    return ESTADO_SELECCION_JORNADA

async def mostrar_horas_por_horario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra horas disponibles de forma general para todos los recursos
    del negocio, según el servicio seleccionado y la jornada elegida.
    """
    query = update.callback_query
    await query.answer()

    jornada_callback = query.data.replace("jor_", "")
    context.user_data["jornada"] = jornada_callback

    fecha_busqueda = context.user_data.get("fecha")

    db = SessionLocal()
    try:
        id_negocio = context.user_data.get("id_negocio")
        id_servicio = context.user_data.get("id_servicio")
        perfil_servicio = context.user_data.get("perfil_servicio", "unisex")

        recursos = crud.obtener_recursos_habilitados_para_servicio(
            db=db,
            id_negocio=id_negocio,
            id_servicio=id_servicio,
            perfil_servicio=perfil_servicio
        )

        horas_disponibles = set()

        for recurso in recursos:
            slots = generar_slots_disponibles(
                db=db,
                id_recurso=recurso.id_recurso,
                fecha_busqueda=fecha_busqueda,
                id_servicio=id_servicio
            )
            for slot in slots:
                hora_slot = slot.time()

                if jornada_callback == "manana" and hora_slot.hour < 14:
                    horas_disponibles.add(slot.strftime("%H:%M"))

                elif jornada_callback == "tarde" and hora_slot.hour >= 14:
                    horas_disponibles.add(slot.strftime("%H:%M"))

        horas_ordenadas = sorted(horas_disponibles)

    finally:
        db.close()

    if not horas_ordenadas:
        jornada_legible = "mañana" if jornada_callback == "manana" else "tarde"
        await query.edit_message_text(
            f"⚠️ No hay horarios disponibles para la jornada de {jornada_legible}."
        )
        return ESTADO_MENU_PRINCIPAL

    botones = [
        [InlineKeyboardButton("⚡ Ver primera cita disponible", callback_data="hor_gen_primera")]
    ]

    fila = []
    for hora in horas_ordenadas:
        fila.append(InlineKeyboardButton(hora, callback_data=f"hor_gen_{hora}"))
        if len(fila) == 2:
            botones.append(fila)
            fila = []
    if fila:
        botones.append(fila)

    jornada_legible = "mañana" if jornada_callback == "manana" else "tarde"

    await query.edit_message_text(
        f"⏰ *Horarios disponibles para el {fecha_busqueda.day}/{fecha_busqueda.month} en la jornada de {jornada_legible}*:\n"
        "Selecciona una hora para ver qué especialistas están disponibles.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_HORA

async def mostrar_recursos_por_hora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Dada una hora elegida en modo horario, muestra qué especialistas
    tienen ese slot disponible.
    """
    query = update.callback_query
    await query.answer()

    hora_str = query.data.replace("hor_gen_", "")
    context.user_data["hora"] = hora_str
    context.user_data["seleccion_automatica"] = False

    db = SessionLocal()
    try:
        id_negocio = context.user_data.get("id_negocio")
        id_servicio = context.user_data.get("id_servicio")
        fecha_busqueda = context.user_data.get("fecha")
        perfil_servicio = context.user_data.get("perfil_servicio", "unisex")

        if not id_negocio or not id_servicio:
            await query.edit_message_text("⚠️ Faltan datos en el flujo. Regresando al menú...")
            return ESTADO_MENU_PRINCIPAL

        recursos = crud.obtener_recursos_habilitados_para_servicio(
            db=db,
            id_negocio=id_negocio,
            id_servicio=id_servicio,
            perfil_servicio=perfil_servicio
        )

        recursos_disponibles = []

        for recurso in recursos:
            slots = generar_slots_disponibles(
                db=db,
                id_recurso=recurso.id_recurso,
                fecha_busqueda=fecha_busqueda,
                id_servicio=id_servicio
            )
            if any(slot.strftime("%H:%M") == hora_str for slot in slots):
                recursos_disponibles.append(recurso)

    finally:
        db.close()

    if not recursos_disponibles:
        await query.edit_message_text(
            "⚠️ Ya no hay especialistas disponibles para esa hora. Por favor elige otra."
        )
        return ESTADO_SELECCION_HORA

    botones = []
    for recurso in recursos_disponibles:
        botones.append([
            InlineKeyboardButton(
                f"👤 {recurso.nombre_recurso}",
                callback_data=f"res_hor_{recurso.id_recurso}"
            )
        ])

    await query.edit_message_text(
        f"👥 *Especialistas disponibles a las {hora_str}*:\n"
        "Selecciona con quién deseas reservar.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_SELECCION_RECURSO_POR_HORA

async def seleccionar_primera_cita_disponible(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Busca el primer slot cronológicamente disponible en la fecha y jornada elegidas.
    Si lo encuentra, selecciona automáticamente la hora y el especialista y pasa
    al resumen de confirmación.
    """
    query = update.callback_query
    await query.answer()

    db = SessionLocal()
    try:
        id_negocio = context.user_data.get("id_negocio")
        id_servicio = context.user_data.get("id_servicio")
        fecha_busqueda = context.user_data.get("fecha")
        jornada = context.user_data.get("jornada")
        perfil_servicio = context.user_data.get("perfil_servicio", "unisex")

        if not id_negocio or not id_servicio:
            await query.edit_message_text("⚠️ No se pudo recuperar el contexto del negocio.")
            return ESTADO_MENU_PRINCIPAL

        recursos = crud.obtener_recursos_habilitados_para_servicio(
            db=db,
            id_negocio=id_negocio,
            id_servicio=id_servicio,
            perfil_servicio=perfil_servicio
        )

        candidatos = []

        for recurso in recursos:
            slots = generar_slots_disponibles(
                db=db,
                id_recurso=recurso.id_recurso,
                fecha_busqueda=fecha_busqueda,
                id_servicio=id_servicio
            )

            for slot in slots:
                hora_slot = slot.time()

                if jornada == "manana" and hora_slot.hour < 14:
                    candidatos.append((slot, recurso))

                elif jornada == "tarde" and hora_slot.hour >= 14:
                    candidatos.append((slot, recurso))

        if not candidatos:
            jornada_legible = "mañana" if jornada == "manana" else "tarde"
            await query.edit_message_text(
                f"⚠️ No se encontró una primera cita disponible en la jornada de {jornada_legible}."
            )
            return ESTADO_MENU_PRINCIPAL

        candidatos.sort(key=lambda item: item[0])
        primer_slot, recurso = candidatos[0]

        context.user_data["hora"] = primer_slot.strftime("%H:%M")
        context.user_data["id_recurso"] = recurso.id_recurso
        context.user_data["seleccion_automatica"] = True

    finally:
        db.close()

    return await mostrar_confirmacion(update, context)

async def seleccionar_recurso_por_hora(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Guarda el recurso elegido después de una búsqueda por horario
    y pasa directamente a la confirmación.
    """
    query = update.callback_query
    await query.answer()

    context.user_data["id_recurso"] = int(query.data.replace("res_hor_", ""))

    return await mostrar_confirmacion(update, context)

async def mostrar_recursos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los especialistas/barberos disponibles."""
    query = update.callback_query
    # No hacemos query.answer() aquí si venimos de redirigir_a_especialistas (que ya la maneja o la dejó pendiente)
    # Pero para seguridad y reusabilidad:
    try: await query.answer() 
    except: pass

    db = SessionLocal()
    try:
        id_negocio = context.user_data.get("id_negocio")
        servicio = db.get(Servicio, context.user_data["id_servicio"])

        if not servicio or servicio.id_negocio != id_negocio:
            await query.edit_message_text(
                "⚠️ El servicio seleccionado no es válido para este negocio."
            )
            return ESTADO_MENU_PRINCIPAL

        perfil_servicio = context.user_data.get("perfil_servicio", "unisex")
        id_servicio = context.user_data.get("id_servicio")

        recursos = crud.obtener_recursos_habilitados_para_servicio(
            db=db,
            id_negocio=id_negocio,
            id_servicio=id_servicio,
            perfil_servicio=perfil_servicio
        )
    finally:
        db.close()
    
    if not recursos:
        await query.edit_message_text(
            "⚠️ No hay especialistas disponibles para el perfil del servicio seleccionado."
        )
        return ESTADO_MENU_PRINCIPAL
    
    botones = []
    for recurso in recursos:
        botones.append([
            InlineKeyboardButton(
                f"👤 {recurso.nombre_recurso}",
                callback_data=f"res_{recurso.id_recurso}"
            )
        ])
    
    await query.edit_message_text(
        "👥 *¿Con quién deseas agendar?*\nSelecciona el especialista disponible:",
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

async def cierres_pendientes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra al administrador las citas ya terminadas en tiempo,
    pero aún pendientes de cierre manual.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return ConversationHandler.END

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        citas = crud.obtener_citas_pendientes_cierre(db, id_negocio)

        if not citas:
            await update.message.reply_text(
                "✅ No hay citas pendientes de cierre en este momento."
            )
            return ConversationHandler.END

        botones = []
        for cita in citas[:10]:
            nombre_cliente = cita.usuario.nombre_usuario if cita.usuario else "Cliente"
            texto = (
                f"📅 {cita.fecha_hora_inicio.strftime('%d/%m %H:%M')} - "
                f"{nombre_cliente}"
            )
            botones.append([
                InlineKeyboardButton(
                    texto,
                    callback_data=f"cierre_{cita.id_cita}"
                )
            ])

        await update.message.reply_text(
            "🧾 *Citas pendientes de cierre*\n\n"
            "Selecciona una cita para marcar si asistió o no asistió.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(botones)
        )
        return ESTADO_CIERRES_PENDIENTES

    finally:
        db.close()

async def mostrar_estadisticas_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra al administrador un panel básico de estadísticas del negocio.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        estadisticas = crud.obtener_estadisticas_negocio(db, id_negocio)
    finally:
        db.close()

    promedio_calificacion = estadisticas["promedio_calificacion"]
    promedio_legible = f"{promedio_calificacion}/5" if promedio_calificacion is not None else "Sin datos"

    mensaje = (
        "📊 *Panel básico del negocio*\n\n"
        f"📅 *Total de citas:* {estadisticas['total_citas']}\n"
        f"✅ *Citas completadas:* {estadisticas['citas_completadas']}\n"
        f"❌ *No asistieron:* {estadisticas['citas_no_asistio']}\n"
        f"📉 *Porcentaje no-show:* {estadisticas['porcentaje_no_show']}%\n"
        f"🚫 *Citas canceladas:* {estadisticas['citas_canceladas']}\n"
        f"⭐ *Calificación promedio:* {promedio_legible}\n"
        f"🔁 *Citas con periodicidad:* {estadisticas['citas_con_periodicidad']}\n"
        f"📨 *Recordatorios futuros enviados:* {estadisticas['recordatorios_futuros_enviados']}"
    )

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )

async def mostrar_estadisticas_detalle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra estadísticas detalladas por especialista y servicio.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        top_especialistas_citas = crud.obtener_top_especialistas_por_citas(db, id_negocio)
        top_especialistas_calificacion = crud.obtener_top_especialistas_por_calificacion(db, id_negocio)
        top_servicios = crud.obtener_top_servicios_mas_reservados(db, id_negocio)
        top_no_show = crud.obtener_servicios_con_mas_no_show(db, id_negocio)
    finally:
        db.close()

    bloque_especialistas_citas = formatear_ranking(
        "👨🔧 *Top especialistas por citas completadas*",
        top_especialistas_citas,
        "total"
    )

    # Aquí no usamos el helper genérico para poder mostrar también cuántas citas calificadas tiene.
    if top_especialistas_calificacion:
        lineas_calificacion = ["⭐ *Top especialistas por calificación promedio*"]
        for indice, fila in enumerate(top_especialistas_calificacion, start=1):
            lineas_calificacion.append(
                f"{indice}. {fila['nombre']} — {fila['promedio']}/5 "
                f"({fila['total_calificadas']} calif.)"
            )
        bloque_especialistas_calificacion = "\n".join(lineas_calificacion) + "\n"
    else:
        bloque_especialistas_calificacion = "⭐ *Top especialistas por calificación promedio*\nSin datos disponibles.\n"

    bloque_servicios = formatear_ranking(
        "💈 *Servicios más reservados*",
        top_servicios,
        "total"
    )

    bloque_no_show = formatear_ranking(
        "📉 *Servicios con más no-show*",
        top_no_show,
        "total_no_show"
    )

    mensaje = (
        "📊 *Estadísticas detalladas del negocio*\n\n"
        f"{bloque_especialistas_citas}\n"
        f"{bloque_especialistas_calificacion}\n"
        f"{bloque_servicios}\n"
        f"{bloque_no_show}"
    )

    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )

async def exportar_citas_detalle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Genera y envía al administrador un CSV detallado con las citas del negocio.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        filepath = admin.exportar_citas_detalle_csv(db, id_negocio)
    finally:
        db.close()

    filename_real = filepath.split("/")[-1]
    
    with open(filepath, "rb") as archivo:
        await update.message.reply_document(
            document=archivo,
            filename=filename_real,
            caption="📁 Aquí tienes el reporte detallado de citas en formato CSV."
        )

async def mostrar_habilidades_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra los especialistas del negocio para gestionar sus habilidades.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return ConversationHandler.END

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        recursos = crud.obtener_recursos_del_negocio(db, id_negocio)
    finally:
        db.close()

    if not recursos:
        await update.message.reply_text("⚠️ No hay especialistas configurados en el negocio.")
        return ConversationHandler.END

    botones = []
    for recurso in recursos:
        botones.append([
            InlineKeyboardButton(
                f"👤 {recurso.nombre_recurso}",
                callback_data=f"hab_recurso_{recurso.id_recurso}"
            )
        ])

    await update.message.reply_text(
        "🛠️ *Gestión de habilidades*\n\nSelecciona un especialista:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_HABILIDADES_RECURSO

async def mostrar_detalle_habilidades_recurso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra los servicios habilitados y no habilitados de un especialista.
    """
    query = update.callback_query
    await query.answer()

    if not query.from_user or not es_admin(query.from_user.id):
        await query.edit_message_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    id_recurso = int(query.data.replace("hab_recurso_", ""))
    context.user_data["id_recurso_habilidad"] = id_recurso

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        recurso = db.get(Recurso, id_recurso)
        if not recurso:
            await query.edit_message_text("⚠️ El especialista ya no existe.")
            return ConversationHandler.END

        servicios_habilitados = crud.obtener_servicios_habilitados_de_recurso(db, id_negocio, id_recurso)
        servicios_no_habilitados = crud.obtener_servicios_no_habilitados_de_recurso(db, id_negocio, id_recurso)
    finally:
        db.close()

    mensaje = (
        f"🛠️ *Habilidades de {recurso.nombre_recurso}*\n\n"
        f"✅ *Servicios habilitados:*\n{formatear_lista_servicios(servicios_habilitados)}\n\n"
        f"➕ *Servicios disponibles para agregar:*\n{formatear_lista_servicios(servicios_no_habilitados)}\n\n"
        "¿Qué deseas hacer?"
    )

    await query.edit_message_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Agregar habilidad", callback_data="hab_accion_agregar")],
            [InlineKeyboardButton("➖ Quitar habilidad", callback_data="hab_accion_quitar")],
        ])
    )
    return ESTADO_HABILIDADES_ACCION

async def mostrar_servicios_para_accion_habilidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra los servicios que se pueden agregar o quitar al especialista.
    """
    query = update.callback_query
    await query.answer()

    if not query.from_user or not es_admin(query.from_user.id):
        await query.edit_message_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    accion = query.data.replace("hab_accion_", "")
    context.user_data["accion_habilidad"] = accion

    id_recurso = context.user_data.get("id_recurso_habilidad")
    id_negocio = obtener_id_negocio_activo()

    if not id_recurso:
        await query.edit_message_text("⚠️ No se encontró el especialista seleccionado.")
        return ConversationHandler.END

    db = SessionLocal()
    try:
        if accion == "agregar":
            servicios = crud.obtener_servicios_no_habilitados_de_recurso(db, id_negocio, id_recurso)
            titulo = "➕ *Selecciona un servicio para agregar*"
            prefijo_callback = "hab_add_"
        else:
            servicios = crud.obtener_servicios_habilitados_de_recurso(db, id_negocio, id_recurso)
            titulo = "➖ *Selecciona un servicio para quitar*"
            prefijo_callback = "hab_del_"
    finally:
        db.close()

    if not servicios:
        await query.edit_message_text(
            "⚠️ No hay servicios disponibles para esa acción."
        )
        return ConversationHandler.END

    botones = []
    for servicio in servicios:
        botones.append([
            InlineKeyboardButton(
                f"💈 {servicio.nombre_servicio}",
                callback_data=f"{prefijo_callback}{servicio.id_servicio}"
            )
        ])

    await query.edit_message_text(
        titulo,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones)
    )
    return ESTADO_HABILIDADES_ACCION

async def ejecutar_cambio_habilidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Agrega o quita una habilidad del especialista seleccionado.
    """
    query = update.callback_query
    await query.answer()

    if not query.from_user or not es_admin(query.from_user.id):
        await query.edit_message_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    id_recurso = context.user_data.get("id_recurso_habilidad")
    id_negocio = obtener_id_negocio_activo()

    if not id_recurso:
        await query.edit_message_text("⚠️ No se encontró el especialista seleccionado.")
        return ConversationHandler.END

    db = SessionLocal()
    try:
        if query.data.startswith("hab_add_"):
            id_servicio = int(query.data.replace("hab_add_", ""))
            exito = crud.agregar_habilidad_a_recurso(db, id_negocio, id_recurso, id_servicio)
            mensaje = "✅ Habilidad agregada correctamente." if exito else "⚠️ No se pudo agregar la habilidad."
        elif query.data.startswith("hab_del_"):
            id_servicio = int(query.data.replace("hab_del_", ""))
            exito = crud.quitar_habilidad_a_recurso(db, id_negocio, id_recurso, id_servicio)
            mensaje = "✅ Habilidad quitada correctamente." if exito else "⚠️ No se pudo quitar la habilidad."
        else:
            await query.edit_message_text("⚠️ Acción no válida.")
            return ConversationHandler.END
    finally:
        db.close()

    context.user_data.pop("accion_habilidad", None)
    context.user_data.pop("id_recurso_habilidad", None)

    await query.edit_message_text(mensaje)
    return ConversationHandler.END

async def ver_bienvenida_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Permite al admin ver el mensaje actual de bienvenida del negocio.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        mensaje = crud.obtener_mensaje_bienvenida(db, id_negocio)
    finally:
        db.close()

    await update.message.reply_text(
        f"📝 *Mensaje actual de bienvenida:*\n\n{mensaje}",
        parse_mode="Markdown"
    )

async def editar_bienvenida_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Inicia el flujo para editar el mensaje de bienvenida.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para usar este comando.")
        return ConversationHandler.END

    await update.message.reply_text(
        "✍️ Envía ahora el nuevo mensaje de bienvenida.\n\n"
        "Ese texto será el que verán los clientes al iniciar el bot."
    )
    return ESTADO_EDITAR_BIENVENIDA

async def guardar_bienvenida_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Guarda el nuevo mensaje de bienvenida enviado por el admin.
    """
    if not update.effective_user or not es_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    if not update.message or not update.message.text:
        await update.message.reply_text("⚠️ No se recibió texto válido.")
        return ConversationHandler.END

    nuevo_mensaje = update.message.text.strip()

    if len(nuevo_mensaje) < 10:
        await update.message.reply_text(
            "⚠️ El mensaje es demasiado corto. Escribe un texto un poco más completo."
        )
        return ESTADO_EDITAR_BIENVENIDA

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        exito = crud.guardar_mensaje_bienvenida(db, id_negocio, nuevo_mensaje)
    finally:
        db.close()

    if not exito:
        await update.message.reply_text(
            "⚠️ No fue posible guardar el mensaje de bienvenida."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "✅ Mensaje de bienvenida actualizado correctamente."
    )
    return ConversationHandler.END

async def mostrar_opciones_cierre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Muestra las opciones de cierre para una cita específica.
    """
    query = update.callback_query
    await query.answer()

    if not query.from_user or not es_admin(query.from_user.id):
        await query.edit_message_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    id_cita = int(query.data.replace("cierre_", ""))
    context.user_data["id_cita_cierre"] = id_cita

    db = SessionLocal()
    try:
        cita = db.get(Cita, id_cita)

        if not cita:
            await query.edit_message_text("⚠️ La cita seleccionada ya no existe.")
            return ConversationHandler.END

        nombre_cliente = cita.usuario.nombre_usuario if cita.usuario else "Cliente"
        nombre_recurso = cita.recurso.nombre_recurso if cita.recurso else "Especialista"

        await query.edit_message_text(
            "🧾 *Cerrar cita*\n\n"
            f"👤 Cliente: {nombre_cliente}\n"
            f"👨‍🔧 Especialista: {nombre_recurso}\n"
            f"📅 Fecha: {cita.fecha_hora_inicio.strftime('%d/%m/%Y')}\n"
            f"⏰ Hora: {cita.fecha_hora_inicio.strftime('%H:%M')}\n\n"
            "Indica el resultado de esta cita:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Asistió", callback_data="cerrar_completada")],
                [InlineKeyboardButton("❌ No asistió", callback_data="cerrar_no_asistio")],
            ])
        )
        return ESTADO_CONFIRMAR_CIERRE

    finally:
        db.close()

async def cerrar_cita_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Ejecuta el cierre definitivo de la cita.
    """
    query = update.callback_query
    await query.answer()

    if not query.from_user or not es_admin(query.from_user.id):
        await query.edit_message_text("⚠️ No tienes permisos para realizar esta acción.")
        return ConversationHandler.END

    id_cita = context.user_data.get("id_cita_cierre")
    id_negocio = obtener_id_negocio_activo()

    if not id_cita:
        await query.edit_message_text("⚠️ No se encontró la cita pendiente de cierre.")
        return ConversationHandler.END

    if query.data == "cerrar_completada":
        nuevo_estado = "completada"
        mensaje = "✅ La cita se marcó como completada."
        disparar_reactivacion = False
        disparar_calificacion = True
    elif query.data == "cerrar_no_asistio":
        nuevo_estado = "no_asistio"
        mensaje = "❌ La cita se marcó como no asistida."
        disparar_reactivacion = True
        disparar_calificacion = False
    else:
        await query.edit_message_text("⚠️ Acción de cierre no válida.")
        return ConversationHandler.END

    db = SessionLocal()
    try:
        cita = db.get(Cita, id_cita)

        exito = crud.actualizar_estado_cita(
            db=db,
            id_negocio=id_negocio,
            id_cita=id_cita,
            nuevo_estado=nuevo_estado
        )

        id_telegram_cliente = None
        nombre_cliente = "Cliente"

        if cita and cita.usuario:
            id_telegram_cliente = cita.usuario.id_telegram
            nombre_cliente = cita.usuario.nombre_usuario or "Cliente"

    finally:
        db.close()

    if not exito:
        await query.edit_message_text(
            "⚠️ No fue posible actualizar el estado de la cita."
        )
        return ConversationHandler.END

    await query.edit_message_text(mensaje)
    
    if disparar_reactivacion and id_telegram_cliente:
        await enviar_mensaje_reactivacion(
            context=context,
            id_telegram=id_telegram_cliente,
            nombre_cliente=nombre_cliente,
        )

    if disparar_calificacion and id_telegram_cliente:
        await enviar_mensaje_calificacion(
            context=context,
            id_telegram=id_telegram_cliente,
            nombre_cliente=nombre_cliente,
            id_cita=id_cita,
        )

    context.user_data.pop("id_cita_cierre", None)
    return ConversationHandler.END

async def enviar_mensaje_reactivacion(
    context: ContextTypes.DEFAULT_TYPE,
    id_telegram: int,
    nombre_cliente: str
) -> None:
    """
    Envía al cliente un mensaje interactivo para intentar recuperar
    la cita perdida por no asistencia.
    """
    await context.bot.send_message(
        chat_id=id_telegram,
        text=MENSAJE_REACTIVACION_NO_ASISTIO.replace(
            "Notamos", f"Hola {nombre_cliente}, notamos"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Sí, reagendar", callback_data="reactivar_si")],
            [InlineKeyboardButton("🤷‍♂️ Quizás luego", callback_data="reactivar_no")],
        ])
    )

async def manejar_reactivacion_no_asistio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la respuesta del cliente al mensaje de reactivación.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "reactivar_si":
        context.user_data.pop("id_cita_cierre", None)
        limpiar_contexto_reserva(context)

        await query.edit_message_text(
            "✅ Perfecto. Vamos a buscar una nueva cita para ti."
        )
        return await mostrar_perfiles_servicio(update, context)

    await query.edit_message_text(
        "👌 Entendido. Cuando quieras volver, aquí estaremos para ayudarte."
    )
    return ConversationHandler.END

async def enviar_mensaje_calificacion(
    context: ContextTypes.DEFAULT_TYPE,
    id_telegram: int,
    nombre_cliente: str,
    id_cita: int
) -> None:
    """
    Envía al cliente una solicitud simple de calificación del servicio.
    """
    await context.bot.send_message(
        chat_id=id_telegram,
        text=MENSAJE_SOLICITUD_CALIFICACION.replace(
            "¿Cómo", f"Hola {nombre_cliente}, ¿cómo"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("😡 1", callback_data=f"cal_{id_cita}_1")],
            [InlineKeyboardButton("😕 2", callback_data=f"cal_{id_cita}_2")],
            [InlineKeyboardButton("😐 3", callback_data=f"cal_{id_cita}_3")],
            [InlineKeyboardButton("🙂 4", callback_data=f"cal_{id_cita}_4")],
            [InlineKeyboardButton("🤩 5", callback_data=f"cal_{id_cita}_5")],
        ])
    )

async def manejar_calificacion_post_cita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la calificación enviada por el cliente después de una cita completada.
    """
    query = update.callback_query
    await query.answer()

    try:
        _, id_cita_str, calificacion_str = query.data.split("_")
        id_cita = int(id_cita_str)
        calificacion = int(calificacion_str)
    except (ValueError, IndexError):
        await query.edit_message_text("⚠️ No se pudo procesar la calificación.")
        return ConversationHandler.END

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        exito = crud.guardar_calificacion_cita(
            db=db,
            id_negocio=id_negocio,
            id_cita=id_cita,
            calificacion=calificacion
        )
    finally:
        db.close()

    if not exito:
        await query.edit_message_text(
            "⚠️ No fue posible guardar tu calificación. Inténtalo más tarde."
        )
        return ConversationHandler.END

    if calificacion >= 4:
        mensaje_confirmacion = "🙏 ¡Gracias por tu valoración! Tu respuesta ha sido registrada."
    else:
        mensaje_confirmacion = "🙏 Gracias por tu sinceridad. Tu respuesta ha sido registrada."

    await query.edit_message_text(mensaje_confirmacion)

    await manejar_filtro_resena(query, calificacion)

    db = SessionLocal()
    try:
        cita = db.get(Cita, id_cita)
        id_telegram_cliente = None
        nombre_cliente = "Cliente"

        if cita and cita.usuario:
            id_telegram_cliente = cita.usuario.id_telegram
            nombre_cliente = cita.usuario.nombre_usuario or "Cliente"
    finally:
        db.close()

    if id_telegram_cliente:
        await enviar_mensaje_periodicidad(
            context=context,
            id_telegram=id_telegram_cliente,
            nombre_cliente=nombre_cliente,
            id_cita=id_cita,
        )

    return ConversationHandler.END

async def manejar_filtro_resena(
    query,
    calificacion: int
) -> None:
    """
    Después de guardar la calificación, dirige al cliente a una acción distinta
    según su nivel de satisfacción.
    """
    id_negocio = obtener_id_negocio_activo()
    db = SessionLocal()
    try:
        negocio = crud.obtener_negocio_por_id(db, id_negocio)
        config = negocio.configuracion_json if negocio and negocio.configuracion_json else {}
        google_review_url = config.get("google_review_url", "").strip()
        support_contact_url = config.get("support_contact_url", "").strip()
    finally:
        db.close()

    if calificacion >= 4:
        botones = []
        if google_review_url:
            botones.append([
                InlineKeyboardButton("🌟 Dejar reseña en Google", url=google_review_url)
            ])

        await query.message.reply_text(
            "💛 *¡Gracias por tu valoración!*\n\n"
            "Nos alegra saber que tu experiencia fue positiva.\n"
            "Si quieres apoyarnos, puedes dejarnos una reseña pública.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(botones) if botones else None,
        )
        return

    botones = []
    if support_contact_url:
        botones.append([
            InlineKeyboardButton("💬 Contarnos qué pasó", url=support_contact_url)
        ])

    await query.message.reply_text(
        "🙏 *Gracias por tu sinceridad*\n\n"
        "Lamentamos que tu experiencia no haya sido la esperada.\n"
        "Nos gustaría conocer mejor lo ocurrido para poder mejorar.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(botones) if botones else None,
    )

async def enviar_mensaje_periodicidad(
    context: ContextTypes.DEFAULT_TYPE,
    id_telegram: int,
    nombre_cliente: str,
    id_cita: int
) -> None:
    """
    Pregunta al cliente si desea un recordatorio para volver a reservar.
    """
    await context.bot.send_message(
        chat_id=id_telegram,
        text=MENSAJE_SOLICITUD_PERIODICIDAD.replace(
            "Si quieres", f"Hola {nombre_cliente}, si quieres"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 En 21 días", callback_data=f"per_{id_cita}_21")],
            [InlineKeyboardButton("📅 En 30 días", callback_data=f"per_{id_cita}_30")],
            [InlineKeyboardButton("❌ No, gracias", callback_data=f"per_{id_cita}_0")],
        ])
    )

async def manejar_periodicidad_post_cita(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la respuesta del cliente sobre el recordatorio futuro.
    """
    query = update.callback_query
    await query.answer()

    try:
        _, id_cita_str, dias_str = query.data.split("_")
        id_cita = int(id_cita_str)
        dias_recordatorio = int(dias_str)
    except (ValueError, IndexError):
        await query.edit_message_text("⚠️ No se pudo procesar tu respuesta.")
        return ConversationHandler.END

    if dias_recordatorio == 0:
        await query.edit_message_text(
            "👌 Perfecto. No te enviaremos recordatorio para esta cita."
        )
        return ConversationHandler.END

    id_negocio = obtener_id_negocio_activo()

    db = SessionLocal()
    try:
        exito = crud.guardar_periodicidad_cita(
            db=db,
            id_negocio=id_negocio,
            id_cita=id_cita,
            dias_recordatorio=dias_recordatorio
        )
    finally:
        db.close()

    if not exito:
        await query.edit_message_text(
            "⚠️ No fue posible guardar tu preferencia de recordatorio."
        )
        return ConversationHandler.END

    await query.message.reply_text(
        f"✅ Perfecto. Te recordaremos tu próxima cita en aproximadamente {dias_recordatorio} días."
    )
    return ConversationHandler.END

async def enviar_mensaje_recordatorio_reagendamiento(
    context: ContextTypes.DEFAULT_TYPE,
    id_telegram: int,
    nombre_cliente: str,
) -> None:
    """
    Envía al cliente un recordatorio para volver a reservar.
    """
    await context.bot.send_message(
        chat_id=id_telegram,
        text=MENSAJE_RECORDATORIO_REAGENDAMIENTO.replace(
            "Te escribimos", f"Hola {nombre_cliente}, te escribimos"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📅 Reservar ahora", callback_data="reagendar_si")],
            [InlineKeyboardButton("❌ Ahora no", callback_data="reagendar_no")],
        ])
    )

async def manejar_recordatorio_reagendamiento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Procesa la respuesta del cliente al recordatorio futuro.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "reagendar_si":
        limpiar_contexto_reserva(context)

        await query.edit_message_text(
            "✅ Perfecto. Vamos a buscar una nueva cita para ti."
        )
        return await mostrar_perfiles_servicio(update, context)

    await query.edit_message_text(
        "👌 Entendido. Cuando quieras volver, aquí estaremos."
    )
    return ConversationHandler.END

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
    
    if "seleccion_automatica" not in context.user_data:
        context.user_data["seleccion_automatica"] = False
    
    db = SessionLocal()
    try:
        servicio = db.get(Servicio, context.user_data["id_servicio"])
        recurso = db.get(Recurso, context.user_data["id_recurso"])
    finally:
        db.close()
    
    resumen = (
        "🏁 *RESUMEN DE TU CITA*\n\n"
        f"💈 *Servicio*: {servicio.nombre_servicio}\n"
        f"🧾 *Perfil del servicio*: {context.user_data.get('perfil_servicio', 'no definido')}\n"
        f"👤 *Especialista*: {recurso.nombre_recurso}\n"
        f"📅 *Fecha*: {context.user_data['fecha']}\n"
        f"🕓 *Jornada*: {context.user_data.get('jornada', 'no aplica')}\n"
        f"⚡ *Selección automática*: {'sí' if context.user_data.get('seleccion_automatica') else 'no'}\n"
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
            id_negocio = context.user_data.get("id_negocio")
            id_usuario = context.user_data.get("id_usuario")
            id_recurso = context.user_data.get("id_recurso")
            id_servicio = context.user_data.get("id_servicio")
            fecha = context.user_data.get("fecha")
            hora = context.user_data.get("hora")

            f_str = f"{fecha} {hora}"
            h_inicio = datetime.strptime(f_str, "%Y-%m-%d %H:%M")

            servicio = db.get(Servicio, id_servicio)
            recurso = db.get(Recurso, id_recurso)

            if not servicio or not recurso:
                await query.edit_message_text(
                    "⚠️ No se pudo validar el servicio o el especialista seleccionado."
                )
                return ESTADO_MENU_PRINCIPAL

            if servicio.id_negocio != id_negocio or recurso.id_negocio != id_negocio:
                await query.edit_message_text(
                    "⚠️ Los datos de la reserva no pertenecen al negocio activo."
                )
                return ESTADO_MENU_PRINCIPAL

            # Revalidación crítica del slot justo antes de guardar.
            slots_actuales = generar_slots_disponibles(
                db=db,
                id_recurso=id_recurso,
                fecha_busqueda=fecha,
                id_servicio=id_servicio
            )
            slot_sigue_disponible = any(slot.strftime("%H:%M") == hora for slot in slots_actuales)

            if not slot_sigue_disponible:
                await query.edit_message_text(
                    "⚠️ Ese horario ya no está disponible. Por favor elige otra hora.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Volver a elegir hora", callback_data=f"fec_{fecha.isoformat()}")]
                    ])
                )
                return ESTADO_SELECCION_FECHA

            h_fin = h_inicio + timedelta(minutes=servicio.duracion_minutos)

            sujeto = db.query(EntidadSujeto).filter(
                EntidadSujeto.id_usuario_dueno == id_usuario
            ).first()

            if not sujeto:
                await query.edit_message_text(
                    "⚠️ No se encontró un sujeto asociado al usuario."
                )
                return ESTADO_MENU_PRINCIPAL

            nueva_cita = Cita(
                id_negocio=id_negocio,
                id_usuario=id_usuario,
                id_sujeto=sujeto.id_sujeto,
                id_recurso=id_recurso,
                id_servicio=id_servicio,
                fecha_hora_inicio=h_inicio,
                fecha_hora_fin=h_fin,
                estado_cita="confirmada",
                precio_cobrado=servicio.precio
            )
            db.add(nueva_cita)
            db.commit()

            logger.info(
                "Cita creada correctamente. id_cita=%s, id_negocio=%s, id_usuario=%s, id_recurso=%s, inicio=%s",
                nueva_cita.id_cita,
                id_negocio,
                id_usuario,
                id_recurso,
                h_inicio,
            )

            await query.edit_message_text(
                "🎉 ¡Enhorabuena! *Tu cita ha sido confirmada.*\n\n"
                "Te enviaremos un recordatorio 24 horas antes. ¡Te esperamos!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu_volver_inicio")]
                ])
            )
        except Exception as e:
            logger.exception("Error al crear la cita: %s", e)
            await query.edit_message_text(
                "⚠️ Ocurrió un error al guardar tu cita. Por favor intenta de nuevo."
            )
        finally:
            db.close()
        
        return ESTADO_MENU_PRINCIPAL
    
    return ESTADO_MENU_PRINCIPAL

# --- INTERFAZ ADMINISTRATIVA ---

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
    id_negocio = context.user_data.get("id_negocio", obtener_id_negocio_activo())
    servicios = db.query(Servicio).filter(Servicio.id_negocio == id_negocio).all()
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
        # Verificar si ya existe para este negocio
        id_negocio = context.user_data.get("id_negocio", obtener_id_negocio_activo())
        existente = db.query(DiaNoDisponible).filter(
            and_(DiaNoDisponible.fecha == fecha, DiaNoDisponible.id_negocio == id_negocio)
        ).first()
        if not existente:
            bloqueo = DiaNoDisponible(id_negocio=id_negocio, fecha=fecha, motivo="Bloqueo Manual Admin")
            db.add(bloqueo)
            db.commit()
            await update.message.reply_text(f"✅ Día {fecha} bloqueado exitosamente para este negocio.")
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
        id_negocio_csv = context.user_data.get("id_negocio", obtener_id_negocio_activo())
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
                CallbackQueryHandler(mostrar_perfiles_servicio, pattern="^menu_agendar$|^menu_volver_inicio$"),
                CallbackQueryHandler(menu_privacidad, pattern="^menu_privacidad$"),
            ],
            ESTADO_SELECCION_PERFIL: [
                CallbackQueryHandler(mostrar_servicios, pattern="^perfil_")
            ],
            ESTADO_SELECCION_SERVICIO: [
                CallbackQueryHandler(mostrar_modo_busqueda, pattern="^srv_")
            ],
            ESTADO_MODO_BUSQUEDA: [
                CallbackQueryHandler(redirigir_a_especialistas, pattern="^modo_especialista$"),
                CallbackQueryHandler(redirigir_a_fechas_por_horario, pattern="^modo_horario$"),
            ],
            ESTADO_SELECCION_RECURSO: [
                CallbackQueryHandler(mostrar_fechas, pattern="^res_")
            ],
            ESTADO_SELECCION_FECHA: [
                CallbackQueryHandler(mostrar_horas, pattern="^fec_"),
                CallbackQueryHandler(mostrar_jornadas_por_horario, pattern="^fec_hor_"),
                CallbackQueryHandler(mostrar_perfiles_servicio, pattern="^menu_agendar$"),
            ],
            ESTADO_SELECCION_JORNADA: [
                CallbackQueryHandler(mostrar_horas_por_horario, pattern="^jor_")
            ],
            ESTADO_SELECCION_HORA: [
                CallbackQueryHandler(mostrar_confirmacion, pattern="^hor_"),
                CallbackQueryHandler(seleccionar_primera_cita_disponible, pattern="^hor_gen_primera$"),
                CallbackQueryHandler(mostrar_recursos_por_hora, pattern="^hor_gen_"),
            ],
            ESTADO_SELECCION_RECURSO_POR_HORA: [
                CallbackQueryHandler(seleccionar_recurso_por_hora, pattern="^res_hor_")
            ],
            ESTADO_HABILIDADES_RECURSO: [
                CallbackQueryHandler(mostrar_detalle_habilidades_recurso, pattern="^hab_recurso_")
            ],
            ESTADO_HABILIDADES_ACCION: [
                CallbackQueryHandler(mostrar_servicios_para_accion_habilidad, pattern="^hab_accion_"),
                CallbackQueryHandler(ejecutar_cambio_habilidad, pattern="^hab_add_"),
                CallbackQueryHandler(ejecutar_cambio_habilidad, pattern="^hab_del_"),
            ],
            ESTADO_EDITAR_BIENVENIDA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_bienvenida_admin)
            ],
            ESTADO_CONFIRMACION_FINAL: [
                CallbackQueryHandler(finalizar_reserva, pattern="^conf_si$"),
                CallbackQueryHandler(mostrar_perfiles_servicio, pattern="^menu_agendar$"),
            ],
            ESTADO_ADMIN_SERVICIOS: [
                CallbackQueryHandler(admin_toggle_servicio, pattern="^adm_srv_tog_"),
                CallbackQueryHandler(menu_admin, pattern="^admin_volver$"),
            ],
            ESTADO_ADMIN_BLOQUEO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirmar_bloqueo)
            ],
            ESTADO_CIERRES_PENDIENTES: [
                CallbackQueryHandler(mostrar_opciones_cierre, pattern="^cierre_")
            ],
            ESTADO_CONFIRMAR_CIERRE: [
                CallbackQueryHandler(cerrar_cita_admin, pattern="^cerrar_")
            ],
            ESTADO_REACTIVACION_NO_ASISTIO: [
                CallbackQueryHandler(manejar_reactivacion_no_asistio, pattern="^reactivar_")
            ],
            ESTADO_CALIFICACION_POST_CITA: [
                CallbackQueryHandler(manejar_calificacion_post_cita, pattern="^cal_")
            ],
            ESTADO_PERIODICIDAD_POST_CITA: [
                CallbackQueryHandler(manejar_periodicidad_post_cita, pattern="^per_")
            ],
            ESTADO_RECORDATORIO_REAGENDAMIENTO: [
                CallbackQueryHandler(manejar_recordatorio_reagendamiento, pattern="^reagendar_")
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(manejar_reactivacion_no_asistio, pattern="^reactivar_"))
    application.add_handler(CallbackQueryHandler(manejar_calificacion_post_cita, pattern="^cal_"))
    application.add_handler(CallbackQueryHandler(manejar_periodicidad_post_cita, pattern="^per_"))
    application.add_handler(CallbackQueryHandler(manejar_recordatorio_reagendamiento, pattern="^reagendar_"))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("cierres_pendientes", cierres_pendientes))
    application.add_handler(CommandHandler("estadisticas", mostrar_estadisticas_admin))
    application.add_handler(CommandHandler("estadisticas_detalle", mostrar_estadisticas_detalle_admin))
    application.add_handler(CommandHandler("habilidades", mostrar_habilidades_admin))
    application.add_handler(CommandHandler("exportar_citas_detalle", exportar_citas_detalle_admin))
    application.add_handler(CommandHandler("ver_bienvenida", ver_bienvenida_admin))
    application.add_handler(CommandHandler("editar_bienvenida", editar_bienvenida_admin))
    application.add_handler(CommandHandler("admin", menu_admin))
    application.add_handler(CommandHandler("mi_privacidad", menu_privacidad))
    application.add_handler(CallbackQueryHandler(manejar_admin_export, pattern="^admin_exportar_csv$"))
    application.add_handler(CallbackQueryHandler(admin_gestionar_servicios, pattern="^admin_servicios$"))
    application.add_handler(CallbackQueryHandler(admin_solicitar_bloqueo, pattern="^admin_bloqueo$"))
    application.add_handler(CallbackQueryHandler(menu_admin, pattern="^admin_volver$"))
    application.add_handler(CallbackQueryHandler(ejecutar_eliminacion_privacidad, pattern="^priv_eliminar$"))
