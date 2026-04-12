# 🚀 Plan de Implementación MVP - Bot de Agendamiento de Citas

Este documento detalla las 6 fases cruciales para el desarrollo y lanzamiento de nuestro MVP, garantizando una base sólida y escalable.

---

## 🗓️ Etapa 1: Infraestructura y Persistencia — ✅ Implementado en MVP
- **Modelado Universal**: Creación de un esquema agnóstico con aislamiento absoluto vía `id_negocio` en todas las tablas (incluyendo `DiaNoDisponible` y `ExcepcionHorario`).
- **Persistencia Híbrida**: Configuración de **SQLite** para desarrollo/MVP y **PostgreSQL** para producción, garantizando paridad de entornos.
- **ORM Moderno**: Implementación de **SQLAlchemy 2.0** utilizando el estándar `db.get()` para consultas.
- **Entorno**: Configuración centralizada vía `.env`.

## ⚙️ Etapa 2: Lógica de Negocio y Motor de Disponibilidad — ✅ Implementado
- **Algoritmo de Tiempo (Timezone Aware)**: Desarrollo del motor de slots basado estrictamente en `ZoneInfo("America/Bogota")`.
- **Gestión de Conflictos**: Implementación de lógica para evitar solapamientos de citas en tiempo real.
- **Validaciones**: Reglas para asegurar que las citas cumplan con los requisitos mínimos de tiempo y capacidad.

## 🤖 Etapa 3: Interfaz del Bot - Flujo del Usuario — ✅ Implementado (Reserva) / 🟡 Parcial (Gestión)
- **Experiencia de Usuario (UX)**: Diseño del flujo de conversación en **Telegram**.
- **Acciones Clave**: Desarrollo de comandos para:
  - **Reserva**: Selección de servicio, fecha y hora.
  - **Cancelación**: Gestión de citas existentes.
  - **Reagendamiento**: Cambio de día/hora de citas previas.

## 🛠️ Etapa 4: Módulo de Administración — 🟡 Parcial (Gestión Básica)
- **Control Centralizado**: Desarrollo de herramientas para que el administrador pueda:
  - Gestionar el catálogo de servicios (precios, descripciones, duraciones).
  - Configurar bloqueos manuales (días festivos, ausencias, descansos).
  - Cierre y apertura de agendas de manera dinámica.

## 🔔 Etapa 5: Sistema de Notificaciones — ✅ Implementado (Telegram/Scheduler) / 🟡 Parcial (Email)
- **Alertas en Tiempo Real**: Envío automático de confirmaciones vía Telegram.
- **Integración con Brevo (SendinBlue)**: Despacho de correos electrónicos transaccionales.
- **Recordatorios Inteligentes**: Programación con **APScheduler** para notificar al usuario con:
  - ⚡ 24 horas de antelación.
  - ⚡ 2 horas antes de la cita.

## 📊 Etapa 6: Calidad, Exportación y Despliegue — 🟡 Parcial (Exportación OK / Privacidad Básica)
- **Privacidad (Habeas Data)**: Implementación funcional de `/mi_privacidad` para anonimización y reporte.
- **Seguridad Admin**: Blindaje de rutas mediante validación `es_admin()`.
- **Lanzamiento (MVP)**: Verificación de estabilidad y despliegue inicial.

---

## 🚀 Roadmap Futuro (Post-MVP)

### 📈 Fase 2: Inteligencia y Crecimiento
- **Módulo de Cierre de Citas**: Gestión administrativa de finalización de servicios.
- **Filtro de Google Reviews**: Sistema de estrellas para optimizar SEO local.
- **Cazador de Sillas Vacías**: Optimización proactiva de la agenda.
- **Cerebro de Periodicidad**: Recordatorios inteligentes (ciclos de 21/30 días).

### 💰 Fase 3: Monetización y Escala
- **Control de Ingresos Extra (Upselling)**: Sugerencias de productos/servicios en el flujo.
- **Pasarela de Pagos**: Integración de abonos y señas.
- **Soporte Multicanal**: WhatsApp Business y Widgets Web.
