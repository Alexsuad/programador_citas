Documento Maestro: Sistema Universal de Agendamiento Inteligente (Bot de Citas Pro)

1. Introducción y Visión del Proyecto

Este proyecto surge como una respuesta estratégica a la brecha digital que enfrentan las pequeñas empresas de servicios en entornos competitivos. Mientras que las grandes cadenas y franquicias utilizan software costoso y ecosistemas complejos, el pequeño emprendedor suele quedar atrapado en la "parálisis de la gestión manual". El Bot de Citas Pro no es simplemente una herramienta de reservas; es un ecosistema de gestión y marketing proactivo diseñado para empoderar al dueño del negocio.

El núcleo del proyecto reside en un motor de reservas "agnóstico" y "multi-entidad". Bajo el principio de Recurso Universal, el sistema no ve "barberos" o "veterinarios", sino recursos_disponibles con capacidades específicas. Esto permite que el software sea reconfigurado en minutos para servir a una peluquería, una clínica canina, un centro de spa o incluso un estudio de tutorías privadas. La visión a largo plazo es democratizar el acceso a herramientas de alta tecnología (IA, analítica y automatización) para el sector de las Pymes.

2. Definición de Objetivos Estratégicos

Objetivo General

Desarrollar una plataforma de agendamiento inteligente basada en un Chatbot de Telegram que automatice el ciclo de vida completo de una cita —desde la captación inicial hasta la fidelización post-servicio— optimizando la operatividad del negocio y eliminando la dependencia de tareas administrativas manuales y propensas al error humano.

Objetivos Específicos

Automatización de Flujos (Eficiencia Operativa): Reducir en un 90% el tiempo que el dueño dedica a coordinar agendas por chat manual, permitiéndole enfocarse en la prestación del servicio.

Arquitectura Escalable (Multi-tenancy): Implementar una infraestructura en PostgreSQL que permita alojar múltiples negocios independientes de forma aislada, garantizando que los datos de un negocio nunca se mezclen con los de otro.

Marketing Predictivo y Retención: Crear un "Cerebro de Periodicidad" que aprenda de los hábitos de consumo de cada cliente (ej. un corte cada 22 días) para enviar recordatorios personalizados justo antes de que el cliente sienta la necesidad del servicio.

Blindaje de Reputación Digital: Diseñar un embudo de retroalimentación inteligente que proteja la imagen pública en Google Maps, desviando críticas a canales internos y fomentando proactivamente las reseñas de 5 estrellas.

Cumplimiento Legal y Ético: Integrar la gestión de consentimiento (Habeas Data / RGPD) de manera nativa en el flujo de bienvenida, asegurando que el negocio sea legalmente robusto ante cualquier auditoría.

3. Tabla de Contenido Detallada

Resumen Ejecutivo y Visión

El Problema: La "Trampa de la Gestión Manual" y el Costo de Oportunidad

La Solución: Arquitectura Basada en Chatbots vs. Apps Tradicionales

Análisis de Impacto, ROI y Productividad

Arquitectura Técnica: SQLAlchemy 2.0, SQLite/Postgres y Modelo Universal

Experiencia de Usuario (UX): El Arte del Agendamiento en 5 Clics

Estrategia de Fidelización: Inteligencia de Negocio y Ciclo del Cliente

Gestión de Datos: Interoperabilidad, Importación y Respaldo

Seguridad, Privacidad y Garantía de Calidad (QA)

Infraestructura, Despliegue en la Nube y Mantenimiento

Hoja de Ruta: Del MVP a la Plataforma SaaS Global

4. Explicación Profunda del Proyecto

4.1. El Problema: Contexto y "Dolores" del Negocio

La mayoría de los emprendedores en el sector servicios sufren de tres "dolores" críticos que estancan su crecimiento:

Fricción de Horario y Disponibilidad: Los clientes suelen querer agendar en momentos de descanso (11 PM o domingos). Si el dueño no responde de inmediato, el cliente busca otra opción en Google Maps. El 40% de las citas se pierden por lentitud en la respuesta.

El Costo de la "Silla Vacía" (No-Show): Una cita olvidada es una pérdida económica irrecuperable. Sin recordatorios automáticos escalonados, la tasa de inasistencia puede llegar al 25% del total de la agenda.

Falta de Memoria Comercial: Al usar cuadernos o chats manuales, el dueño pierde el rastro de quién dejó de venir. El negocio se vuelve puramente reactivo en lugar de proactivo.

4.2. La Solución: Un Motor de Reservas de Nueva Generación

Se ha seleccionado Telegram como interfaz principal por encima de WhatsApp o Apps nativas por razones técnicas y de costo:

Fricción Cero: No requiere descargas pesadas (si ya tienen la app) ni procesos de login complicados. El bot ya conoce el ID del usuario.

Costo de Desarrollo y Operación: Permite una lógica de teclados inline_buttons muy rica y segura sin los costos prohibitivos de las APIs oficiales de WhatsApp Business para emprendedores.

Rendimiento y Estabilidad: Las interacciones son instantáneas y la plataforma es altamente resistente a caídas de servicio.

Componentes Críticos del Motor:

Recursos y Especialistas: La base de datos es elástica. Si el negocio es una barbería, el recurso es el "Barbero". Si es un Spa, el recurso puede ser la "Cabina de Masaje". Esta abstracción es la que permite la universalidad del sistema.

Panel Administrativo /admin: Un centro de comando blindado donde el dueño puede bloquear agendas por emergencias, cambiar precios dinámicamente o descargar reportes financieros detallados sin necesidad de una computadora.

4.3. El Valor Diferencial: Impacto Real en el Negocio

El sistema se paga solo al generar un retorno medible:

Recuperación de Tiempo: El dueño recupera aproximadamente 15 horas semanales que antes perdía en el chat.

Aumento de la Tasa de Retorno: Al predecir cuándo el cliente necesita volver, se aumenta la frecuencia de visitas anuales de 8 a 12 por cliente recurrente.

SEO Local Orgánico: Al automatizar el flujo de reseñas positivas, el negocio escala posiciones en Google Maps, atrayendo tráfico "gratis" de personas que buscan servicios cercanos.

5. Diseño Técnico y Lógica de Datos

El sistema se construye sobre Python utilizando un enfoque orientado a objetos y una base de datos relacional gestionada con SQLAlchemy. En el MVP actual se utiliza SQLite para desarrollo, manteniendo compatibilidad estructural para PostgreSQL en producción.

Flexibilidad de Infraestructura:
Para el MVP y entorno de desarrollo se utiliza SQLite, manteniendo total compatibilidad con PostgreSQL para la migración a producción sin cambios en la lógica de negocio.

Gestión de Tiempo Precisa:
El manejo de fechas y horarios es "Timezone Aware", utilizando exclusivamente `ZoneInfo("Europe/Madrid")` para evitar desajustes en las citas.

Estructura de Datos y Multi-tenancy (Aislamiento Absoluto):

id_negocio: El pilar del multi-tenancy. Todas las tablas (incluyendo `DiaNoDisponible` y `ExcepcionHorario`) cuentan con esta llave foránea. Cada consulta SQL filtra estrictamente por este ID para garantizar la privacidad y el aislamiento de datos entre negocios.

metadatos_json: Aquí reside la flexibilidad del diseño. En lugar de crear columnas rígidas, usamos un campo JSON que se adapta según el negocio. Para una peluquería guardamos {"tipo_cabello": "graso"}, para una veterinaria guardamos {"raza": "Husky", "vacunas_al_dia": true}.

estado_cita: Una máquina de estados lógica que gestiona las transiciones (agendada -> recordada -> completada o cancelada). Cada cambio de estado dispara un evento (ej. enviar mensaje al barbero o liberar el slot de tiempo).

6. Seguridad, Privacidad y Calidad (QA)

Privacidad y consentimiento: El sistema ya incorpora un flujo inicial de consentimiento para el tratamiento de datos del usuario dentro del proceso de reserva. La gestión ampliada de privacidad y derechos del titular sigue prevista como evolución posterior del sistema.

Validación Administrativa: Las rutas y comandos administrativos están blindados mediante la validación obligatoria `es_admin()`, asegurando que solo personal autorizado gestione la configuración del negocio.

Validación de Datos con Pydantic: Se implementan esquemas de validación estrictos. Ningún dato entra a la base de datos sin ser verificado (teléfonos con formato correcto, correos válidos, fechas coherentes).

Resiliencia y Recuperación: El diseño contempla una futura estrategia de respaldos y recuperación. En el MVP actual, esta capa todavía no se encuentra implementada como mecanismo automatizado de producción.

7. Hoja de Ruta (Roadmap) Detallada

Fase 1: Saneamiento de Base y Arquitectura (COMPLETADA)
- **Aislamiento Multi-tenant**: Todas las tablas críticas cuentan con `id_negocio`.
- **Saneamiento de Modelos**: Corrección de defaults mutables en JSON (`default=dict`).
- **SQLAlchemy 2.0**: Migración exitosa a sintaxis moderna con `future=True`.
- **Cero Hardcoding**: Eliminación de IDs estáticos en bot y CRUD.

Fase 2: El Nacimiento del MVP (Foco: Retención y Operatividad)
- **UX de Alta Velocidad**: Flujo de agendamiento simplificado mediante botones interactivos para reducir la fricción del usuario.
- **Gestión de Reagendamiento**: El sistema permite mover citas de manera autónoma, liberando el espacio anterior instantáneamente para otros clientes.
- **Notificaciones Escalonadas**: Recordatorios inteligentes a las 24 horas y 2 horas antes de la cita para reducir el No-Show al mínimo.

Fase 2: Inteligencia y Crecimiento Proactivo

Módulo de Cierre de Citas: Finalización formal de citas para un control administrativo riguroso.

Filtro de Google Reviews: Implementación del sistema de estrellas que detecta la satisfacción y redirige estratégicamente a Google Maps para optimizar el SEO local.

Cazador de Sillas Vacías: Algoritmo proactivo que identifica huecos en la agenda y sugiere acciones para maximizar la ocupación.

Cerebro de Periodicidad: Sistema inteligente de recordatorios preventivos (ciclos de 21/30 días) basado en el historial del cliente.

Fase 3: Plataforma SaaS, Pagos y Monetización

Pasarela de Pagos Integrada: Cobro de señas o abonos iniciales (Stripe / Mercado Pago) para asegurar citas de alto valor.

Control de Ingresos Extra (Upselling): Módulo para ofrecer servicios o productos complementarios durante el proceso de reserva.

Análisis de Tendencias y BI: Un panel que le informa al dueño: "Tus martes de 2 a 4 PM están siempre vacíos, ¿quieres lanzar una promoción automática para ese bloque?".

Soporte Multicanal: Expansión de la misma lógica hacia WhatsApp Business y widgets web para captar clientes desde cualquier plataforma.

Nota Metódica: Cada etapa de este documento será validada con pruebas de usuario antes de pasar a la siguiente fase de desarrollo, manteniendo siempre el principio de código limpio y escalable.