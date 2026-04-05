# File: main.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Punto de entrada principal (Motor Dual: Bot + API).
# Rol: Orquestador del sistema.
# ──────────────────────────────────────────────────────────────────────

import os
import asyncio
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
import logging
from telegram.ext import ApplicationBuilder
from modules.telegram_bot import configurar_bot
from modules.scheduler import iniciar_scheduler

# Configuración de Logs a archivo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("error_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar configuración
load_dotenv()

# Instancia de FastAPI
app = FastAPI(title="Bot de Agendamiento Pro - API")

@app.get("/")
def home():
    return {"status": "online", "message": "API de agendamiento activa"}

async def iniciar_telegram():
    """Inicializa y arranca el bot de Telegram de forma asíncrona."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_token_here":
        print("⚠️ TELEGRAM_BOT_TOKEN no configurado. El bot no iniciará.")
        return

    # Configurar la aplicación de Telegram
    application = ApplicationBuilder().token(token).build()
    
    # Registrar comandos y manejadores (Desde modules/telegram_bot.py)
    configurar_bot(application)
    
    # Iniciar motor de notificaciones (APScheduler)
    iniciar_scheduler(application.bot)
    
    print("🚀 Bot de Telegram iniciado...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

async def main():
    """Corre FastAPI y el Bot de Telegram simultáneamente."""
    # Lanzamos el Bot de Telegram en el background
    asyncio.create_task(iniciar_telegram())
    
    # Lanzamos el servidor Web (FastAPI)
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        logger.info("🎬 Iniciando Sistema de Agendamiento Inteligente...")
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"🛑 FALLO CRÍTICO EN EL ARRANQUE: {str(e)}", exc_info=True)
    finally:
        logger.info("👋 Apagado ordenado del sistema.")
