# File: modules/admin.py
# ──────────────────────────────────────────────────────────────────────
# Propósito: Utilidades de gestión masiva de datos (Import/Export).
# Rol: Soporte administrativo (Etapa 6).
# ──────────────────────────────────────────────────────────────────────

import csv
import io
import logging
import os
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session

from database import crud
from database.models import Cita, Usuario, EntidadSujeto
from utils.validators import UsuarioCreate
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

def exportar_citas_csv(db: Session, id_negocio: int) -> str:
    """
    Genera un archivo CSV con el historial de citas.
    Codificación utf-8-sig para compatibilidad total con Excel.
    """
    citas = db.query(Cita).filter(Cita.id_negocio == id_negocio).all()
    
    filename = f"export_citas_{datetime.now(ZoneInfo('Europe/Madrid')).strftime('%Y%m%d_%H%M')}.csv"
    filepath = os.path.join("tmp", filename)
    os.makedirs("tmp", exist_ok=True)
    
    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID Cita", "Cliente", "Servicio", "Especialista", "Inicio", "Fin", "Estado", "Precio"])
        
        for c in citas:
            writer.writerow([
                c.id_cita,
                c.usuario.nombre_usuario if c.usuario else "N/A",
                c.servicio.nombre_servicio if c.servicio else "N/A",
                c.recurso.nombre_recurso if c.recurso else "N/A",
                c.fecha_hora_inicio.strftime("%Y-%m-%d %H:%M"),
                c.fecha_hora_fin.strftime("%Y-%m-%d %H:%M"),
                c.estado_cita,
                c.precio_cobrado
            ])
            
    return filepath

def exportar_citas_detalle_csv(db: Session, id_negocio: int) -> str:
    """
    Genera un CSV detallado con información completa de las citas del negocio.
    Codificación utf-8-sig para compatibilidad con Excel.
    """
    citas = crud.obtener_citas_detalladas_negocio(db, id_negocio)

    filename = f"export_citas_detalle_{datetime.now(ZoneInfo('Europe/Madrid')).strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join("tmp", filename)
    os.makedirs("tmp", exist_ok=True)

    with open(filepath, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "id_cita",
            "negocio",
            "cliente",
            "id_telegram",
            "especialista",
            "servicio",
            "perfil_servicio",
            "fecha_hora_inicio",
            "fecha_hora_fin",
            "estado_cita",
            "precio_cobrado",
            "calificacion_servicio",
            "fecha_calificacion",
            "dias_recordatorio_reagendamiento",
            "fecha_recordatorio_reagendamiento",
            "recordatorio_reagendamiento_enviado",
        ])

        for cita in citas:
            writer.writerow([
                cita.id_cita,
                cita.negocio.nombre_comercial if cita.negocio else "",
                cita.usuario.nombre_usuario if cita.usuario else "",
                cita.usuario.id_telegram if cita.usuario else "",
                cita.recurso.nombre_recurso if cita.recurso else "",
                cita.servicio.nombre_servicio if cita.servicio else "",
                cita.servicio.perfil_servicio if cita.servicio else "",
                cita.fecha_hora_inicio.strftime("%Y-%m-%d %H:%M") if cita.fecha_hora_inicio else "",
                cita.fecha_hora_fin.strftime("%Y-%m-%d %H:%M") if cita.fecha_hora_fin else "",
                cita.estado_cita or "",
                cita.precio_cobrado if cita.precio_cobrado is not None else "",
                cita.calificacion_servicio if cita.calificacion_servicio is not None else "",
                cita.fecha_calificacion.strftime("%Y-%m-%d %H:%M") if cita.fecha_calificacion else "",
                cita.dias_recordatorio_reagendamiento if cita.dias_recordatorio_reagendamiento is not None else "",
                cita.fecha_recordatorio_reagendamiento.strftime("%Y-%m-%d %H:%M") if cita.fecha_recordatorio_reagendamiento else "",
                "sí" if cita.recordatorio_reagendamiento_enviado else "no",
            ])

    logger.info(
        "Exportación detallada CSV completada. id_negocio=%s, total_citas=%s, archivo=%s",
        id_negocio,
        len(citas),
        filepath,
    )

    return filepath

def importar_clientes_csv(db: Session, id_negocio: int, csv_content: str) -> dict:
    """
    Lee un archivo CSV e importa usuarios a la base de datos masivamente.
    Usa Pydantic para validar los datos antes del insert.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    exitos = 0
    errores = 0
    
    for row in reader:
        try:
            # Validación con nuestro esquema Pydantic
            # Asumimos formato: id_telegram, nombre_usuario, correo_electronico, telefono
            user_in = UsuarioCreate(
                id_telegram=int(row["id_telegram"]),
                nombre_usuario=row["nombre_usuario"],
                correo_electronico=row["correo_electronico"],
                telefono=row.get("telefono"),
                acepta_privacidad=True
            )
            
            # Verificar si ya existe
            existente = db.query(Usuario).filter(Usuario.id_telegram == user_in.id_telegram).first()
            if not existente:
                nuevo_usuario = Usuario(
                    id_telegram=user_in.id_telegram,
                    nombre_usuario=user_in.nombre_usuario,
                    correo_electronico=user_in.correo_electronico,
                    telefono=user_in.telefono,
                    acepta_privacidad=True,
                    fecha_aceptacion_terminos=datetime.now(ZoneInfo("Europe/Madrid")),
                    version_terminos_aceptada="Import_CSV"
                )
                db.add(nuevo_usuario)
                db.flush()
                # Crear su entidad sujeto por defecto
                sujeto = EntidadSujeto(id_usuario_dueno=nuevo_usuario.id_usuario, nombre_sujeto=user_in.nombre_usuario)
                db.add(sujeto)
                exitos += 1
        except Exception as e:
            logger.exception("Fallo en la importación de fila %s: %s", row, e)
            db.rollback()
            errores += 1
            
    db.commit()
    logger.info(
        "Importación CSV finalizada. id_negocio=%s, exitos=%s, errores=%s",
        id_negocio,
        exitos,
        errores,
    )
    return {"exitos": exitos, "errores": errores}
