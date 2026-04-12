# File: modules/notifications.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Centralizar el envío de alertas externas (Telegram/Email).
# Rol: Capa de despacho de comunicaciones (Etapa 5).
# ──────────────────────────────────────────────────────────────────────

import logging
import os
from typing import Dict

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from telegram import Bot
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

async def enviar_recordatorio_telegram(bot: Bot, chat_id: int, mensaje: str) -> bool:
    """Envía un mensaje de texto vía Telegram de forma asíncrona."""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=mensaje,
            parse_mode=ParseMode.MARKDOWN
        )
        return True
    except Exception as e:
        logger.exception("Error enviando mensaje de Telegram a chat_id=%s: %s", chat_id, e)
        return False

async def enviar_reactivacion_no_asistencia(bot: Bot, chat_id: int, nombre_cliente: str) -> bool:
    """
    Envía un mensaje empático al cliente cuando no asistió a su cita,
    invitándolo a reagendar.
    """
    mensaje = (
        "😔 *No pudimos verte hoy*\n\n"
        f"Hola {nombre_cliente}, notamos que no pudiste asistir a tu cita.\n\n"
        "¿Te gustaría agendar una nueva fecha ahora mismo?"
    )

    return await enviar_recordatorio_telegram(bot, chat_id, mensaje)

def enviar_confirmacion_brevo(destinatario: str, datos_cita: Dict) -> bool:
    """
    Envía un correo de confirmación usando la API de Brevo (SendinBlue).
    Estructura base para futura integración completa.
    """
    api_key = os.getenv("SENDINBLUE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        logger.warning("API Key de Brevo no configurada. Se omite el envío de correo.")
        return False

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = api_key
    
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Construcción del correo base
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": destinatario}],
        subject="Confirmación de tu Cita Inteligente 📅",
        html_content=(
            f"<html><body>"
            f"<h1>¡Hola! Tu cita ha sido confirmada</h1>"
            f"<p>Detalles:</p>"
            f"<ul>"
            f"<li><b>Servicio:</b> {datos_cita.get('servicio')}</li>"
            f"<li><b>Fecha:</b> {datos_cita.get('fecha')}</li>"
            f"<li><b>Hora:</b> {datos_cita.get('hora')}</li>"
            f"</ul>"
            f"<p>Te esperamos en el negocio.</p>"
            f"</body></html>"
        ),
        sender={
            "name": os.getenv("BREVO_SENDER_NAME", "Agendamiento Pro"),
            "email": os.getenv("BREVO_SENDER_EMAIL", "noreply@agendamiento.pro"),
        }
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        logger.info("Correo de confirmación enviado a %s", destinatario)
        return True
    except ApiException as e:
        logger.exception("Error enviando email vía Brevo a %s: %s", destinatario, e)
        return False
