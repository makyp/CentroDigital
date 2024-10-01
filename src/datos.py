from bson import ObjectId
import re
import uuid
from datetime import datetime
class Usuario:
    def __init__(self, nombre, apellido, correo, password, role, cargo, habilidades):
        self.nombre = nombre
        self.apellido = apellido
        self.correo = correo
        self.password = password
        self.role = role
        self.cargo = cargo
       
        if isinstance(habilidades, str):
            self.habilidades = [h.strip() for h in re.split(r'\s*,\s*', habilidades)] #regex utilizada para omitir espacios en la elaboracion de la lista
            
        elif isinstance(habilidades, list):
            self.habilidades = habilidades
        else:
            self.habilidades = [] 
    
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
    
class Empresa:
    def __init__(self, nombre_empresa , correo_empresa, NIT, password):
        self.nombre_empresa = nombre_empresa
        self.correo_empresa = correo_empresa
        self.NIT = NIT
        self.password = password

    def formato_doc(self):
        return {
            'nombre': self.nombre_empresa,
            'correo': self.correo_empresa,
            'role':'empresa',
            'NIT': self.NIT,
            'password': self.password,
        }
    
class UserWithoutRegister:
     def __init__(self, nombre, correo, password, role):
        self.nombre = nombre
        self.correo = correo
        self.password = password
        self.role = role
      
    
     def formato_doc(self):
        return {
            'nombre': self.nombre,
            'correo': self.correo,
            'password': self.password,
            'role': self.role,
            'registroCompletado': False
        }

class ObjetivoEspecifico:
    def __init__(self, id, descripcion):
        self.id = id
        self.descripcion = descripcion     
     
class Proyecto:
    def __init__(self, nombre, descripcion, fechainicio, fechafinal, estado, objetivoGeneral, objetivosEspecificos):
        self.nombre = nombre
        self.descripcion = descripcion
        self.fechainicio = fechainicio
        self.fechafinal = fechafinal
        self.estado = estado
        self.objetivoGeneral = objetivoGeneral
        self.objetivosEspecificos = [ObjetivoEspecifico(i + 1, obj) for i, obj in enumerate(objetivosEspecificos)]  # Lista de ObjetivoEspecifico
        self.tareas = []  
        self.miembros = [] 

    def agregar_tarea(self, nombre, descripcion, fechavencimiento, objetivo_especifico_id, miembro_asignado=None, estado='pendiente'):
        # Verifica si el objetivo específico ID es válido
        if not any(objetivo.id == objetivo_especifico_id for objetivo in self.objetivosEspecificos):
            raise ValueError("El ID del objetivo específico no es válido")

        nueva_tarea = {
            'nombre': nombre,
            'descripcion': descripcion,
            'fechavencimiento': fechavencimiento,
            'miembroasignado': miembro_asignado,
            'estado': estado,
            'comentarios': [],  # Inicialmente vacío
            'tiempo_dedicado': 0  # Inicialmente 0
        }
        self.tareas.append(nueva_tarea)

    def asignar_miembro(self, miembro):
        self.miembros.append(miembro)



class ObjetivoEspecifico:
    def __init__(self, descripcion):
        self.id = str(uuid.uuid4())  # Genera un UUID único para cada objetivo
        self.descripcion = descripcion

    def to_dict(self):
        return {
            'id': self.id,
            'descripcion': self.descripcion
        }

    
    class Proyecto:
     
     def __init__(self, nombre, descripcion, fechainicio, fechafinal, estado, objetivoGeneral, objetivosEspecificos):
        self.nombre = nombre
        self.descripcion = descripcion
        self.fechainicio = fechainicio
        self.fechafinal = fechafinal
        self.estado = estado
        self.objetivoGeneral = objetivoGeneral
        self.objetivosEspecificos = self.generar_objetivos_con_id(objetivosEspecificos)  # Lista de objetivos con ID y descripción
        self.tareas = []  # Lista de tareas
        self.miembros = []  # Lista de miembros

    def generar_objetivos_con_id(self, descripciones_objetivos):
        """
        Genera una lista de objetivos específicos, cada uno con un ID único y una descripción.
        :param descripciones_objetivos: Lista de descripciones (cadenas de texto) para los objetivos.
        :return: Lista de instancias de ObjetivoEspecifico.
        """
        return [ObjetivoEspecifico(descripcion) for descripcion in descripciones_objetivos]

    def agregar_tarea(self, nombre, descripcion, fechavencimiento, objetivo_especifico_id, miembro_asignado=None, estado='pendiente'):
        """
        Agrega una nueva tarea asociada a un objetivo específico basado en el 'id' del objetivo.
        """
        # Verifica si el objetivo específico ID es válido
        if not any(objetivo.id == objetivo_especifico_id for objetivo in self.objetivosEspecificos):
            raise ValueError("El ID del objetivo específico no es válido")

        nueva_tarea = {
            'nombre': nombre,
            'descripcion': descripcion,
            'fechavencimiento': fechavencimiento,
            'miembroasignado': miembro_asignado,
            'estado': estado,
            'objetivo_especifico_id': objetivo_especifico_id,  # Asociar la tarea al ID del objetivo
            'comentarios': [],
            'tiempo_dedicado': 0
        }

        # Agrega la tarea a la lista de tareas del proyecto
        self.tareas.append(nueva_tarea)

    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fechainicio': self.fechainicio,
            'fechafinal': self.fechafinal,
            'estado': self.estado,
            'objetivoGeneral': self.objetivoGeneral,
            'objetivosEspecificos': [objeto.to_dict() for objeto in self.objetivosEspecificos],  # Convierte cada objeto a dict
            'tareas': self.tareas,
            'miembros': self.miembros,
        }


    def formato_doc(self):
        return {
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fechainicio': self.fechainicio,
            'fechafinal': self.fechafinal,
            'estado': self.estado,
            'objetivoGeneral': self.objetivoGeneral,
            'objetivosEspecificos': self.generar_objetivos_con_id(self.objetivosEspecificos),
            'tareas': self.tareas,  
            'miembros': self.miembros,  
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


