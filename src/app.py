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

app = Flask(__name__)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'maira.quiro.p02@gmail.com' 
app.config['MAIL_PASSWORD'] = 'aibxuphykognlqyc'    
app.config['MAIL_DEFAULT_SENDER'] = 'centrodigitaldedesarrollotecnologico@gmail.com' 
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_SUPPRESS_SEND'] = False  # Para evitar que supriman el envío de correos en modo debug
app.config['MAIL_ASCII_ATTACHMENTS'] = False

# Inicializamos Mail
mail = Mail(app)
app.secret_key = 'uhggjghlñhu'

# Conexión a la base de datos
db = Conexion()
usuarios_collection = db['usuarios']
proyectos_collection = db['proyectos']
tareas_collection = db['tareas']
solicitudes_collection = db['solicitudes']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    if 'correo' in session:
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        if usuario:
            return render_template('home.html', usuario = usuario)
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        
        # Consulta para buscar al usuario en la base de datos
        usuario = usuarios_collection.find_one({'correo': correo})
        
        # Verificar si el usuario existe y si la contraseña es correcta
        if usuario and usuario['password'] and password.strip() and check_password_hash(usuario['password'], password):
            session['correo'] = usuario['correo']
            session['role'] = usuario['role']
            session['nombre'] = usuario['nombre']
            
            # Si el usuario tiene el rol de empresa, almacenar el _id en la sesión
            if usuario['role'] == 'empresa':
                session['empresa_id'] = str(usuario['_id'])  # Convertir ObjectId a string
            
            return redirect(url_for('home'))
        else:
            # Agregar mensaje flash de error
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
                 token=s.dumps(correo, salt='registro-usuario')
                 nuevo_usuario = UserWithoutRegister(nombre, correo, VerificationCode, role)
                 usuarios_collection.insert_one(nuevo_usuario.formato_doc())
                 msg=enviar_correo_registro(correo,VerificationCode,token)
                 mail.send(msg)
                 flash('Registro exitoso. Se ha enviado un correo con tus credenciales.')
                except Exception as e:
                    flash(f'Error al enviar el correo: {str(e)}')
                return redirect(url_for('home'))
        return render_template('inicio_sesion/registro.html')
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('home'))

@app.route('/completar_registro/<token>', methods=['GET', 'POST'])
def completar_registro(token):
    try:
        s = URLSafeTimedSerializer(app.secret_key)
        email = s.loads(token, salt='registro-usuario', max_age=259200)  
        usuario = usuarios_collection.find_one({'correo': email})

        if not usuario:
            flash('Usuario no encontrado.')
            return redirect(url_for('home'))
        
        nombre_completo = usuario.get('nombre')  
        correo = usuario.get('correo')
        verificationCode = usuario.get('verficationCode')
         
        if request.method == 'POST':
            
            telefono = request.form.get('telefono')
            profesion = request.form.get('profesion')
            estudios = request.form.get('estudios')
            habilidades = request.form.get('habilidades')
            experiencia = request.form.get('experiencia')
            programa = request.form.get('programa')
            temp_Password= request.form['temp_password']
            new_password = request.form['new_password']
            
            if (verificationCode != temp_Password):
                print('La contraseña temporal no es válida.')
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
                        'verficationCode': None,
                        'programa': programa,
                        'password': generate_password_hash(new_password),
                        'registroCompletado': True  
                    }
                }
            )

            flash('Registro completado exitosamente.')
            return redirect(url_for('login'))
            
        return render_template('inicio_sesion/completar_registro.html',
                               nombre_completo=nombre_completo,correo=correo,token=token)
    except Exception as e:
        print('El enlace de registro ha expirado o es inválido. Error: {str(e)}')
        return redirect(url_for('home'))
    
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
        return redirect(url_for('home'))

@app.route('/admin_empresas', methods=['GET', 'POST'])
def admin_empresas():
    if 'correo' in session and session.get('role') == 'admin':
        # Filtrar usuarios cuyo role sea "empresa"
        getusuarios = list(usuarios_collection.find({"role": "empresa"}))
        
        return render_template('admin/admin_empresas.html', usuarios=getusuarios)
    else:
        flash('No tienes permisos para acceder a esta página.')
        return redirect(url_for('home'))

@app.route('/usuario/<id>/editar', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'correo' in session and session.get('role') == 'admin':
        usuario = usuarios_collection.find_one({'_id': ObjectId(id)})
        if request.method == 'POST':
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            correo = request.form['correo']
            role = request.form['role']
            cargo = request.form['cargo']
            habilidades = request.form['habilidades'].split(',')

            # Actualizar información del usuario
            usuarios_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'nombre': nombre,
                    'apellido': apellido,
                    'correo': correo,
                    'role': role,
                    'cargo': cargo,
                    'habilidades': habilidades
                }}
            )

            # Actualizar la información del usuario en los proyectos donde esté asignado
            proyectos_collection.update_many(
                {'miembros._id': ObjectId(id)},
                {'$set': {
                    'miembros.$.nombre': nombre,
                    'miembros.$.apellido': apellido,
                    'miembros.$.correo': correo
                }}
            )

            # Actualizar la información del usuario en las tareas donde esté asignado
            proyectos = proyectos_collection.find({'tareas.miembroasignado': ObjectId(id)})
            for proyecto in proyectos:
                for tarea in proyecto['tareas']:
                    if tarea['miembroasignado'] == str(id):
                        tarea['miembro_nombre'] = f"{nombre} {apellido}"
                proyectos_collection.update_one(
                    {'_id': proyecto['_id']},
                    {'$set': {'tareas': proyecto['tareas']}}
                )

            flash('Usuario actualizado exitosamente.')
            return redirect(url_for('admin_usuarios'))

        return render_template('admin/editar_usuario.html', usuario=usuario)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

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
    return redirect(url_for('home'))


@app.route('/admin_proyectos', methods=['GET', 'POST'])
def admin_proyectos():
    if 'correo' in session and session.get('role') == 'admin':
        # Para ver los proyectos existentes
        proyectos = proyectos_collection.find()

        # Para agregar un nuevo proyecto
        if request.method == 'POST':
             nombre = request.form.get('nombre')
             descripcion = request.form.get('descripcion')
             fechainicio = request.form.get('fechainicio')
             fechafinal = request.form.get('fechafinal')
             objetivo_general = request.form.get('objetivo_general')
             objetivos_especificos = request.form.getlist('objetivos_especificos')
             estado = request.form.get('estado')

                # Validar que todos los campos requeridos estén presentes
             if not all([nombre, descripcion, fechainicio, fechafinal, objetivo_general, estado]):
                    flash('Todos los campos son obligatorios.', 'danger')
                    return redirect(url_for('admin_proyectos'))

                # Crear el nuevo proyecto
             nuevo_proyecto = Proyecto(
                    nombre=nombre,
                    descripcion=descripcion,
                    fechainicio=fechainicio,
                    fechafinal=fechafinal,
                    estado=estado,
                    objetivoGeneral=objetivo_general,
                    objetivosEspecificos=objetivos_especificos
                )

                # Insertar el proyecto en la base de datos
             proyectos_collection.insert_one(nuevo_proyecto.formato_doc())

                # Reiniciar 'objetivos_mostrados' en la sesión
             session.pop('objetivos_mostrados', None)
             flash('Proyecto creado exitosamente.', 'success')
             return redirect(url_for('admin_proyectos'))
        
        # Convertir el cursor de proyectos en una lista para poder iterar sobre ella múltiples veces
        lista_proyectos = list(proyectos)
        
        # Reemplazar el ID del miembro asignado por su nombre completo
        for proyecto in lista_proyectos:
            for tarea in proyecto.get('tareas', []):
                miembro_id = tarea.get('miembro_asignado')  # el 'id' del miembro asignado
                if miembro_id:
                    # Buscar al usuario en la base de datos usando el id
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1})
                    # Si se encuentra el usuario, reemplazar el 'id' con su nombre completo
                    if miembro:
                        tarea['miembro_asignado'] = f"{miembro['nombre']}"
                    else:
                        tarea['miembro_asignado'] = "Sin asignar"
                else:
                    tarea['miembro_asignado'] = "Sin asignar"

        return render_template('admin/admin_proyectos.html', proyectos=lista_proyectos)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/nuevo_proyecto', methods=['GET', 'POST'])
def nuevo_proyecto():
    if 'correo' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            fechainicio = request.form.get('fechainicio')
            fechafinal = request.form.get('fechafinal')
            objetivo_general = request.form.get('objetivo_general')
            objetivos_especificos = request.form.getlist('objetivos_especificos')
            estado = request.form.get('estado')

            # Validar que todos los campos requeridos estén presentes
            if not all([nombre, descripcion, fechainicio, fechafinal, objetivo_general, estado]):
                flash('Todos los campos son obligatorios.', 'danger')
                return redirect(url_for('nuevo_proyecto'))

            # Validar que fechainicio sea anterior a fechafinal
            if fechainicio > fechafinal:
                flash('La fecha de inicio debe ser anterior a la fecha final.', 'danger')
                return redirect(url_for('nuevo_proyecto'))

            try:
                # Crear el nuevo proyecto
                nuevo_proyecto = Proyecto(
                    nombre=nombre,
                    descripcion=descripcion,
                    fechainicio=fechainicio,
                    fechafinal=fechafinal,
                    estado=estado,
                    objetivoGeneral=objetivo_general,
                    objetivosEspecificos=objetivos_especificos
                )

                # Insertar el proyecto en la base de datos
                proyectos_collection.insert_one(nuevo_proyecto.formato_doc())
                flash('Proyecto creado exitosamente.', 'success')

            except Exception as e:
                flash('Error al crear el proyecto: {}'.format(str(e)), 'danger')

            return redirect(url_for('admin_proyectos'))  # Redirigir de vuelta a la lista de proyectos

        return render_template('admin/nuevo_proyecto.html')  # Cargar el formulario para agregar un nuevo proyecto

    flash('No tienes permisos para realizar esta acción.', 'danger')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/editar', methods=['GET', 'POST'])
def editar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        
        if not proyecto:
            flash('No se encontró el proyecto.')
            return redirect(url_for('ver_proyectos'))

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            objetivoGeneral= request.form.get('objetivoGeneral')
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
                    'objetivoGeneral':objetivoGeneral
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

            flash('Proyecto actualizado exitosamente.')
            return redirect(url_for('admin_proyectos'))

        return render_template('admin/editar_proyecto.html', proyecto=proyecto)

    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/eliminar')
def eliminar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyectos_collection.delete_one({'_id': ObjectId(id)})
        flash('Proyecto eliminado exitosamente.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/asignar_miembros', methods=['GET', 'POST'])
def asignar_miembros(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if proyecto:
            if request.method == 'POST':
                # Procesar la eliminación de miembros seleccionados
                eliminar_miembros_seleccionados = request.form.getlist('eliminar_miembro')
                if eliminar_miembros_seleccionados:
                    proyecto['miembros'] = [miembro for miembro in proyecto['miembros'] if str(miembro['_id']) not in eliminar_miembros_seleccionados]
                
                # Procesar la adición de miembros seleccionados
                agregar_miembros_seleccionados = request.form.getlist('agregar_miembro')
                for miembro_id in agregar_miembros_seleccionados:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)})
                    if miembro:
                        proyecto['miembros'].append(miembro)
                
                # Actualizar el proyecto en la base de datos
                proyectos_collection.update_one({'_id': ObjectId(id)}, {'$set': proyecto})
                
                flash('Acciones de asignación de miembros realizadas exitosamente.')
                return redirect(url_for('admin_proyectos'))
            
            usuarios = usuarios_collection.find({"registroCompletado": True})
            return render_template('admin/asignar_miembros.html', proyecto=proyecto, usuarios=usuarios)
        else:
            flash('No se encontró el proyecto.')
            return redirect(url_for('admin_proyectos'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))



@app.route('/seleccionar_proyecto', methods=['GET', 'POST'])
def seleccionar_proyecto():
    if 'correo' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            proyecto_id = request.form.get('proyecto_id')
            return redirect(url_for('agregar_tarea', proyecto_id=proyecto_id))
        proyectos = proyectos_collection.find()
        return render_template('admin/seleccionar_proyecto.html', proyectos=proyectos)
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<proyecto_id>/agregar_tarea/', methods=['GET', 'POST'])
def agregar_tarea(proyecto_id):
    if 'correo' in session and session.get('role') == 'admin':

        proyecto_data = proyectos_collection.find_one({'_id': ObjectId(proyecto_id)})

        if proyecto_data:
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']  # Fecha de vencimiento
                miembro_asignado = request.form.get('miembro_asignado')  # Miembro asignado opcional
                estado = request.form.get('estado')  # Estado de la tarea (por defecto: 'pendiente')
                objetivo_especifico_id = request.form['objetivo_especifico_id']
               
                objetivos_ids = [obj['id'] for obj in proyecto_data['objetivosEspecificos']]
                if objetivo_especifico_id not in objetivos_ids:
                    raise ValueError("El ID del objetivo específico no es válido")
                nueva_tarea_id = ObjectId()
                nueva_tarea = {
                    '_id':nueva_tarea_id,
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechavencimiento': fechavencimiento,
                    'miembro_asignado': miembro_asignado,
                    'estado': estado,
                    'objetivo_especifico_id': objetivo_especifico_id,
                }

                proyectos_collection.update_one(
                    {'_id': ObjectId(proyecto_id)},
                    {'$push': {'tareas': nueva_tarea}}
                )
                return redirect(url_for('seleccionar_proyecto'))
                
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto_data['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
            return render_template('admin/agregar_tarea.html', proyecto=proyecto_data, usuarios=miembros_asignados)
        
        flash('No se encontró el proyecto.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))



@app.route('/tareas', methods=['GET'])
def ver_todas_las_tareas():
    if 'correo' in session and session.get('role') == 'admin':
        filtro_proyecto = request.args.get('proyecto')  # Filtro de nombre de proyecto
        filtro_miembro = request.args.get('miembro')  # Filtro de miembro asignado
        
        proyectos = proyectos_collection.find()
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
    return redirect(url_for('home'))

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
    return redirect(url_for('home'))

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
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})
        
        if not proyecto:
            flash('No se encontró la tarea.')
            return redirect(url_for('ver_todas_las_tareas'))
        
        tarea = next((t for t in proyecto['tareas'] if t['_id'] == ObjectId(id)), None)
        
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
                            sender='tu_email@gmail.com',
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
                
        miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
        miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))

        return render_template(
            'admin/editar_tarea.html', 
            tarea=tarea, 
            proyecto=proyecto, 
            miembros=miembros_asignados,
            objetivos_especificos=proyecto.get('objetivosEspecificos', [])
        )
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/tarea/<id>/eliminar', methods=['POST'])
def eliminar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})
        
        if proyecto:
            try:
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
                            sender='tu_email@gmail.com',
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
        else:
            flash('No se encontró la tarea.')
        
        return redirect(url_for('ver_todas_las_tareas'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/perfil')
def perfil():
    if 'correo' in session:
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        if usuario:
            proyectos = list(proyectos_collection.find({'miembros._id': usuario['_id']}))
            
            tareas_asignadas = []
            for proyecto in proyectos:
                for tarea in proyecto['tareas']:
                    if tarea['miembroasignado'] == str(usuario['_id']):
                        tareas_asignadas.append(tarea)
            
            return render_template('perfil.html', usuario=usuario, proyectos=proyectos, tareas=tareas_asignadas)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

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
                for tarea in proyecto['tareas']:
                    # Asegurarnos de comparar el ID del miembro asignado como string
                    if str(tarea['miembro_asignado']) == str(usuario['_id']):
                        tarea_info = {
                            '_id': tarea['_id'],  # ID de la tarea
                            'nombre': tarea['nombre'],  # Nombre de la tarea
                            'descripcion': tarea['descripcion'],  # Descripción de la tarea
                            'estado': tarea['estado'],  # Estado de la tarea
                            'fechavencimiento': tarea.get('fechavencimiento', 'No asignada'),  # Fecha de vencimiento (opcional)
                            'proyecto': proyecto['nombre']  # Nombre del proyecto
                        }
                        tareas_asignadas.append(tarea_info)
            
            # Renderizamos la plantilla con las tareas asignadas al usuario
            return render_template('mis_tareas.html', tareas=tareas_asignadas)
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))



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
            msg = Message('Recuperación de Contraseña', sender='CentroDigitalDeDesarrollo@gmail.com', recipients=[correo])
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
        password = request.form['password']
        ConfirmPassword = request.form['Confirm_password']

        if usuarios_collection.find_one({'correo': correo_empresa}):
            flash('El correo ya está registrado.')
        else:
            try:
                if nombre_empresa and correo_empresa and nit and password and ConfirmPassword:
                    if ConfirmPassword == password:
                        passwordHashed = generate_password_hash(password)
                        nuevo_usuario = Empresa(nombre_empresa, correo_empresa, nit, passwordHashed)
                        usuarios_collection.insert_one(nuevo_usuario.formato_doc())
                        flash('Empresa registrada exitosamente.')
                        return redirect(url_for('home'))
                    else:
                        flash('Las contraseñas no coinciden')
                else:
                    flash('Por favor, completa todos los campos.')
            except Exception as e:
                flash(f'Error al registrar la empresa: {str(e)}')
                return redirect(url_for('home'))

    return render_template('empresa.html')


@app.route('/cambiar_estado_tarea/<id>', methods=['POST'])
def cambiar_estado_tarea(id):
    nuevo_estado = request.form['estado']  # Obtiene el nuevo estado del formulario
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
                    flash('El estado de la tarea ha sido actualizado.')
                    return redirect(url_for('mis_tareas'))
    
    flash('No se pudo actualizar el estado de la tarea.')
    return redirect(url_for('mis_tareas'))


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
        
        # Obtener el ID de la empresa desde la sesión (sin pasarlo en el formulario)
        empresa_id = session.get('empresa_id')

        nueva_solicitud = {
            'nombre': nombre_proyecto,
            'descripcion': descripcion,
            'requerimientos': requerimientos,
            'tiempo_estimado': tiempo_estimado,
            'fecha_solicitud': datetime.now(),
            'estado': 'Pendiente',
            'empresa_id': ObjectId(empresa_id)  # Relacionar con la empresa
        }
        solicitudes_collection.insert_one(nueva_solicitud)
        flash('Solicitud de proyecto enviada exitosamente.', 'success')
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
        return redirect(url_for('home'))
    
    return render_template('admin/ver_solicitudes_empresas.html', proyectos=solicitudes)

@app.route('/actualizar_solicitud/<solicitud_id>', methods=['POST'])
def actualizar_solicitud(solicitud_id):
    if 'correo' in session and session.get('role') == 'admin':
        nuevo_estado = request.form.get('estado')  # Obtener el nuevo estado desde el formulario
        
        try:
            # Buscar la solicitud por ID
            solicitud = solicitudes_collection.find_one({'_id': ObjectId(solicitud_id)})
            if not solicitud:
                flash('Solicitud no encontrada.', 'danger')
                return redirect(url_for('ver_todas_solicitudes'))
            
            # Obtener el ID de la empresa relacionada
            empresa_id = solicitud.get('empresa_id')  # Asumiendo que la solicitud tiene un campo 'empresa_id'
            
            # Buscar el correo de la empresa utilizando el ID
            empresa = usuarios_collection.find_one({'_id': ObjectId(empresa_id)})
            if not empresa:
                flash('Empresa no encontrada.', 'danger')
                return redirect(url_for('ver_todas_solicitudes'))
            
            # Actualizar la solicitud
            solicitudes_collection.update_one(
                {'_id': ObjectId(solicitud_id)}, 
                {'$set': {'estado': nuevo_estado}}
            )

            # Enviar correo de notificación
            msg = Message(
                subject=f'Actualización de Solicitud: {solicitud["nombre"]}',
                sender='maira.quiro.p02@gmail.com',
                recipients=[empresa['correo']]  # Usar el correo de la empresa
            )
            msg.body = f"""
            Estimado(a),

            La solicitud del proyecto "{solicitud['nombre']}" ha sido actualizada a estado: {nuevo_estado}.

            Detalles de la solicitud:
            - Descripción: {solicitud['descripcion']}
            - Requerimientos: {solicitud['requerimientos']}
            - Tiempo estimado: {solicitud['tiempo_estimado']} semanas

            Si tienes alguna pregunta o necesitas más información, no dudes en contactarnos.

            Saludos cordiales,
            Centro Digital de Desarrollo Tecnológico
            """
            mail.send(msg)

            flash(f'Solicitud actualizada a {nuevo_estado}.', 'success')
        except Exception as e:
            print(f"Error actualizando la solicitud: {e}")
            flash('Ocurrió un error al actualizar la solicitud.', 'danger')
    
    return redirect(url_for('ver_todas_solicitudes'))

if __name__ == '__main__':
    app.run(debug=True)
