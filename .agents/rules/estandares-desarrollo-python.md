---
trigger: always_on
---

# ESTÁNDARES DE DESARROLLO EN PYTHON

## 1. CALIDAD Y CUIDADO DEL CÓDIGO
- Cuando modifiques código, asegúrate OBLIGATORIAMENTE de que el código candidato no rompa la funcionalidad del código original.
- El código generado debe ser limpio, sin código muerto (elimina imports no usados o prints de debug) y sin rutinas repetidas.
- Revisa tu trabajo 2 veces antes de entregar el resultado definitivo.

## 2. ESTILO Y ESTRUCTURA
- Uso obligatorio de `snake_case` para variables, funciones y métodos.
- Utiliza `asyncio` para operaciones de alta concurrencia. Justifica si decides usar un enfoque síncrono.
- Cero hardcoding: Las claves, tokens y URLs de bases de datos deben cargarse siempre usando `.env` y `os.getenv()`.

## 3. ESTÁNDAR DE HERRAMIENTAS (UV)
- Utiliza `uv` como estándar único para la gestión de dependencias y entornos (`uv sync`, `uv run`, `uv add`).
- Queda prohibido usar `pip` directamente, salvo problemas de compatibilidad documentados.

## 4. DOCUMENTACIÓN
Todo archivo `.py` nuevo debe iniciar con este encabezado:
# File: [Ruta relativa]
# ──────────────────────────────────────────────────────────────────────
# Propósito: [Descripción breve]
# Rol: [Función dentro del sistema]
# ──────────────────────────────────────────────────────────────────────

## 5. RECUPERACIÓN DE CONTEXTO Y ARQUITECTURA (MEMORIA A LARGO PLAZO)
Si en algún momento pierdes el hilo de la conversación, no tienes claridad sobre el objetivo actual, o necesitas tomar una decisión de arquitectura, TIENES PROHIBIDO adivinar o alucinar.

En caso de duda o pérdida de contexto, tu obligación es abrir y leer detenidamente los archivos ubicados en la carpeta docs/ de este proyecto (específicamente el Documento Maestro y el Plan de Implementación y otros documentos que se encuentren en esta carpeta).

Utiliza estos documentos como tu "fuente de verdad" para entender los modelos de la base de datos PostgreSQL, la estructura del proyecto y los requerimientos del negocio antes de proponer código nuevo.

Y si continuas con las dudas estas obligado a preguntar.