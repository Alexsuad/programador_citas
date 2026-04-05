# File: modules/notifications.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Centralizar el envío de alertas externas (Telegram/Email).
# Rol: Capa de despacho de comunicaciones (Etapa 5).
# ──────────────────────────────────────────────────────────────────────

import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from telegram import Bot
from telegram import Bot
from telegram.constants import ParseMode
from typing import Dict
import logging

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
        logger.error(f"❌ Error enviando Telegram a {chat_id}: {e}")
        return False

def enviar_confirmacion_brevo(destinatario: str, datos_cita: Dict) -> bool:
    """
    Envía un correo de confirmación usando la API de Brevo (SendinBlue).
    Estructura base para futura integración completa.
    """
    api_key = os.getenv("SENDINBLUE_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        logger.warning("⚠️ API Key de Brevo no configurada. Saltando envío de correo.")
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
        sender={"name": "Agendamiento Pro", "email": "noreply@agendamiento.pro"}
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        logger.error(f"❌ Error enviando Email via Brevo: {e}")
        return False
