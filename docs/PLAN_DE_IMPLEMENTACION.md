# 🚀 Plan de Implementación MVP - Bot de Agendamiento de Citas

Este documento detalla las 6 fases cruciales para el desarrollo y lanzamiento de nuestro MVP, garantizando una base sólida y escalable.

---

## 🗓️ Etapa 1: Infraestructura y Persistencia
- **Modelado Universal**: Creación de un esquema en **PostgreSQL** capaz de soportar negocios, recursos, servicios y sujetos de manera agnóstica al sector.
- **Conectividad**: Configuración de **SQLAlchemy** para la gestión de la base de datos y migraciones iniciales.
- **Entorno**: Asegurar que las variables de entorno (`.env`) y la configuración base de la API estén operativas.

## ⚙️ Etapa 2: Lógica de Negocio y Motor de Disponibilidad
- **Algoritmo de Tiempo**: Desarrollo del motor que calcula slots disponibles basándose en horarios de recursos y duración de servicios.
- **Gestión de Conflictos**: Implementación de lógica para evitar solapamientos de citas en tiempo real.
- **Validaciones**: Reglas para asegurar que las citas cumplan con los requisitos mínimos de tiempo y capacidad.

## 🤖 Etapa 3: Interfaz del Bot - Flujo del Usuario
- **Experiencia de Usuario (UX)**: Diseño del flujo de conversación en **Telegram**.
- **Acciones Clave**: Desarrollo de comandos para:
  - **Reserva**: Selección de servicio, fecha y hora.
  - **Cancelación**: Gestión de citas existentes.
  - **Reagendamiento**: Cambio de día/hora de citas previas.

## 🛠️ Etapa 4: Módulo de Administración
- **Control Centralizado**: Desarrollo de herramientas para que el administrador pueda:
  - Gestionar el catálogo de servicios (precios, descripciones, duraciones).
  - Configurar bloqueos manuales (días festivos, ausencias, descansos).
  - Cierre y apertura de agendas de manera dinámica.

## 🔔 Etapa 5: Sistema de Notificaciones
- **Alertas en Tiempo Real**: Envío automático de confirmaciones vía Telegram.
- **Integración con Brevo (SendinBlue)**: Despacho de correos electrónicos transaccionales.
- **Recordatorios Inteligentes**: Programación con **APScheduler** para notificar al usuario con:
  - ⚡ 24 horas de antelación.
  - ⚡ 2 horas antes de la cita.

## 📊 Etapa 6: Calidad, Exportación y Despliegue
- **Gestión de Datos**: Funcionalidad para exportar e importar historiales y citas mediante archivos **CSV**.
- **Pruebas Automatizadas**: Implementación de tests unitarios y de integración con **pytest**.
- **Lanzamiento (MVP)**: Verificación de estabilidad y despliegue inicial en entorno controlado.
