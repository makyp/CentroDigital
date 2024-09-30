import datetime
import secrets
import random
from itsdangerous import URLSafeTimedSerializer
import string
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
app.config['MAIL_USERNAME'] = 'eusebioorlando1515@gmail.com' 
app.config['MAIL_PASSWORD'] = 'oxctlajixjkgjruc'    
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
        if usuario and check_password_hash(usuario['password'], password):
            session['correo'] = usuario['correo']
            session['role'] = usuario['role']
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
                 password = generar_contraseña()
                 s = URLSafeTimedSerializer(app.secret_key)
                 token=s.dumps(correo, salt='registro-usuario')
                 passwordHashed=generate_password_hash(password)
                 nuevo_usuario = UserWithoutRegister(nombre, correo, passwordHashed, role)
                 usuarios_collection.insert_one(nuevo_usuario.formato_doc())
                 msg=enviar_correo_registro(correo,password,token)
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
        email = s.loads(token, salt='registro-usuario', max_age=3600)  
        usuario = usuarios_collection.find_one({'correo': email})

        if not usuario:
            flash('Usuario no encontrado.')
            return redirect(url_for('home'))
        
        nombre_completo = usuario.get('nombre')  
        correo = usuario.get('correo')
        password = usuario.get('password')
         
        if request.method == 'POST':
            
            telefono = request.form.get('telefono')
            profesion = request.form.get('profesion')
            estudios = request.form.get('estudios')
            habilidades = request.form.get('habilidades')
            experiencia = request.form.get('experiencia')
            programa = request.form.get('programa')
            temp_Password= request.form['temp_password']
            new_password = request.form['new_password']
            
            # Validar que las contraseñas coincidan (opcional)
            if not check_password_hash(password, temp_Password):
                print('La contraseña temporal no es válida.')
                return redirect(url_for('completar_registro', token=token))
            
            # Actualizar los datos del usuario en la base de datos
            usuarios_collection.update_one(
                {'correo': correo},
                {
                    '$set': {
                        'telefono': telefono,
                        'profesion': profesion,
                        'estudios': estudios,
                        'habilidades': habilidades,
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
        usuarios = list(usuarios_collection.find())
        return render_template('admin/admin_usuarios.html', usuarios=usuarios)
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
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            fechainicio = request.form['fechainicio']
            fechafinal = request.form['fechafinal']
            estado = request.form['estado']
            nuevo_proyecto = Proyecto(nombre, descripcion, fechainicio, fechafinal, estado)
            proyectos_collection.insert_one(nuevo_proyecto.formato_doc())
            flash('Proyecto creado exitosamente.')
            return redirect(url_for('admin_proyectos'))

        # Convertir el cursor de proyectos en una lista para poder iterar sobre ella múltiples veces
        lista_proyectos = list(proyectos)
        
        # Reemplazar el ID del miembro asignado por su nombre completo
        for proyecto in lista_proyectos:
            for tarea in proyecto.get('tareas', []):
                miembro_id = tarea.get('miembroasignado')
                if miembro_id:
                    miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1, 'apellido': 1})
                    if miembro:
                        tarea['miembroasignado'] = f"{miembro['nombre']} {miembro['apellido']}"
                    else:
                        tarea['miembroasignado'] = "Sin asignar"
                else:
                    tarea['miembroasignado'] = "Sin asignar"

        return render_template('admin/admin_proyectos.html', proyectos=lista_proyectos)
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/editar', methods=['GET', 'POST'])
def editar_proyecto(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if request.method == 'POST':
            nombre = request.form['nombre']
            descripcion = request.form['descripcion']
            fechainicio = request.form['fechainicio']
            fechafinal = request.form['fechafinal']
            estado = request.form['estado']
            proyectos_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechainicio': fechainicio,
                    'fechafinal': fechafinal,
                    'estado': estado
                }}
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
            
            usuarios = usuarios_collection.find()
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
            return redirect(url_for('agregar_tarea', id=proyecto_id))
        proyectos = proyectos_collection.find()
        return render_template('admin/seleccionar_proyecto.html', proyectos=proyectos)
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/proyecto/<id>/agregar_tarea', methods=['GET', 'POST'])
def agregar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        proyecto = proyectos_collection.find_one({'_id': ObjectId(id)})
        if proyecto:
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']
                miembroasignado = request.form['miembroasignado']
                estado = request.form['estado']
                
                nueva_tarea = {
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'fechavencimiento': fechavencimiento,
                    'miembroasignado': miembroasignado,
                    'estado': estado,
                    'comentarios': [],
                    'tiempo_dedicado': 0
                }
                
                tarea_id = tareas_collection.insert_one(nueva_tarea).inserted_id
                nueva_tarea['_id'] = tarea_id
                proyectos_collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$push': {'tareas': nueva_tarea}}
                )
                flash('Tarea agregada exitosamente.')
                return redirect(url_for('ver_todas_las_tareas'))
            
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
            return render_template('admin/agregar_tarea.html', proyecto=proyecto, usuarios=miembros_asignados)
        
        flash('No se encontró el proyecto.')
        return redirect(url_for('admin_proyectos'))
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

from flask import request, session, flash, redirect, url_for, render_template
from bson.objectid import ObjectId

@app.route('/tareas', methods=['GET'])
def ver_todas_las_tareas():
    if 'correo' in session and session.get('role') == 'admin':
        # Obtener los filtros de la URL
        filtro_proyecto = request.args.get('proyecto')
        filtro_miembro = request.args.get('miembro')
        
        proyectos = proyectos_collection.find()
        tareas = []
        for proyecto in proyectos:
            # Si hay filtro por nombre de proyecto, aplicar el filtro
            if filtro_proyecto and filtro_proyecto.lower() not in proyecto['nombre'].lower():
                continue  # Saltar este proyecto si no coincide con el filtro

            for tarea in proyecto.get('tareas', []):
                miembro_id = tarea.get('miembroasignado')
                miembro_nombre = "Sin asignar"
                
                if miembro_id:
                    if isinstance(miembro_id, dict):  # Verificar si es un diccionario
                        miembro_id = miembro_id.get('_id')  # Obtener el ID del diccionario
                    if isinstance(miembro_id, (str, bytes)):  # Verificar si es una cadena o bytes
                        miembro = usuarios_collection.find_one({'_id': ObjectId(miembro_id)}, {'nombre': 1, 'apellido': 1})
                        if miembro:
                            miembro_nombre = f"{miembro['nombre']} {miembro['apellido']}"
                
                tarea['miembro_nombre'] = miembro_nombre
                tarea['proyecto_nombre'] = proyecto['nombre']
                tarea['proyecto_id'] = proyecto['_id']

                # Si hay filtro por miembro, aplicar el filtro
                if filtro_miembro and filtro_miembro.lower() not in miembro_nombre.lower():
                    continue  # Saltar esta tarea si no coincide con el filtro

                tareas.append(tarea)

        return render_template('admin/ver_tareas.html', tareas=tareas)

    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))


# Ruta para ver todas las tareas
@app.route('/tareas_general')
def ver_tareas_general():
    tareas = tareas_collection.find()
    return render_template('ver_todas_las_tareas.html', tareas=tareas)

@app.route('/tarea/<id>/comentar', methods=['POST'])
def comentar_tarea(id):
    if request.method == 'POST':
        contenido = request.form['contenido']
        autor = session['correo']
        comentario = {'autor': autor, 'contenido': contenido}
        tareas_collection.update_one({'_id': ObjectId(id)}, {'$push': {'comentarios': comentario}})
        flash('Comentario agregado exitosamente.')
    return redirect(url_for('ver_tareas_general'))

@app.route('/tarea/<id>/editar', methods=['GET', 'POST'])
def editar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        tarea = tareas_collection.find_one({'_id': ObjectId(id)})
        if tarea:
            proyecto = proyectos_collection.find_one({'tareas._id': ObjectId(id)})
            if request.method == 'POST':
                nombre = request.form['nombre']
                descripcion = request.form['descripcion']
                fechavencimiento = request.form['fechavencimiento']
                miembroasignado = request.form['miembroasignado']
                estado = request.form['estado']

                tareas_collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$set': {
                        'nombre': nombre,
                        'descripcion': descripcion,
                        'fechavencimiento': fechavencimiento,
                        'miembroasignado': miembroasignado,
                        'estado': estado
                    }}
                )

                proyectos_collection.update_one(
                    {'_id': proyecto['_id'], 'tareas._id': ObjectId(id)},
                    {'$set': {
                        'tareas.$.nombre': nombre,
                        'tareas.$.descripcion': descripcion,
                        'tareas.$.fechavencimiento': fechavencimiento,
                        'tareas.$.miembroasignado': miembroasignado,
                        'tareas.$.estado': estado
                    }}
                )

                flash('Tarea actualizada exitosamente.')
                return redirect(url_for('ver_todas_las_tareas'))
            
            miembros_asignados_ids = [ObjectId(miembro['_id']) for miembro in proyecto['miembros']]
            miembros_asignados = list(usuarios_collection.find({'_id': {'$in': miembros_asignados_ids}}))
            return render_template('admin/editar_tarea.html', tarea=tarea, proyecto=proyecto, miembros=miembros_asignados)
        
        flash('No se encontró la tarea.')
        return redirect(url_for('ver_todas_las_tareas'))
    
    flash('No tienes permisos para realizar esta acción.')
    return redirect(url_for('home'))

@app.route('/tarea/<id>/eliminar', methods=['POST'])
def eliminar_tarea(id):
    if 'correo' in session and session.get('role') == 'admin':
        tarea = tareas_collection.find_one({'_id': ObjectId(id)})
        if tarea:
            tareas_collection.delete_one({'_id': ObjectId(id)})
            proyectos_collection.update_one(
                {'tareas._id': ObjectId(id)},
                {'$pull': {'tareas': {'_id': ObjectId(id)}}}
            )
            flash('Tarea eliminada exitosamente.')
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
    if 'correo' in session:
        usuario = usuarios_collection.find_one({'correo': session['correo']})
        if usuario:
            proyectos = list(proyectos_collection.find({'miembros._id': usuario['_id']}))
            
            tareas_asignadas = []
            for proyecto in proyectos:
                for tarea in proyecto['tareas']:
                    if tarea['miembroasignado'] == str(usuario['_id']):
                        tarea_info = {
                            '_id': tarea['_id'],  # Incluimos el ID de la tarea
                            'nombre': tarea['nombre'],
                            'descripcion': tarea['descripcion'],
                            'estado': tarea['estado'],
                            'proyecto': proyecto['nombre']
                        }
                        tareas_asignadas.append(tarea_info)
            
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

if __name__ == '__main__':
    app.run(debug=True)
