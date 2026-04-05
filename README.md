# 📅 Bot de Agendamiento Inteligente (MVP)

Sistema universal de gestión de citas para Telegram, diseñado para alta escalabilidad y precisión en el cálculo de disponibilidad.

## 🚀 Inicio Rápido (uv)

Este proyecto utiliza `uv` como gestor estándar de dependencias y entornos.

1. **Instalar dependencias y activar entorno**:
   ```bash
   uv sync
   ```

2. **Configurar entorno**:
   Copia el archivo `.env.example` a `.env` y rellena las variables:
   ```bash
   cp .env.example .env
   # Edita .env con tu TELEGRAM_BOT_TOKEN
   ```

3. **Inicializar y Poblado de Datos**:
   (Opcional si deseas ver datos de prueba inmediatamente)
   ```bash
   uv run alembic upgrade head
   export PYTHONPATH=$PYTHONPATH:.
   uv run python -m database.seeding
   ```

4. **Lanzar el Sistema**:
   ```bash
   uv run python main.py
   ```

## 🧪 Pruebas de Calidad

Para verificar que el motor de disponibilidad y solapamiento funciona correctamente:
```bash
uv run pytest tests/test_availability.py
```

## 📊 Módulos de Administración

- **Exportación**: Genera reportes en CSV compatible con Excel (`utf-8-sig`).
- **Importación**: Permite cargar clientes masivamente desde archivos CSV.
- **Recordatorios**: Motor automático de alertas vía Telegram (24h/2h).

## 🛠️ Tecnologías Utilizadas

- **Core**: Python 3.12 (uv)
- **Persistencia**: SQLite (SQLAlchemy + Alembic)
- **Mensajería**: python-telegram-bot
- **Asincronía**: APScheduler
- **Validación**: Pydantic
- **API**: FastAPI + Uvicorn

---
*Desarrollado con el protocolo de calidad "Vamos despacio que tengo prisa".*
