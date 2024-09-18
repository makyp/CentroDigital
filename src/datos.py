from bson import ObjectId
from datetime import datetime
class Usuario:
    def __init__(self, nombre, apellido, correo, password, role, cargo, habilidades):
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.password = password
        self.role = role
        self.cargo = cargo
        self.habilidades = habilidades
    
    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'apellido': self.apellido,
            'correo': self.correo,
            'password': self.password,
            'role': self.role,
            'cargo': self.cargo,
            'habilidades': self.habilidades,
        }

class Proyecto:
    def __init__(self, nombre, descripcion, fechainicio, fechafinal, estado):
        self.nombre = nombre
        self.descripcion = descripcion
        self.fechainicio = fechainicio
        self.fechafinal = fechafinal
        self.estado = estado
        self.tareas = []
        self.miembros = []
    
    def agregar_tarea(self, tarea):
        self.tareas.append(tarea)
    
    def asignar_miembro(self, miembro):
        self.miembros.append(miembro)
    
    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fechainicio': self.fechainicio,
            'fechafinal': self.fechafinal,
            'estado': self.estado,
            'tareas': [tarea.formato_doc() for tarea in self.tareas],
            'miembros': [miembro.formato_doc() for miembro in self.miembros],
        }

class Tarea:
    def __init__(self, proyecto, nombre, descripcion, fechavencimiento, miembroasignado, estado):
        self.proyecto = proyecto
        self.nombre = nombre
        self.descripcion = descripcion
        self.fechavencimiento = fechavencimiento
        self.miembroasignado = miembroasignado
        self.estado = estado
        self.comentarios = []
        self.tiempo_dedicado = 0
    
    def agregar_comentario(self, comentario):
        self.comentarios.append(comentario)
    
    def registrar_tiempo(self, horas):
        self.tiempo_dedicado += horas
    
    def formato_doc(self):
        return {
            'proyecto': self.proyecto,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fechavencimiento': self.fechavencimiento,
            'miembroasignado': self.miembroasignado.formato_doc() if self.miembroasignado else None,
            'estado': self.estado,
            'comentarios': self.comentarios,
            'tiempo_dedicado': self.tiempo_dedicado,
        }

class Comentario:
    def __init__(self, autor_id, contenido, fecha):
        self.autor_id = autor_id
        self.contenido = contenido
        self.fecha = fecha

    def formato_doc(self):
        return {
            'autor_id': self.autor_id,
            'contenido': self.contenido,
            'fecha': self.fecha
        }


class Mensaje:
    def __init__(self, remitente, destinatario, contenido, fecha=None, _id=None):
        self._id = _id if _id else ObjectId()
        self.remitente = remitente
        self.destinatario = destinatario
        self.contenido = contenido
        self.fecha = fecha if fecha else datetime.now()

    def formato_doc(self):
        return {
            '_id': self._id,
            'remitente': self.remitente,
            'destinatario': self.destinatario,
            'contenido': self.contenido,
            'fecha': self.fecha.isoformat()
        }