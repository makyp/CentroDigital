from bson import ObjectId
import re
import uuid
from datetime import datetime

class Usuario:
    def __init__(self, nombre, correo, password, role, habilidades):
        self.nombre = nombre
        self.correo = correo
        self.password = password
        self.role = role

        if isinstance(habilidades, str):
            self.habilidades = [h.strip() for h in re.split(r'\s*,\s*', habilidades)]  # regex para crear lista
        elif isinstance(habilidades, list):
            self.habilidades = habilidades
        else:
            self.habilidades = []

    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'correo': self.correo,
            'password': self.password,
            'role': self.role,
            'habilidades': self.habilidades,
        }

class Empresa:
    def __init__(self, nombre, correo, nit, encargado, telefono, password):
        self.nombre = nombre
        self.correo = correo
        self.nit = nit
        self.encargado = encargado
        self.telefono = telefono
        self.password = password

    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'correo': self.correo,
            'role': 'empresa',
            'nit': self.nit,
            'encargado': self.encargado,
            'telefono': self.telefono,
            'password': self.password
        }

class UserWithoutRegister:
    def __init__(self, nombre, correo, VerificationCode, role):
        self.nombre = nombre
        self.correo = correo
        self.VerificationCode = VerificationCode
        self.role = role
         
    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'correo': self.correo,
            'verficationCode': self.VerificationCode,
            'password': None,
            'role': self.role,
            'registroCompletado': False
        }

class ObjetivoEspecifico:
    def __init__(self, descripcion):
        self.id = str(uuid.uuid4())  # Genera un UUID único
        self.descripcion = descripcion

    def to_dict(self):
        return {
            'id': self.id,
            'descripcion': self.descripcion
        }
class Comentario:
    def __init__(self, nombre_autor, texto):
        self.nombre_autor = nombre_autor
        self.texto = texto
        self.fecha = datetime.now()  # Guarda la fecha y hora actual

    def to_dict(self):
        return {
            'nombre_autor': self.nombre_autor,
            'texto': self.texto,
            'fecha': self.fecha.isoformat()  # Convierte la fecha a formato ISO para almacenamiento
        }
class Proyecto:
    def __init__(self, nombre, descripcion, fechainicio, fechafinal, estado, objetivoGeneral, objetivosEspecificos,empresa_id,solicitud_id ):
        self.nombre = nombre
        self.descripcion = descripcion
        self.fechainicio = fechainicio
        self.fechafinal = fechafinal
        self.estado = estado
        self.objetivoGeneral = objetivoGeneral
        self.objetivosEspecificos = self.generar_objetivos_con_id(objetivosEspecificos)
        self.empresa_id= empresa_id
        self.solicitud_id= solicitud_id
        self.tareas = []  # Lista de tareas
        self.miembros = []  # Lista de miembros
        self.lideres = []

    def generar_objetivos_con_id(self, descripciones_objetivos):
        return [ObjetivoEspecifico(descripcion) for descripcion in descripciones_objetivos]

    def agregar_tarea(self, nombre, descripcion, fechavencimiento, objetivo_especifico_id, miembro_asignado=None, estado='pendiente'):
        if not any(objetivo.id == objetivo_especifico_id for objetivo in self.objetivosEspecificos):
            raise ValueError("El ID del objetivo específico no es válido")

        nueva_tarea = {
            'nombre': nombre,
            'descripcion': descripcion,
            'fechavencimiento': fechavencimiento,
            'miembroasignado': miembro_asignado,
            'estado': estado,
            'objetivo_especifico_id': objetivo_especifico_id,
            'comentarios': [],  # Inicialmente vacío
            'tiempo_dedicado': 0
        }

        self.tareas.append(nueva_tarea)

    def agregar_comentario_a_tarea(self, nombre_tarea, nombre_autor, texto):
        for tarea in self.tareas:
            if tarea['nombre'] == nombre_tarea:
                nuevo_comentario = Comentario(nombre_autor, texto)  # Crea un nuevo comentario
                tarea['comentarios'].append(nuevo_comentario.to_dict())  # Agrega el comentario a la tarea
                return  # Salir del método después de agregar el comentario
        raise ValueError("Tarea no encontrada.")

    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fechainicio': self.fechainicio,
            'fechafinal': self.fechafinal,
            'estado': self.estado,
            'objetivoGeneral': self.objetivoGeneral,
            'objetivosEspecificos': [objeto.to_dict() for objeto in self.objetivosEspecificos],
            'tareas': self.tareas,
            'miembros': self.miembros,
            'lideres': self.lideres 
        }