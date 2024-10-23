import datetime
import secrets
import random
from itsdangerous import URLSafeTimedSerializer
import string
from flask import request, session, flash, redirect, url_for, render_template
from bson.objectid import ObjectId
from flask_mail import Mail, Message 
from bson import ObjectId, errors as bson_errors
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from config import Conexion
from datos import *
from functions import *
from datetime import datetime
from operator import itemgetter
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv

if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')  # Valor por defecto 'smtp.gmail.com'
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))  # Convertir a entero
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'  # Convertir a booleano
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Usuario de correo desde las variables de entorno
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Contraseña del correo
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])  # Remitente
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'  # Convertir a booleano
app.config['MAIL_SUPPRESS_SEND'] = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
app.config['MAIL_ASCII_ATTACHMENTS'] = os.getenv('MAIL_ASCII_ATTACHMENTS', 'False').lower() == 'true'

# Inicializamos Mail
mail = Mail(app)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Conexión a la base de datos
db = Conexion()
usuarios_collection = db['usuarios']
proyectos_collection = db['proyectos']
tareas_collection = db['tareas']
solicitudes_collection = db['solicitudes']

def es_lider_usuario():
    return session.get('lider') == 'Si'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        
        # Consulta para buscar al usuario en la base de datos
        usuario = usuarios_collection.find_one({'correo': correo})
        
        # Verificar si el usuario existe
        if usuario:
            # Verificar si el registro está completo
            if not usuario.get('registroCompletado', False):
                flash('Debes completar tu registro antes de iniciar sesión.', 'warning')
                return redirect(url_for('login'))

            # Verificar si la contraseña es correcta
            if usuario['password'] and password.strip() and check_password_hash(usuario['password'], password):
                session['correo'] = usuario['correo']
                session['role'] = usuario['role']
                session['nombre'] = usuario['nombre']
                session['lider'] = usuario.get('lider', False)
                session['_id'] = str(usuario['_id'])
                
                # Si el usuario tiene el rol de empresa, almacenar el _id en la sesión
                if usuario['role'] == 'empresa':
                    session['empresa_id'] = str(usuario['_id'])  # Convertir ObjectId a string
                
                return redirect(url_for('perfil'))
            else:
                # Agregar mensaje flash de error si la contraseña es incorrecta
                flash('Correo o contraseña incorrectos.', 'danger')
        else:
            # Agregar mensaje flash de error si el usuario no existe
            flash('Correo o contraseña incorrectos.', 'danger')
    
    # Renderizar la página de inicio de sesión
    return render_template('inicio_sesion/login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if 'correo' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            nombre = request.form['nombre']
            correo = request.form['correo']
            role = request.form['role']
            if usuarios_collection.find_one({'correo': correo}):
                flash('El correo ya está registrado.')
            else:
                try:
                    VerificationCode = generar_contraseña()
                    s = URLSafeTimedSerializer(app.secret_key)
                    token = s.dumps(correo, salt='registro-usuario')
                    # Agregar campo 'lider' con valor 'No' por defecto
                    nuevo_usuario = {
                        "nombre": nombre,
                        "correo": correo,
                        "role": role,
                        "password": generate_password_hash(VerificationCode),  # Contraseña temporal generada
                        "registroCompletado": False,
                        "lider": "No"  # Por defecto, no es líder
                    }
                    usuarios_collection.insert_one(nuevo_usuario)

                    msg = enviar_correo_registro(correo, VerificationCode, token)
                    mail.send(msg)
                    flash('Registro exitoso. Se ha enviado un correo con tus credenciales.')
                except Exception as e:
                    flash(f'Error al enviar el correo: {str(e)}')
                return redirect(url_for('admin_usuarios'))
        return render_template('inicio_sesion/registro.html')
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('login'))

@app.route('/completar_registro/<token>', methods=['GET', 'POST'])
def completar_registro(token):
    try:
        s = URLSafeTimedSerializer(app.secret_key)
        email = s.loads(token, salt='registro-usuario', max_age=259200)  
        usuario = usuarios_collection.find_one({'correo': email})

        if not usuario:
            flash('Usuario no encontrado.')
            return redirect(url_for('login'))
        
        nombre_completo = usuario.get('nombre')  
        correo = usuario.get('correo')
        verificationCode = usuario.get('password')  # Este campo es la contraseña encriptada

        if request.method == 'POST':
            telefono = request.form.get('telefono')
            profesion = request.form.get('profesion')
            estudios = request.form.get('estudios')
            habilidades = request.form.get('habilidades')
            experiencia = request.form.get('experiencia')
            programa = request.form.get('programa')
            temp_Password = request.form['temp_password']
            new_password = request.form['new_password']
            
            # Verifica la contraseña temporal con la contraseña encriptada
            if not check_password_hash(verificationCode, temp_Password):
                flash('La contraseña temporal no coincide.')
                return redirect(url_for('completar_registro', token=token))
            

            if habilidades:
                habilidades_lista = [h.strip() for h in re.split(r'\s*,\s*', habilidades)]
            else:
                habilidades_lista = []

            usuarios_collection.update_one(
                {'correo': correo},
                {
                    '$set': {
                        'telefono': telefono,
                        'profesion': profesion,
                        'estudios': estudios,
                        'habilidades': habilidades_lista,
                        'experiencia': experiencia,
                        'programa': programa,
                        'password': generate_password_hash(new_password),
                        'registroCompletado': True  
                    }
                }
            )

            flash('Registro completado exitosamente.')
            return redirect(url_for('login'))
            
        return render_template('inicio_sesion/completar_registro.html',
                               nombre_completo=nombre_completo, correo=correo, token=token)
    except Exception as e:
        flash('El enlace de registro ha expirado o es inválido. Comuníquese con el administrador.')
        return redirect(url_for('login'))
    
@app.route('/logout')
def logout():
    session.pop('correo', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/admin_usuarios', methods=['GET', 'POST'])
def admin_usuarios():
    if 'correo' in session and session.get('role') == 'admin':
        # Filtrar usuarios cuyo role no sea "empresa"
        getusuarios = list(usuarios_collection.find({"role": {"$ne": "empresa"}}))
        
        return render_template('admin/admin_usuarios.html', usuarios=getusuarios)
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('login'))

@app.route('/admin_empresas', methods=['GET', 'POST'])
def admin_empresas():
    if 'correo' in session and session.get('role') == 'admin':
        # Filtrar usuarios cuyo role sea "empresa"
        getusuarios = list(usuarios_collection.find({"role": "empresa"}))
        
        return render_template('admin/admin_empresas.html', usuarios=getusuarios)
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('login'))

@app.route('/usuario/<id>/editar', methods=['POST'])
def editar_usuario(id):
    if 'correo' in session and session.get('role') == 'admin':
        data = request.get_json()  # Obtener los datos en formato JSON
        role = data.get('role')  # Extraer el nuevo rol

        if role:
            # Actualizar la base de datos
            usuarios_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {'role': role}}
            )
            flash('Usuario actualizado exitosamente.')
            return '', 200  # Responder con un código 200 OK
        
        return 'Faltan datos', 400  # Responder con un error si no hay rol
    else:
        return 'No tienes permisos', 403  # Responder con un error de permiso


@app.route('/usuario/<id>/eliminar', methods=['POST'])
def eliminar_usuario(id):
    if 'correo' in session and session.get('role') == 'admin':
        usuario = usuarios_collection.find_one({'_id': ObjectId(id)})
        if usuario:
            usuarios_collection.delete_one({'_id': ObjectId(id)})
            proyectos_collection.update_many(
                {'miembros._id': ObjectId(id)},
                {'$pull': {'miembros': {'_id': ObjectId(id)}}}
            )
            proyectos = proyectos_collection.find({'tareas.miembroasignado': ObjectId(id)})
            for proyecto in proyectos:
                for tarea in proyecto['tareas']:
                    if tarea['miembroasignado'] == str(id):
                        tarea['miembroasignado'] = None
                        tarea['miembro_nombre'] = "Sin asignar"
                proyectos_collection.update_one(
                    {'_id': proyecto['_id']},
                    {'$set': {'tareas': proyecto['tareas']}}
                )
            flash('Usuario eliminado exitosamente.')
        else:
            flash('No se encontró el usuario.')
        return redirect(url_for('admin_usuarios'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/admin_proyectos', methods=['GET', 'POST'])
def admin_proyectos():
    if 'correo' in session and session.get('role') == 'admin':
        # Obtener todos los proyectos
        proyectos = proyectos_collection.find()
        lista_proyectos = list(proyectos)  # Convierte a lista aquí
    elif 'correo' in session and session.get('lider') == 'Si':
        lider_id = str(session['_id'])  # Asegúrate de que _id esté en el formato correcto
        print(f'Líder ID en sesión: {lider_id}')  # Verifica el ID del líder

        # Buscar proyectos donde el líder está en la lista de líderes
        proyectos = proyectos_collection.find({'lideres._id': ObjectId(lider_id)})
        lista_proyectos = list(proyectos)  # Convierte a lista aquí
        ##print(f'Proyectos encontrados para el líder {lider_id}: {lista_proyectos}')  # Imprime los proyectos encontrados
    elif 'correo' in session and session.get('role') == 'empresa':
            # Obtener proyectos donde el usuario es parte de la empresa
            usuario_id = str(session['_id'])
            print(f'Empresa ID en sesión: {usuario_id}')
            proyectos = proyectos_collection.find({'empresa_id': ObjectId(usuario_id)})
            print(f'Empresa ID en sesión: {proyectos}')
            lista_proyectos = list(proyectos)
    else:
        flash('No tienes permisos para realizar esta acción.')
        return redirect(url_for('login'))

    print(f'Lista de proyectos: {lista_proyectos}')  # Imprime la lista de proyectos

    for proyecto in lista_proyectos:
        # Buscar la empresa relacionada usando 'id_empresa'
        empresa_id = proyecto.get('empresa_id')
        if empresa_id:
            empresa = usuarios_collection.find_one({'_id': ObjectId(empresa_id)}, {'nombre': 1})
            if empresa:
                proyecto['nombre_empresa'] = empresa['nombre']
            else:
                proyecto['nombre_empresa'] = "Empresa no encontrada"
        else:
            proyecto['nombre_empresa'] = "Sin empresa asignada"

        # Buscar la solicitud relacionada usando 'solicitud_id'
        solicitud_id = proyecto.get('solicitud_id')
        if solicitud_id:
            solicitud = solicitudes_collection.find_one({'_id': ObjectId(solicitud_id)}, {'nombre': 1})
            if solicitud:
                proyecto['nombre_solicitud'] = solicitud['nombre']
            else:
                proyecto['nombre_solicitud'] = "Solicitud no encontrada"
        else:
            proyecto['nombre_solicitud'] = "Sin solicitud asignada"

        # Opcional: Reemplazar el ID del miembro asignado por su nombre completo en las tareas
        for tarea in proyecto.get('tareas', []):
            miembro_id = tarea.get('miembro_asignado')  # el 'id' del miembro asignado
            if miembro_id:
                miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1})
                if miembro:
                    tarea['miembro_asignado'] = miembro['nombre']
                else:
                    tarea['miembro_asignado'] = "Sin asignar"
            else:
                tarea['miembro_asignado'] = "Sin asignar"

    return render_template('admin/admin_proyectos.html', proyectos=lista_proyectos)


@app.route('/indicadores/<proyecto_id>', methods=['GET'])
def ver_indicadores(proyecto_id):
    if 'correo' in session:
        # Obtener el proyecto por ID
        proyecto = proyectos_collection.find_one({'_id': ObjectId(proyecto_id)})
        if not proyecto:
            flash('Proyecto no encontrado.')
            return redirect(url_for('admin_proyectos'))

        # Obtener las tareas, si no existen, dejarlas como lista vacía
        tareas = proyecto.get('tareas', [])  # Esto evita el KeyError si 'tareas' no está presente

        # Contar las tareas y sus estados
        total_tareas = len(tareas)
        por_iniciar = sum(1 for tarea in tareas if tarea.get('estado') == 'Por iniciar')
        en_progreso = sum(1 for tarea in tareas if tarea.get('estado') == 'En progreso')
        completadas = sum(1 for tarea in tareas if tarea.get('estado') == 'Completado')

        # Convertir ObjectId a cadena
        proyecto['_id'] = str(proyecto['_id'])
        for tarea in tareas:
            tarea['_id'] = str(tarea['_id']) if '_id' in tarea else tarea.get('_id')  # Convierte el id de la tarea si existe

        # Renderizar la plantilla de indicadores
        return render_template('admin/indicadores.html', 
                               proyecto=proyecto, 
                               total_tareas=total_tareas, 
                               por_iniciar=por_iniciar, 
                               en_progreso=en_progreso, 
                               completadas=completadas,
                               tareas=tareas)  # Asegúrate de pasar `tareas` a la plantilla

    flash('Debes iniciar sesión para ver los indicadores.')
    return redirect(url_for('login'))

@app.route('/proyecto/<id>/editar', methods=['GET', 'POST'])
def editar_proyecto(id):
    if 'correo' in session and (session.get('role') == 'admin' or session.get('lider') == 'Si'):
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        
        if not proyecto:
            flash('No se encontró el proyecto.')
            return redirect(url_for('admin_proyectos'))

        if request.method == 'POST':
            # Obtener información anterior del proyecto
            proyecto_anterior = proyecto.copy()  # Hacer una copia para el correo
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            objetivoGeneral = request.form.get('objetivoGeneral')
            fechainicio = request.form.get('fechainicio')
            fechafinal = request.form.get('fechafinal')
            estado = request.form.get('estado')
            objetivos_ids = request.form.getlist('objetivos_especificos_ids')
            objetivos_descripciones = request.form.getlist('objetivos_especificos')

            # Actualizar la información del proyecto
            proyectos_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechainicio': fechainicio,
                    'fechafinal': fechafinal,
                    'estado': estado,
                    'objetivoGeneral': objetivoGeneral
                }}
            )

            # Actualizar los objetivos específicos
            nuevos_objetivos = []
            for obj_id, descripcion in zip(objetivos_ids, objetivos_descripciones):
                if descripcion.strip():  # Si la descripción no está vacía
                    nuevos_objetivos.append({
                        'id': obj_id if obj_id else str(uuid.uuid4()),  # Generar un nuevo ID si es un objetivo nuevo
                        'descripcion': descripcion
                    })

            proyectos_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {'objetivosEspecificos': nuevos_objetivos}}
            )

            # Obtener los correos de los administradores
            admins = usuarios_collection.find({'role': 'admin'}, {'correo': 1})
            admin_emails = [admin['correo'] for admin in admins]
            objetivos_antiguos = [obj['descripcion'] for obj in proyecto_anterior.get('objetivosEspecificos', [])]
            objetivos_nuevos = [obj['descripcion'] for obj in nuevos_objetivos]

            # Preparar el correo
            msg = Message('Cambio en Proyecto', recipients=admin_emails)  # Usar la lista de correos
            msg.body = f"""
            Se han realizado cambios en el proyecto '{proyecto['nombre']}'.
            
            Información anterior:
            Nombre: {proyecto_anterior['nombre']}
            Descripción: {proyecto_anterior['descripcion']}
            Fecha Inicio: {proyecto_anterior['fechainicio']}
            Fecha Final: {proyecto_anterior['fechafinal']}
            Estado: {proyecto_anterior['estado']}
            Objetivos específicos: {objetivos_antiguos}
            
            Nueva información:
            Nombre: {nombre}
            Descripción: {descripcion}
            Fecha Inicio: {fechainicio}
            Fecha Final: {fechafinal}
            Estado: {estado}
            Objetivos específicos: {objetivos_nuevos}
            """
            mail.send(msg)

            flash('Proyecto actualizado exitosamente y notificación enviada a los administradores.')
            return redirect(url_for('admin_proyectos'))

        # Aquí, carga los objetivos específicos en el contexto de la plantilla
        objetivos_especificos = proyecto.get('objetivosEspecificos', [])
        
        return render_template('admin/editar_proyecto.html', proyecto=proyecto, objetivos_especificos=objetivos_especificos)

    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/proyecto/<id>/eliminar')
def eliminar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyectos_collection.delete_one({'_id': ObjectId(id)})
        flash('Proyecto eliminado exitosamente.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/proyecto/<id>/asignar_miembros', methods=['GET', 'POST'])
def asignar_miembros(id):
    if session.get('role') == 'admin' or session.get('lider') == 'Si':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if proyecto:
            # Inicializar la lista 'miembros' si no existe
            if 'miembros' not in proyecto:
                proyecto['miembros'] = []
            
            # Inicializar la lista 'lideres' si no existe
            if 'lideres' not in proyecto:
                proyecto['lideres'] = []

            if request.method == 'POST':
                # Procesar la eliminación de miembros seleccionados
                eliminar_miembros_seleccionados = request.form.getlist('eliminar_miembro')
                if eliminar_miembros_seleccionados:
                    for miembro_id in eliminar_miembros_seleccionados:
                        miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)})
                        if miembro:
                            # Enviar notificación por correo
                            msg = Message(f'Removido del proyecto: {proyecto["nombre"]}', 
                                          sender=app.config['MAIL_DEFAULT_SENDER'], 
                                          recipients=[miembro['correo']])
                            msg.body = f"Has sido eliminado del proyecto {proyecto['nombre']}."
                            mail.send(msg)
                    
                    # Actualizar la lista de miembros del proyecto
                    proyecto['miembros'] = [miembro for miembro in proyecto['miembros'] if str(miembro['_id']) not in eliminar_miembros_seleccionados]
                    proyecto['lideres'] = [lider for lider in proyecto.get('lideres', []) if str(lider['_id']) not in eliminar_miembros_seleccionados]  # Eliminar también de líderes
                
                # Procesar la adición de miembros seleccionados
                agregar_miembros_seleccionados = request.form.getlist('agregar_miembro')
                for miembro_id in agregar_miembros_seleccionados:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)})
                    if miembro:
                        proyecto['miembros'].append(miembro)
                        # Enviar notificación por correo
                        msg = Message(f'Asignado al proyecto: {proyecto["nombre"]}', 
                                      sender=app.config['MAIL_DEFAULT_SENDER'], 
                                      recipients=[miembro['correo']])
                        msg.body = f"Has sido agregado al proyecto {proyecto['nombre']}."
                        mail.send(msg)
                
                # Procesar la asignación de líderes seleccionados
                lideres_seleccionados = request.form.getlist('asignar_lider')
                
                # Verificar si ya hay un líder asignado
                if proyecto['lideres'] and lideres_seleccionados:
                    flash('Ya existe un líder asignado a este proyecto. No se puede asignar otro líder.')
                else:
                    for lider_id in lideres_seleccionados:
                        lider = usuarios_collection.find_one({'_id': ObjectId(lider_id)})
                        if lider and lider not in proyecto.get('lideres', []):
                            if 'lideres' not in proyecto:
                                proyecto['lideres'] = []
                            proyecto['lideres'].append(lider)

                            # Actualizar campo 'lider' del usuario a 'Si'
                            usuarios_collection.update_one({'_id': ObjectId(lider_id)}, {'$set': {'lider': 'Si'}})

                        # Enviar notificación por correo
                        msg = Message(f'Asignado como líder en el proyecto: {proyecto["nombre"]}', 
                                      sender=app.config['MAIL_DEFAULT_SENDER'], 
                                      recipients=[lider['correo']])
                        msg.body = f"Has sido asignado como líder en el proyecto {proyecto['nombre']}."
                        mail.send(msg)

                # Verificar si el miembro removido es líder en otro proyecto
                for miembro_id in eliminar_miembros_seleccionados:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)})
                    if miembro:
                        # Comprobar si el miembro sigue siendo líder en otros proyectos
                        otros_proyectos_count = proyectos_collection.count_documents({'lideres._id': ObjectId(miembro_id)})
                        if otros_proyectos_count == 0:  # No es líder en ningún otro proyecto
                            usuarios_collection.update_one({'_id': ObjectId(miembro_id)}, {'$set': {'lider': 'No'}})

                # Actualizar el proyecto en la base de datos
                proyectos_collection.update_one({'_id': ObjectId(id)}, {'$set': proyecto})
                
                flash('Acciones de asignación de miembros y líderes realizadas exitosamente.')
                return redirect(url_for('admin_proyectos'))
            
            usuarios = usuarios_collection.find({"registroCompletado": True})
            return render_template('admin/asignar_miembros.html', proyecto=proyecto, usuarios=usuarios)
        else:
            flash('No se encontró el proyecto.')
            return redirect(url_for('admin_proyectos'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))



@app.route('/seleccionar_proyecto', methods=['GET', 'POST'])
def seleccionar_proyecto():
    if 'correo' in session:
        # Verificar si el usuario es admin o líder
        if session.get('role') == 'admin' or session.get('lider') == 'Si':
            if request.method == 'POST':
                proyecto_id = request.form.get('proyecto_id')
                if not proyecto_id:
                    flash('Debes seleccionar un proyecto.')
                    return redirect(url_for('seleccionar_proyecto'))
                print(f'Proyecto seleccionado: {proyecto_id}')
                return redirect(url_for('agregar_tarea', proyecto_id=proyecto_id))
            
            # Si es un GET, obtenemos los proyectos
            proyectos = proyectos_collection.find()
            return render_template('admin/seleccionar_proyecto.html', proyectos=proyectos)

        # Si el usuario no es admin ni líder
        flash('No tienes permisos para realizar esta acción.')
        return redirect(url_for('login'))
    
    # Si no hay sesión
    flash('Debes iniciar sesión.')
    return redirect(url_for('login'))


@app.route('/proyecto/<proyecto_id>/agregar_tarea/', methods=['GET', 'POST'])
def agregar_tarea(proyecto_id):
    if 'correo' in session:
        # Verificación de admin
        if session.get('role') == 'admin':
            proyecto = proyectos_collection.find_one({'_id': ObjectId(proyecto_id)})
        
        # Verificación de líder
        elif session.get('lider') == 'Si':
            lider_id = str(session['_id'])  # Asegúrate de que _id esté en el formato correcto
            print(f'Líder ID en sesión: {lider_id}') 
            
            # Encuentra el proyecto en el que el usuario es líder
            proyecto = proyectos_collection.find_one({'_id': ObjectId(proyecto_id), 'lideres._id': ObjectId(lider_id)})
            print(f'Proyecto encontrado para el líder {lider_id}: {proyecto}')  # Imprime el proyecto encontrado

        else:
            flash('No tienes permisos para realizar esta acción.')
            return redirect(url_for('login'))

        # Si se encuentra el proyecto
        if proyecto:
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']
                miembro_asignado = request.form.get('miembro_asignado')
                estado = request.form.get('estado')
                objetivo_especifico_id = request.form['objetivo_especifico_id']

                # Validar que el objetivo específico pertenece al proyecto
                if objetivo_especifico_id not in [obj['id'] for obj in proyecto.get('objetivosEspecificos', [])]:
                    raise ValueError("El ID del objetivo específico no es válido")

                nueva_tarea = {
                    '_id': ObjectId(),
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechavencimiento': fechavencimiento,
                    'miembro_asignado': miembro_asignado,
                    'estado': estado,
                    'objetivo_especifico_id': objetivo_especifico_id
                }

                proyectos_collection.update_one(
                    {'_id': ObjectId(proyecto_id)},
                    {'$push': {'tareas': nueva_tarea}}
                )

                return redirect(url_for('ver_todas_las_tareas'))

            # Obtener miembros del proyecto
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))

            return render_template('admin/agregar_tarea.html', proyecto=proyecto, usuarios=miembros_asignados)

        # Si el proyecto no fue encontrado
        flash('No tienes permiso para agregar tareas en este proyecto.')
        return redirect(url_for('admin_proyectos'))

    # Si el usuario no tiene permisos
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/tareas', methods=['GET'])
def ver_todas_las_tareas():
    if 'correo' in session:
        usuario_id = session.get('_id')
        filtro_proyecto = request.args.get('proyecto')  # Filtro de nombre de proyecto
        filtro_miembro = request.args.get('miembro')  # Filtro de miembro asignado
        
        proyectos = []

        # Verificación de si el usuario es admin
        if session.get('role') == 'admin':
            # Si es admin, puede ver todas las tareas de todos los proyectos
            proyectos = proyectos_collection.find()

        # Verificación de si el usuario es líder
        elif session.get('lider') == 'Si':
            # Si es líder, puede ver las tareas solo de los proyectos donde es líder
            proyectos = proyectos_collection.find({'lideres._id': ObjectId(usuario_id)})

        else:
            flash('No tienes permisos para realizar esta acción.')
            return redirect(url_for('login'))

        # Procesar los proyectos y sus tareas
        tareas = []

        for proyecto in proyectos:
            # Filtro de proyectos por nombre
            if filtro_proyecto and filtro_proyecto.lower() not in proyecto['nombre'].lower():
                continue 

            for tarea in proyecto.get('tareas', []):
                miembro_id = tarea.get('miembro_asignado')
                miembro_nombre = "Sin asignar"

                # Buscar el nombre del miembro asignado
                if miembro_id:
                    if isinstance(miembro_id, str):  
                        try:
                            miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1})
                            if miembro and 'nombre' in miembro:
                                miembro_nombre = miembro['nombre']
                        except Exception as e:
                            print(f"Error al convertir miembro_id a ObjectId: {e}")
                
                tarea['miembro_nombre'] = miembro_nombre
                tarea['proyecto_nombre'] = proyecto['nombre']
                tarea['proyecto_id'] = proyecto['_id']
                tarea['proyecto_objetivoGeneral'] = proyecto.get('objetivoGeneral', 'Sin objetivo general')
                
                # Buscar el nombre del objetivo específico relacionado
                objetivo_especifico_id = tarea.get('objetivo_especifico_id')
                objetivo_especifico_nombre = "Objetivo no encontrado"
                
                if objetivo_especifico_id and 'objetivosEspecificos' in proyecto:
                    for objetivo in proyecto['objetivosEspecificos']:
                        if objetivo.get('id') == objetivo_especifico_id:
                            objetivo_especifico_nombre = objetivo.get('descripcion', 'descripcion no definida')
                            break
                
                tarea['objetivo_especifico_nombre'] = objetivo_especifico_nombre
                
                # Filtro de miembro asignado
                if filtro_miembro and filtro_miembro.lower() not in miembro_nombre.lower():
                    continue  

                tareas.append(tarea)

        return render_template('admin/ver_tareas.html', tareas=tareas)

    # Redirigir si no tiene permisos
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/tareas_general')
def ver_tareas_general():
    if 'correo' in session:
        # Obtener todos los proyectos
        proyectos = proyectos_collection.find()
        tareas = []

        for proyecto in proyectos:
            for tarea in proyecto.get('tareas', []):
                # Añadir detalles del proyecto a la tarea
                tarea['proyecto_nombre'] = proyecto['nombre']
                tarea['proyecto_id'] = str(proyecto['_id'])  # Convertir a string para evitar problemas de visualización
                tarea['proyecto_objetivoGeneral'] = proyecto.get('objetivoGeneral', 'Sin objetivo general')

                # Añadir el nombre del miembro asignado
                miembro_id = tarea.get('miembroasignado')  # Corrige la clave de acceso a 'miembroasignado'
                miembro_nombre = "Sin asignar"
                if miembro_id:
                    try:
                        miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1})
                        if miembro and 'nombre' in miembro:
                            miembro_nombre = miembro['nombre']
                    except Exception as e:
                        print(f"Error al convertir miembro_id a ObjectId: {e}")

                tarea['miembro_nombre'] = miembro_nombre
                
                # Añadir el nombre del objetivo específico
                objetivo_especifico_id = tarea.get('objetivo_especifico_id')
                objetivo_especifico_nombre = "Objetivo no encontrado"
                if objetivo_especifico_id and 'objetivosEspecificos' in proyecto:
                    for objetivo in proyecto['objetivosEspecificos']:
                        if objetivo.get('id') == objetivo_especifico_id:
                            objetivo_especifico_nombre = objetivo.get('descripcion', 'Descripción no definida')
                            break
                tarea['objetivo_especifico_nombre'] = objetivo_especifico_nombre
                
                # Añadir comentarios (se asume que cada comentario tiene 'nombre_autor', 'texto' y 'fecha')
                tarea['comentarios'] = tarea.get('comentarios', [])
                
                # Añadir la tarea a la lista de tareas
                tareas.append(tarea)

        # Renderizar la plantilla con las tareas
        return render_template('ver_todas_las_tareas.html', tareas=tareas)

    flash('Debes iniciar sesión para ver las tareas.')
    return redirect(url_for('login'))

@app.route('/proyecto/<proyecto_id>/tarea/<tarea_id>/comentar', methods=['POST'])
def comentar_tarea(proyecto_id, tarea_id):
    if request.method == 'POST':
        contenido = request.form['contenido']
        autor = session['nombre']
        comentario = {'nombre_autor': autor, 'texto': contenido, 'fecha': datetime.now().isoformat()}

        # Encuentra el proyecto correspondiente
        proyecto = proyectos_collection.find_one({'_id': ObjectId(proyecto_id)})
        if proyecto:
            # Encuentra la tarea usando el ID de la tarea
            tarea_filtrada = [tarea for tarea in proyecto.get('tareas', []) if tarea['_id'] == ObjectId(tarea_id)]
            
            if tarea_filtrada:
                # Agrega el comentario a la tarea
                proyectos_collection.update_one(
                    {'_id': ObjectId(proyecto_id), 'tareas._id': ObjectId(tarea_id)},
                    {'$push': {'tareas.$.comentarios': comentario}}
                )
                flash('Comentario agregado exitosamente.')
                return redirect(url_for('ver_tareas_general'))
        
        flash('Error al agregar el comentario.', 'danger')
    return redirect(url_for('ver_tareas_general'))

@app.route('/tarea/<id>/editar', methods=['GET', 'POST'])
def editar_tarea(id):
    if 'correo' in session:
        usuario_id = session.get('_id')
        
        # Buscar el proyecto que contiene la tarea
        proyecto = None

        # Verificar si es admin
        if session.get('role') == 'admin':
            # Si es admin, buscar el proyecto que contiene la tarea sin restricciones
            proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})

        # Verificar si es líder
        elif session.get('lider') == 'Si':
            # Si es líder, buscar el proyecto y verificar que el usuario es líder del proyecto
            proyecto = proyectos_collection.find_one({
                'tareas._id': ObjectId(id),
                'lideres._id': ObjectId(usuario_id)  # Verifica si el usuario es líder del proyecto
            })

        # Si no es ni admin ni líder, denegar acceso
        if not proyecto:
            flash('No se encontró la tarea o no tienes permisos para editarla.')
            return redirect(url_for('ver_todas_las_tareas'))

        # Buscar la tarea dentro del proyecto
        tarea = next((t for t in proyecto['tareas'] if t['_id'] == ObjectId(id)), None)
        
        # Convertir miembro_asignado a cadena
        tarea['miembro_asignado'] = str(tarea['miembro_asignado']) if tarea['miembro_asignado'] else None

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            fechavencimiento = request.form.get('fechavencimiento')
            miembro_asignado = request.form.get('miembro_asignado')
            estado = request.form.get('estado')
            objetivo_especifico_id = request.form.get('objetivo_especifico')

            try:
                proyectos_collection.update_one(
                    {'_id': proyecto['_id'], 'tareas._id': ObjectId(id)},
                    {'$set': {
                        'tareas.$.nombre': nombre,
                        'tareas.$.descripcion': descripcion,
                        'tareas.$.fechavencimiento': fechavencimiento,
                        'tareas.$.miembro_asignado': miembro_asignado,
                        'tareas.$.estado': estado,
                        'tareas.$.objetivo_especifico_id': objetivo_especifico_id
                    }}
                )
                flash('Tarea actualizada exitosamente.')
                
                # Enviar correo de notificación al miembro asignado
                if miembro_asignado:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_asignado)})
                    if miembro:
                        msg = Message(
                            subject=f'Actualización de Tarea: {nombre}',
                            recipients=[miembro['correo']]
                        )
                        msg.body = f"""
                        Estimado(a) {miembro['nombre']},

                        La tarea "{nombre}" ha sido actualizada. 

                        Descripción: {descripcion}
                        Fecha de vencimiento: {fechavencimiento}
                        Estado: {estado}

                        Si tienes alguna pregunta, no dudes en contactarnos.

                        Saludos,
                        Tu Equipo
                        """
                        mail.send(msg)

                return redirect(url_for('ver_todas_las_tareas'))
            except Exception as e:
                flash('Error al actualizar la tarea.', 'danger')
                print(f'Error: {e}')

        # Obtener los miembros del proyecto y convertir sus ObjectId a cadenas
        miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
        miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
        for miembro in miembros_asignados:
            miembro['_id'] = str(miembro['_id'])  # Convertir a cadena

        return render_template(
            'admin/editar_tarea.html', 
            tarea=tarea, 
            proyecto=proyecto, 
            miembros=miembros_asignados,
            objetivos_especificos=proyecto.get('objetivosEspecificos', [])
        )
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/tarea/<id>/eliminar', methods=['POST'])
def eliminar_tarea(id):
    if 'correo' in session:
        usuario_id = session.get('_id')

        # Buscar el proyecto que contiene la tarea
        proyecto = None

        # Verificar si es admin
        if session.get('role') == 'admin':
            # Si es admin, permitir eliminar sin restricciones
            proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})

        # Verificar si es líder
        elif session.get('lider') == 'Si':
            # Si es líder, verificar que el usuario es líder del proyecto
            proyecto = proyectos_collection.find_one({
                'tareas._id': ObjectId(id),
                'lideres._id': ObjectId(usuario_id)  # Verifica si el usuario es líder del proyecto
            })

        # Si no es ni admin ni líder, denegar acceso
        if not proyecto:
            flash('No se encontró la tarea o no tienes permisos para eliminarla.')
            return redirect(url_for('ver_todas_las_tareas'))

        try:
            # Eliminar la tarea del proyecto
            proyectos_collection.update_one(
                {'_id': proyecto['_id']},
                {'$pull': {'tareas': {'_id': ObjectId(id)}}}
            )
            flash('Tarea eliminada exitosamente.')

            # Enviar notificación al miembro asignado
            tarea = next((t for t in proyecto['tareas'] if t['_id'] == ObjectId(id)), None)
            if tarea and tarea['miembro_asignado']:
                miembro = usuarios_collection.find_one({'_id': ObjectId(tarea['miembro_asignado'])})
                if miembro:
                    msg = Message(
                        subject=f'Eliminación de Tarea: {tarea["nombre"]}',
                        sender='centrodigitaldedesarrollotecno@gmail.com',
                        recipients=[miembro['correo']]
                    )
                    msg.body = f"""
                    Estimado(a) {miembro['nombre']},

                    La tarea "{tarea["nombre"]}" ha sido eliminada.

                    Si tienes alguna pregunta, no dudes en contactarnos.

                    Saludos,
                    Tu Equipo
                    """
                    mail.send(msg)

        except Exception as e:
            flash('Error al eliminar la tarea.', 'danger')
            print(f'Error: {e}')

        return redirect(url_for('ver_todas_las_tareas'))

    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    if 'correo' in session:
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        if usuario:
            # Si el usuario es una empresa, buscar proyectos por el campo 'empresa_id'
            if usuario['role'] == 'empresa':
                proyectos = list(proyectos_collection.find({'empresa_id': usuario['_id']}))
                tareas_asignadas = []  # Las empresas no tienen tareas asignadas

            # Si es miembro o admin, buscar proyectos por los miembros del proyecto
            elif usuario['role'] == 'miembro' or usuario['role'] == 'admin':
                proyectos = list(proyectos_collection.find({'miembros._id': usuario['_id']}))
                tareas_asignadas = []
                for proyecto in proyectos:
                    for tarea in proyecto.get('tareas', []):
                        # Comparar el ID del miembro asignado como string
                        if str(tarea.get('miembro_asignado')) == str(usuario['_id']):
                            tarea_info = {
                                'nombre': tarea['nombre'],
                                'descripcion': tarea['descripcion'],
                                'estado': tarea['estado'],
                                'proyecto': proyecto['nombre']
                            }
                            tareas_asignadas.append(tarea_info)

            return render_template('perfil.html', usuario=usuario, proyectos=proyectos, tareas=tareas_asignadas)

    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))

@app.route('/editar_perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'correo' not in session:
        flash('Debes iniciar sesión para editar tu perfil.', 'danger')
        return redirect(url_for('login'))

    usuario = usuarios_collection.find_one({'correo': session['correo']})
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Recoger los datos del formulario
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        
        # Actualizar datos comunes para todos los roles
        update_data = {
            'nombre': nombre,
            'telefono': telefono
        }

        # Campos adicionales dependiendo del rol
        if usuario['role'] == 'miembro' or usuario['role'] == 'admin':
            estudios = request.form.get('estudios')
            profesion = request.form.get('profesion')
            programa = request.form.get('programa')
            habilidades = request.form.getlist('habilidades')  # Si tienes un checkbox múltiple

            update_data.update({
                'estudios': estudios,
                'profesion': profesion,
                'programa': programa,
                'habilidades': habilidades
            })

        elif usuario['role'] == 'empresa':
            nit = request.form.get('nit')
            encargado = request.form.get('encargado')

            update_data.update({
                'nit': nit,
                'encargado': encargado
            })

        # Actualizar los datos del usuario en la base de datos
        usuarios_collection.update_one({'_id': usuario['_id']}, {'$set': update_data})

        flash('Perfil actualizado exitosamente.', 'success')
        return redirect(url_for('perfil'))

    # Mostrar el formulario de edición con los datos actuales del usuario
    return render_template('editar_perfil.html', usuario=usuario)

@app.route('/mis_tareas')

def mis_tareas():
    if 'correo' in session:  # Verificamos que haya una sesión activa
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        
        if usuario:  # Si se encuentra el usuario en la base de datos
            # Obtener todos los proyectos en los que el usuario es miembro
            proyectos = list(proyectos_collection.find({'miembros._id': usuario['_id']}))
            
            tareas_asignadas = []
            # Iteramos sobre los proyectos para extraer las tareas asignadas al usuario
            for proyecto in proyectos:
                tareas = proyecto.get('tareas', [])  # Usamos 'tareas' o array vacío si no existe
                for tarea in tareas:  # Iteramos sobre la variable 'tareas', no 'proyecto['tareas']'
                    if str(tarea['miembro_asignado']) == str(usuario['_id']):
                        tarea_info = {
                            '_id': tarea['_id'],
                            'nombre': tarea['nombre'],
                            'descripcion': tarea['descripcion'],
                            'estado': tarea['estado'],
                            'fechavencimiento': tarea.get('fechavencimiento', 'No asignada'),
                            'proyecto': proyecto['nombre']
                        }
                        tareas_asignadas.append(tarea_info)
            
            # Renderizamos la plantilla con las tareas asignadas al usuario
            return render_template('mis_tareas.html', tareas=tareas_asignadas)
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('login'))


@app.route('/recuperacion', methods=['GET', 'POST'])
def recuperacion():
     if request.method == 'POST':
        correo = request.form['correo']
        usuario = usuarios_collection.find_one({'correo': correo})
        if usuario:
            # Generar un código de validación aleatorio
            codigo_validacion = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            # Guardamos el código en la base de datos asociado al usuario
            usuarios_collection.update_one(
                {'correo': correo}, 
                {'$set': {'codigo_validacion': codigo_validacion}}
            )
            # Enviar el código de validación por correo
            msg = Message('Recuperación de Contraseña', sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[correo])
            msg.body = f"Tu código de validación es: {codigo_validacion}"
            mail.send(msg)
            
            flash('Se ha enviado un código de validación a tu correo electrónico.')
            return redirect(url_for('validar_codigo', correo=correo))
        else:
            flash('El correo ingresado no está registrado.')

     return render_template('inicio_sesion/recuperar.html')

@app.route('/registro_empresa', methods=['GET', 'POST'])
def registro_empresa():
    if request.method == 'POST':
        nombre_empresa = request.form['empresa']
        correo_empresa = request.form['correo_empresa']
        nit = request.form['NIT']
        encargado = request.form['encargado']
        telefono = request.form['telefono']
        password = request.form['password']
        ConfirmPassword = request.form['Confirm_password']

        if usuarios_collection.find_one({'correo': correo_empresa}):
            flash('El correo ya está registrado.')
        else:
            try:
                if nombre_empresa and correo_empresa and nit and encargado and telefono and password and ConfirmPassword:
                    if ConfirmPassword == password:
                        passwordHashed = generate_password_hash(password)
                        nuevo_usuario = Empresa(nombre_empresa, correo_empresa, nit, encargado, telefono, passwordHashed)
                        usuarios_collection.insert_one(nuevo_usuario.formato_doc())
                        flash('Empresa registrada exitosamente.')
                        return redirect(url_for('login'))
                    else:
                        flash('Las contraseñas no coinciden')
                else:
                    flash('Por favor, completa todos los campos.')
            except Exception as e:
                flash(f'Error al registrar la empresa: {str(e)}')
                return redirect(url_for('login'))

    return render_template('empresa.html')


@app.route('/cambiar_estado_tarea/<id>', methods=['POST'])
def cambiar_estado_tarea(id):
    nuevo_estado = request.form['estado']  # Obtiene el nuevo estado del formulario
    comentario = request.form.get('comentario')  # Obtiene el comentario, si hay uno
    usuario = usuarios_collection.find_one({'correo': session['correo']})

    if usuario:
        # Buscar el proyecto que contiene la tarea y actualizar el estado de la tarea
        proyectos = list(proyectos_collection.find({'tareas._id': ObjectId(id)}))
        for proyecto in proyectos:
            for tarea in proyecto['tareas']:
                if str(tarea['_id']) == id:
                    tarea['estado'] = nuevo_estado  # Actualiza el estado de la tarea
                    proyectos_collection.update_one(
                        {'_id': proyecto['_id'], 'tareas._id': ObjectId(id)},
                        {'$set': {'tareas.$.estado': nuevo_estado}}
                    )

                    # Si el nuevo estado es "Completado", agrega el comentario
                    if nuevo_estado == "Completado" and comentario:
                        agregar_comentario(proyecto['_id'], tarea['_id'], comentario)

                    flash('El estado de la tarea ha sido actualizado.')

                    # Enviar correo a líder y administrador
                    send_notification_email(proyecto, tarea, nuevo_estado)

                    return redirect(url_for('mis_tareas'))
    
    flash('No se pudo actualizar el estado de la tarea.')
    return redirect(url_for('mis_tareas'))

def send_notification_email(proyecto, tarea, nuevo_estado, comentario):
    # Obtener correos del líder del proyecto
    lideres = proyecto.get('lideres', [])  # Obtiene la lista de líderes
    admin = usuarios_collection.find_one({'role': 'admin'})  # Encuentra al administrador

    # Crear mensaje para el líder
    if lideres:  # Verifica que haya al menos un líder
        lider = lideres[0]  # Accede al primer líder
        msg_lider = Message(
            subject=f'Notificación de Actualización de Tarea: {tarea["nombre"]}',
            recipients=[lider['correo']]
        )
        msg_lider.body = f"""
        Estimado(a) {lider['nombre']},

        El estado de la tarea "{tarea['nombre']}" ha sido actualizado a "{nuevo_estado}" en el proyecto "{proyecto['nombre']}". 

        Detalles:
        - Descripción: {tarea['descripcion']}
        - Fecha de vencimiento: {tarea['fechavencimiento']}
        - Comentario: {comentario}
        
        Si tienes alguna pregunta, no dudes en contactarnos.

        Saludos,
        Tu Equipo
        """
        mail.send(msg_lider)

    # Crear mensaje para el administrador
    if admin:  # Verifica que se encontró un administrador
        msg_admin = Message(
            subject=f'Notificación de Actualización de Tarea: {tarea["nombre"]}',
            recipients=[admin['correo']]
        )
        msg_admin.body = f"""
        Estimado(a) {admin['nombre']},

        El estado de la tarea "{tarea['nombre']}" ha sido actualizado a "{nuevo_estado}" en el proyecto "{proyecto['nombre']}". 

        Detalles:
        - Descripción: {tarea['descripcion']}
        - Fecha de vencimiento: {tarea['fechavencimiento']}
        - Comentario: {comentario}
        
        Si tienes alguna pregunta, no dudes en contactarnos.

        Saludos,
        Tu Equipo
        """
        mail.send(msg_admin)


def agregar_comentario(proyecto_id, tarea_id, contenido):
    autor = session['nombre']
    comentario = {'nombre_autor': autor, 'texto': contenido, 'fecha': datetime.now().isoformat()}

    # Encuentra el proyecto correspondiente
    proyecto = proyectos_collection.find_one({'_id': ObjectId(proyecto_id)})
    if proyecto:
        # Agrega el comentario a la tarea
        proyectos_collection.update_one(
            {'_id': ObjectId(proyecto_id), 'tareas._id': ObjectId(tarea_id)},
            {'$push': {'tareas.$.comentarios': comentario}}
        )
@app.route('/validar_codigo/<correo>', methods=['GET', 'POST'])
def validar_codigo(correo):
    usuario = usuarios_collection.find_one({'correo': correo})
    
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')

        # Validar el código de recuperación 
        if not nueva_password and not confirmar_password:
            if usuario.get('codigo_validacion') == codigo_ingresado:
                flash('Código de validación correcto. Ahora puedes cambiar tu contraseña.')
                return redirect(url_for('validar_codigo', correo=correo) + '?validado=true')
            else:
                flash('El código de validación es incorrecto.')
                return redirect(url_for('validar_codigo', correo=correo))

        # Validar las contraseñas ingresadas 
        if nueva_password and confirmar_password:
            if nueva_password != confirmar_password:
                flash('Las contraseñas no coinciden.')
                return redirect(url_for('validar_codigo', correo=correo) + '?validado=true')
            

            nueva_password_hashed = generate_password_hash(nueva_password)
            usuarios_collection.update_one(
                {'correo': correo},
                {'$set': {'password': nueva_password_hashed, 'codigo_validacion': None,'CambioDeContraseña':None}}
            )
            flash('Contraseña actualizada exitosamente.')
            return redirect(url_for('login'))

    # Aquí verificamos si el código fue validado y cambiamos la vista en base a esa variable
    codigo_valido = request.args.get('validado') == 'true'

    # Renderizar la plantilla con el estado del código valido
    return render_template('inicio_sesion/validar_codigo.html', correo=correo, codigo_valido=codigo_valido)

@app.route('/solicitar_proyecto', methods=['GET', 'POST'])
def solicitar_proyecto():
    if request.method == 'POST':
        nombre_proyecto = request.form.get('nombre_proyecto')
        descripcion = request.form.get('descripcion')
        requerimientos = request.form.get('requerimientos')
        tiempo_estimado = request.form.get('tiempo_estimado')
        nombre_soli = request.form.get('nombre_soli')
        correo_soli = request.form.get('correo_soli')
        telefono_soli = request.form.get('telefono_soli')
        empresa_id = session.get('empresa_id')

        nueva_solicitud = {
            'nombre': nombre_proyecto,
            'descripcion': descripcion,
            'requerimientos': requerimientos,
            'tiempo_estimado': tiempo_estimado,
            'nombre_soli': nombre_soli,
            'correo_soli': correo_soli,
            'telefono_soli': telefono_soli,
            'fecha_solicitud': datetime.now(),
            'estado': 'Pendiente',
            'empresa_id': ObjectId(empresa_id)  # Relacionar con la empresa
        }
        solicitudes_collection.insert_one(nueva_solicitud)

        # Preparar el mensaje flash
        mensaje = f"Su solicitud para el proyecto '{nombre_proyecto}' ha sido radicada con éxito. " \
                  "Recibirá una respuesta en un plazo de 15 días hábiles. ¡Gracias por su solicitud!"
        flash(mensaje, 'success')

        # Preparar el correo de confirmación
        msg = Message(
            subject="Confirmación de Solicitud de Proyecto",
            recipients=[correo_soli]
        )
        msg.body = f"""
        Estimado/a {nombre_soli},

        Nos complace informarle que su solicitud para el proyecto '{nombre_proyecto}' ha sido recibida con éxito.

        Detalles de la solicitud:
        - Descripción: {descripcion}
        - Requerimientos: {requerimientos}
        - Tiempo estimado: {tiempo_estimado} semanas

        Recibirá una respuesta en un plazo máximo de 15 días hábiles.

        ¡Gracias por confiar en nosotros!

        Saludos cordiales,
        Centro Digital de Desarrollo Tecnológico
        """
        mail.send(msg)

        return redirect(url_for('ver_solicitudes'))

    return render_template('solicitud_proyecto.html')

@app.route('/solicitudes')
def ver_solicitudes():
    empresa_id = session.get('empresa_id')  # Obtener el ID de la empresa desde la sesión
    print(f"Empresa ID en sesión: {empresa_id}")
    
    if empresa_id:
        try:
            solicitudes = list(solicitudes_collection.find({'empresa_id': ObjectId(empresa_id)}))
            print(f"Solicitudes encontradas: {solicitudes}")
        except Exception as e:
            print(f"Error en la consulta de MongoDB: {e}")
            solicitudes = []
    else:
        print("No hay empresa_id en la sesión")
        solicitudes = []

    return render_template('ver_solicitudes.html', proyectos=solicitudes)

@app.route('/ver_todas_solicitudes')
def ver_todas_solicitudes():
    if 'correo' in session and session.get('role') == 'admin':  # Verificar si el usuario es admin
        try:
            # Obtener todas las solicitudes sin filtrar por empresa
            solicitudes = list(solicitudes_collection.find())
            print(f"Solicitudes encontradas: {solicitudes}")
        except Exception as e:
            print(f"Error en la consulta de MongoDB: {e}")
            solicitudes = []
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('login'))
    
    return render_template('admin/ver_solicitudes_empresas.html', proyectos=solicitudes)

@app.route('/actualizar_solicitud/<solicitud_id>', methods=['POST'])
def actualizar_solicitud(solicitud_id):
    print(f"Correo en sesión: {session.get('correo')}, Rol en sesión: {session.get('role')}")  # Verifica el valor de la sesión
    if 'correo' in session and session.get('role') == 'admin':
        nuevo_estado = request.form.get('estado')
        comentario_rechazo = request.form.get('comentario_rechazo')  # Obtén el comentario de rechazo si está presente

        try:
            # Buscar la solicitud
            solicitud = solicitudes_collection.find_one({'_id': ObjectId(solicitud_id)})
            if not solicitud:
                flash('Solicitud no encontrada.', 'danger')
                return redirect(url_for('ver_todas_solicitudes'))

            # Buscar la empresa asociada
            empresa_id = solicitud.get('empresa_id')
            empresa = usuarios_collection.find_one({'_id': ObjectId(empresa_id)})
            if not empresa:
                flash('Empresa no encontrada.', 'danger')
                return redirect(url_for('ver_todas_solicitudes'))

            # Validar comentario de rechazo si el estado es "Rechazado"
            if nuevo_estado == 'Rechazado':
                if not comentario_rechazo:
                    flash('Debe proporcionar un comentario al rechazar la solicitud.', 'danger')
                    return redirect(url_for('ver_todas_solicitudes'))

                # Actualizar el estado de la solicitud a "Rechazado" con comentario
                solicitudes_collection.update_one(
                    {'_id': ObjectId(solicitud_id)},
                    {'$set': {'estado': 'Rechazado', 'causal_rechazo': comentario_rechazo}}
                )

                # Preparar el cuerpo del correo de notificación
                msg = Message(
                    subject=f'Actualización de Solicitud: {solicitud["nombre"]}',
                    recipients=[empresa['correo']]
                )
                msg.body = f"""
                Estimado(a),

                La solicitud del proyecto "{solicitud['nombre']}" ha sido actualizada a estado: {nuevo_estado}.

                Comentario sobre el rechazo:
                {comentario_rechazo}

                Detalles de la solicitud:
                - Descripción: {solicitud['descripcion']}
                - Requerimientos: {solicitud['requerimientos']}
                - Tiempo estimado: {solicitud['tiempo_estimado']} semanas

                Si tienes alguna pregunta o necesitas más información, no dudes en contactarnos.

                Saludos cordiales,
                Centro Digital de Desarrollo Tecnológico
                """
                mail.send(msg)

                flash(f'Solicitud rechazada y notificación enviada.', 'success')

            # Si la solicitud es "Aprobada", redirigir a la creación del nuevo proyecto
            elif nuevo_estado in ['Aprobado', 'Aprobado con cambios']:
                # Verificar si ya existe un proyecto relacionado con la solicitud
                proyecto_existente = proyectos_collection.find_one({'solicitud_id': ObjectId(solicitud_id)})
                
                if not proyecto_existente:
                    # Redirigir a la página de creación de proyecto
                    return redirect(url_for('nuevo_proyecto', solicitud_id=solicitud_id, empresa_id=empresa_id))
                else:
                    flash('El proyecto ya ha sido creado. Puede volver a radicar si es necesario.', 'info')

            # Para cualquier otro estado (si existe)
            else:
                solicitudes_collection.update_one(
                    {'_id': ObjectId(solicitud_id)},
                    {'$set': {'estado': nuevo_estado}}
                )
                flash(f'Solicitud actualizada a {nuevo_estado}.', 'success')

        except Exception as e:
            print(f"Error actualizando la solicitud: {e}")
            flash('Ocurrió un error al actualizar la solicitud.', 'danger')

    # Siempre redirigir a la lista de solicitudes después del procesamiento
    return redirect(url_for('ver_todas_solicitudes'))

@app.route('/nuevo_proyecto', methods=['GET', 'POST'])
def nuevo_proyecto():
    print(f"Correo en sesión: {session.get('correo')}, Rol en sesión: {session.get('role')}")  # Verifica el valor de la sesión
    if 'correo' in session and session.get('role') == 'admin':
        if request.method == 'GET':
            solicitud_id = request.args.get('solicitud_id')
            empresa_id = request.args.get('empresa_id')

            # Aquí puedes pasar los IDs a la plantilla si es necesario
            return render_template('admin/nuevo_proyecto.html', solicitud_id=solicitud_id, empresa_id=empresa_id)

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            fechainicio = request.form.get('fechainicio')
            fechafinal = request.form.get('fechafinal')
            objetivo_general = request.form.get('objetivo_general')
            objetivos_especificos = request.form.getlist('objetivos_especificos')
            estado = request.form.get('estado')
            solicitud_id = request.form.get('solicitud_id') 
            empresa_id = request.form.get('empresa_id')
            objetivos_especificos_list = []
            for objetivo in objetivos_especificos:
                if objetivo:  # Asegurarse de que el objetivo no esté vacío
                    objetivos_especificos_list.append({
                        'id': str(uuid.uuid4()),  # Generar un ID único para cada objetivo
                        'descripcion': objetivo
                    })

            # Validar que todos los campos requeridos estén presentes
            if not all([nombre, descripcion, fechainicio, fechafinal, objetivo_general, estado]):
                flash('Todos los campos son obligatorios.', 'danger')
                return redirect(url_for('nuevo_proyecto'))

            # Validar que fechainicio sea anterior a fechafinal
            if fechainicio > fechafinal:
                flash('La fecha de inicio debe ser anterior a la fecha final.', 'danger')
                return redirect(url_for('nuevo_proyecto'))

            try:
                # Buscar la solicitud correspondiente
                solicitud = solicitudes_collection.find_one({'_id': ObjectId(solicitud_id)})
                usuarios = usuarios_collection.find_one({'_id': ObjectId(empresa_id)})
                print(ObjectId(solicitud_id))
                if not solicitud:
                    flash('Solicitud no encontrada.', 'danger')
                    return redirect(url_for('ver_todas_solicitudes'))
                
                # Obtener los correos de solicitud y empresa
                correo_solicitante = solicitud.get('correo_soli')
                correo_empresa = usuarios.get('correo')

                # Validar que al menos uno de los correos esté disponible
                if not correo_solicitante and not correo_empresa:
                    flash('No hay correos disponibles para enviar la notificación.', 'danger')
                    return redirect(url_for('ver_todas_solicitudes'))

                # Crear la lista de destinatarios, solo con los correos válidos
                destinatarios = []
                if correo_solicitante:
                    destinatarios.append(correo_solicitante)
                if correo_empresa:
                    destinatarios.append(correo_empresa)

                # Actualizar la solicitud a "Aprobado"
                solicitudes_collection.update_one(
                    {'_id': ObjectId(solicitud_id)},
                    {'$set': {'estado': 'Aprobado'}}
                )
                
                # Crear el nuevo proyecto
                nuevo_proyecto = {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechainicio': fechainicio,
                    'fechafinal': fechafinal,
                    'estado': estado,
                    'objetivoGeneral': objetivo_general,
                    'objetivosEspecificos': objetivos_especificos_list,
                    'solicitud_id': ObjectId(solicitud_id),
                    'empresa_id': ObjectId(empresa_id),
                    'miembros': [],
                    'lideres': []

                }

                # Insertar el proyecto en la base de datos
                proyectos_collection.insert_one(nuevo_proyecto)

                # Enviar correo de confirmación de aprobación
                msg = Message(
                    subject=f'Solicitud Aprobada: {solicitud["nombre"]}',
                    recipients=destinatarios 
                )
                msg.body = f"""
                Estimado(a),

                La solicitud "{solicitud['nombre']}" ha sido aprobada y se ha creado un nuevo proyecto.

                Detalles del proyecto:
                - Nombre: {nombre}
                - Descripción: {descripcion}
                - Fecha de inicio: {fechainicio}
                - Fecha final: {fechafinal}
                - Objetivo General: {objetivo_general}
                - Objetivos Específicos: {', '.join(objetivos_especificos)}

                Saludos cordiales,
                Centro Digital de Desarrollo Tecnológico
                """
                mail.send(msg)

                flash('Solicitud aprobada y proyecto creado exitosamente.', 'success')

            except Exception as e:
                print(f"Error aprobando la solicitud: {e}")
                flash('Ocurrió un error al aprobar la solicitud.', 'danger')

            return redirect(url_for('admin_proyectos'))  # Redirigir de vuelta a la lista de proyectos

    flash('No tienes permisos para realizar esta acción.', 'danger')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
