---
trigger: always_on
---

Paso 1: Preséntate al usuario e indícale que vas a realizar el Intake Operativo para asegurar que no haya errores de configuración.
Paso 2: Haz las siguientes preguntas al usuario de forma estructurada y espera su respuesta antes de continuar:
   A) Entorno: ¿Dónde correrá este código (Local WSL, VPS, Railway)? ¿Cómo se ejecutará (CLI, Web API)?
   B) Entradas: ¿Cuál es la ruta exacta de los archivos a procesar? ¿Hay formatos específicos?
   C) Salidas: ¿Dónde debo guardar los resultados? ¿Se permite sobrescribir archivos?
   D) Seguridad: ¿Se manejarán datos sensibles? ¿Existen restricciones de APIs externas?
Paso 3: Una vez que el usuario responda, haz un resumen de las variables operativas, confírmalas y pregunta si estás autorizado para comenzar a modificar o crear los archivos.