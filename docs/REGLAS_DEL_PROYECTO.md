# 📜 Reglas del Proyecto y Lineamientos de Desarrollo

Para asegurar la coherencia, escalabilidad y calidad de este MVP, todos los desarrollos deben adherirse estrictamente a las siguientes normas:

---

## 🧘 1. Filosofía: "Vamos despacio que tengo prisa"
- **Contextualización Obligatoria**: Antes de escribir una sola línea de código, el desarrollador (o IA) debe explicar el paso a paso de lo que se va a hacer. No se aceptan implementaciones "a ciegas".
- **Enfoque Estratégico**: Se prioriza la calidad arquitectónica sobre la velocidad de entrega bruta.

## 🏷️ 2. Nomenclatura Estricta
- **Nomenclatura**: Uso obligatorio y exclusivo de **`snake_case`** para todas las variables, funciones y nombres de archivos. 
  - *Ejemplo: `obtener_disponibilidad_servicio()` en lugar de `obtenerDisponibilidadServicio()`.*

## 🧼 3. Modificación y Calidad del Código
- **Código Limpio**: El código candidato debe estar libre de "código muerto" (comentarios obsoletos, variables no usadas) o redundancias.
- **Integridad Funcional**: Queda prohibido romper la funcionalidad original del código existente. Cada nueva pieza debe integrarse sin causar efectos secundarios negativos.
- **Regla del "Doble Chequeo"**: Cada entrega final debe ser revisada meticulosamente dos veces antes de darse por concluida.

## 🏗️ 4. Diseño Arquitectónico Universal
- **Modelo Agnóstico**: El sistema no se diseña exclusivamente para una barbería o una clínica, sino que utiliza un "Esquema Universal":
  - **Negocios**: Entidad principal que ofrece el servicio.
  - **Recursos**: Quien o que provee el servicio (personal, sala, equipo).
  - **Servicios**: El producto o actividad que se agenda (con duración y precio).
  - **Sujetos**: El cliente final que realiza la reserva.
- **Escalabilidad**: Esta estructura permite que el bot sea adaptable a cualquier sector comercial mediante configuración, sin rediseñar el núcleo.

## 🔒 5. Blindaje Multi-tenant y Aislamiento de Datos
- **Filtro Obligatorio**: Queda prohibido realizar consultas a tablas de negocio (Servicios, Citas, Recursos, etc.) sin filtrar explícitamente por `id_negocio`.
- **Integridad**: Ninguna operación de escritura o modificación debe permitirse sin validar la pertenencia del registro al negocio en sesión.

## 🔌 6. Configuración y Cero Hardcoding
- **Variables de Entorno**: Queda estrictamente prohibido dejar IDs, tokens, o URLs de base de datos "hardcodeados" en el código.
- **Externalización**: Todas las configuraciones variables deben residir en archivos `.env` o en el campo `configuracion_json` de la tabla `negocios`.

## 🔐 7. Reglas de Persistencia, Configuración y Trazabilidad
- **Sin hardcoding operativo**: Queda prohibido fijar manualmente valores como `id_negocio=1`, teléfonos, remitentes o configuraciones de entorno dentro del código productivo.
- **Aislamiento por negocio**: Toda consulta o mutación que afecte disponibilidad, festivos, excepciones, citas o exportaciones debe respetar explícitamente el `id_negocio` cuando aplique.
- **Logging obligatorio**: En módulos productivos se debe usar `logging.getLogger(__name__)`. El uso de `print()` queda reservado solo para scripts manuales o pruebas CLI aisladas.
- **Lecturas directas modernas**: Para lecturas simples por clave primaria se debe preferir `db.get(Modelo, id)` en lugar de patrones antiguos equivalentes.

---

> [!IMPORTANT]
> El incumplimiento de estas reglas será motivo de refactorización inmediata para alinearse con los estándares aquí documentados.
