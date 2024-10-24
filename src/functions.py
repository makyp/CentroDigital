from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from flask import url_for
from flask import flash
import random
import string

def enviar_correo_registro(nombre, email, password, token):
    enlace = url_for('completar_registro', token=token, _external=True)
    
    # Mensaje profesional y con formato estético
    msg = Message("Completa tu registro - Centro Digital de Desarrollo UdeC", recipients=[email])
    msg.body = (f"Estimado/a {nombre},\n\n"
                "Nos complace informarte que has sido agregado/a al equipo del Centro Digital de Desarrollo "
                "de la Universidad de Cundinamarca. Para completar tu registro y comenzar a colaborar, por favor sigue el enlace "
                "a continuación:\n\n"
                f"{enlace}\n\n"
                f"Tu contraseña provisional es: {password}\n\n"
                "⚠️ **Importante**: Este enlace tiene una validez de 3 días. Te recomendamos completar el proceso lo antes posible.\n\n"
                "Este correo electrónico es solo para fines de notificación y no acepta respuestas. Si tienes alguna duda, "
                "por favor contacta con el administrador del sistema.\n\n"
                "Atentamente,\n"
                "Equipo del Centro Digital de Desarrollo Tecnológico\n"
                "Universidad de Cundinamarca")
    
    msg.html = (f"<p>Estimado/a <strong>{nombre}</strong>,</p>"
                "<p>Nos complace informarte que has sido agregado/a al equipo del "
                "<strong>Centro Digital de Desarrollo</strong> de la Universidad de Cundinamarca.</p>"
                "<p>Para completar tu registro y comenzar a colaborar, por favor sigue el enlace "
                "a continuación:</p>"
                f"<p><a href='{enlace}' style='color: #027333;'>Completar Registro</a></p>"
                f"<p>Tu contraseña provisional es: <strong>{password}</strong></p>"
                "<p><strong>⚠️ Importante:</strong> Este enlace tiene una validez de 3 días. Te recomendamos completar el proceso "
                "lo antes posible.</p>"
                "<p>Este correo electrónico es solo para fines de notificación y no acepta respuestas. Si tienes alguna duda, "
                "por favor contacta con el administrador del sistema.</p>"
                "<p>Atentamente,<br>"
                "Equipo del Centro Digital de Desarrollo Tecnológico<br>"
                "Universidad de Cundinamarca</p>")
    
    return msg

def generar_contraseña():
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for i in range(8))

def notificar_administradores_y_propietario_confirmacionregistro(nombre_completo, correo_propietario, mail, usuarios_collection):
    # Obtener la lista de administradores desde la base de datos
    administradores = usuarios_collection.find({'role': 'admin'})
    correos_admin = [admin['correo'] for admin in administradores]

    # Definir el pie de página común a ambos correos
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Enviar correo a los administradores
    msg_admin = Message(
        "Nuevo registro completado",
        recipients=correos_admin,
        html=f"""
        <p>Estimado administrador,</p>
        <p>El usuario <strong>{nombre_completo}</strong> ha completado su registro en la plataforma.</p>
        <p>Te invitamos a revisar sus datos y asignarle nuevos proyectos si es necesario.</p>
        {footer}
        """
    )
    mail.send(msg_admin)

    # Enviar correo al propietario
    msg_propietario = Message(
        "Registro completado con éxito",
        recipients=[correo_propietario],
        html=f"""
        <p>Hola <strong>{nombre_completo}</strong>,</p>
        <p>Nos complace informarte que tu registro en el sistema ha sido completado exitosamente.</p>
        <p>Ya puedes acceder a la plataforma y comenzar a utilizar nuestros servicios.</p>
        {footer}
        """
    )
    mail.send(msg_propietario)

def notificar_cambio_rol(nombre_completo_usuario, correo_usuario, nombre_admin, rol_anterior, nuevo_role, mail, usuarios_collection):
    # Obtener la lista de administradores desde la base de datos
    administradores = usuarios_collection.find({'role': 'admin'})
    correos_admin = [admin['correo'] for admin in administradores]

    # Definir el pie de página común a ambos correos
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Enviar correo a los administradores
    msg_admin = Message(
        "Cambio de rol realizado",
        recipients=correos_admin,  # Enviar a todos los administradores
        html=f"""
        <p>Estimado administrador,</p>
        <p>El usuario <strong>{nombre_completo_usuario}</strong> ha cambiado de rol en la plataforma.</p>
        <p>El cambio fue realizado por el administrador <strong>{nombre_admin}</strong>.</p>
        <p><strong>Rol anterior:</strong> {rol_anterior}</p>
        <p><strong>Nuevo rol:</strong> {nuevo_role}</p>
        {footer}
        """
    )
    mail.send(msg_admin)

    # Enviar correo al usuario afectado
    msg_usuario = Message(
        "Tu rol ha sido actualizado",
        recipients=[correo_usuario],  # Enviar al correo del usuario
        html=f"""
        <p>Hola <strong>{nombre_completo_usuario}</strong>,</p>
        <p>Te informamos que tu rol en la plataforma ha sido actualizado por el administrador <strong>{nombre_admin}</strong>.</p>
        <p><strong>Rol anterior:</strong> {rol_anterior}</p>
        <p><strong>Nuevo rol:</strong> {nuevo_role}</p>
        <p>Si tienes alguna duda, por favor comunícate con tu administrador.</p>
        {footer}
        """
    )
    mail.send(msg_usuario)

def notificar_eliminacion_usuario(nombre_usuario, correo_usuario, nombre_admin, mail, usuarios_collection):
    administradores = usuarios_collection.find({'role': 'admin', 'correo': {'$ne': correo_usuario}})
    correos_admin = [admin['correo'] for admin in administradores]

    # Definir el pie de página común con formato
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    try:
        # Mensaje para los administradores
        msg_admin = Message(
            "Eliminación de usuario",
            recipients=correos_admin,
            html=f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <p>Estimados administradores,</p>
                <p>El administrador <strong>{nombre_admin}</strong> ha eliminado al usuario <strong>{nombre_usuario}</strong> ({correo_usuario}) del sistema.</p>
                {footer}
            </div>
            """
        )
        mail.send(msg_admin)
        
        # Mensaje para el usuario eliminado
        msg_usuario = Message(
            "Cuenta eliminada",
            recipients=[correo_usuario],
            html=f"""
            <div style="font-family: Arial, sans-serif; color: #333;">
                <p>Hola <strong>{nombre_usuario}</strong>,</p>
                <p>Tu cuenta ha sido eliminada del sistema. Para más información, por favor contacta al administrador.</p>
                {footer}
            </div>
            """
        )
        mail.send(msg_usuario)

    except Exception as e:
        flash(f'Error al enviar el correo: {str(e)}')

def notificar_cambio_proyecto(proyecto_anterior, proyecto_nuevo, nombre_admin, mail, usuarios_collection):
    # Obtener correos de los administradores
    admins = usuarios_collection.find({'role': 'admin'}, {'correo': 1})
    admin_emails = [admin['correo'] for admin in admins]

    # Obtener correos de los líderes del proyecto anterior
    lider_emails = []
    for lider in proyecto_anterior.get('lideres', []):
        if 'correo' in lider:
            lider_emails.append(lider['correo'])

    # Combinar correos de admins y líderes
    destinatarios = admin_emails + lider_emails

    # Información anterior y nueva para el cuerpo del correo
    objetivos_antiguos = [obj['descripcion'] for obj in proyecto_anterior.get('objetivosEspecificos', [])]
    objetivos_nuevos = [obj['descripcion'] for obj in proyecto_nuevo.get('objetivosEspecificos', [])]

    # Definir el pie de página común
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Preparar el correo
    msg = Message('Cambio en Proyecto', recipients=destinatarios)
    msg.html = f"""
    <p>{nombre_admin} ha realizado cambios en el proyecto '{proyecto_anterior['nombre']}'.</p>
    
    <p><strong>Información anterior:</strong></p>
    <p><strong>Nombre:</strong> {proyecto_anterior['nombre']}</p>
    <p><strong>Descripción:</strong> {proyecto_anterior['descripcion']}</p>
    <p><strong>Fecha Inicio:</strong> {proyecto_anterior['fechainicio']}</p>
    <p><strong>Fecha Final:</strong> {proyecto_anterior['fechafinal']}</p>
    <p><strong>Estado:</strong> {proyecto_anterior['estado']}</p>
    <p><strong>Objetivos específicos:</strong> {objetivos_antiguos}</p>

    <p><strong>Nueva información:</strong></p>
    <p><strong>Nombre:</strong> {proyecto_nuevo['nombre']}</p>
    <p><strong>Descripción:</strong> {proyecto_nuevo['descripcion']}</p>
    <p><strong>Fecha Inicio:</strong> {proyecto_nuevo['fechainicio']}</p>
    <p><strong>Fecha Final:</strong> {proyecto_nuevo['fechafinal']}</p>
    <p><strong>Estado:</strong> {proyecto_nuevo['estado']}</p>
    <p><strong>Objetivos específicos:</strong> {objetivos_nuevos}</p>

    {footer}
    """

    # Enviar el correo
    mail.send(msg)

def notificar_eliminacion_proyecto(proyecto, nombre_admin, usuarios_collection, mail):
    # Obtener la lista de administradores desde la base de datos
    administradores = usuarios_collection.find({'role': 'admin'})
    correos_admin = [admin['correo'] for admin in administradores]

    # Definir el pie de página común
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Preparar el cuerpo del correo
    msg = Message(
        subject='Proyecto Eliminado',
        recipients=correos_admin
    )
    msg.html = f"""
    <p>Estimados administradores,</p>
    <p>Se ha eliminado el siguiente proyecto:</p>
    <p><strong>Nombre:</strong> {proyecto['nombre']}</p>
    <p><strong>Descripción:</strong> {proyecto['descripcion']}</p>
    <p><strong>Fecha de Inicio:</strong> {proyecto['fechainicio']}</p>
    <p><strong>Fecha Final:</strong> {proyecto['fechafinal']}</p>
    <p><strong>Estado:</strong> {proyecto['estado']}</p>
    <p><strong>Objetivo General:</strong> {proyecto['objetivoGeneral']}</p>
    <p><strong>Eliminado por:</strong> {nombre_admin}</p>
    {footer}
    """
    
    mail.send(msg)

from flask_mail import Message

def notificar_asignacion_miembros(proyecto, miembros_agregados, correo_administradores, correo_lideres, mail):
    # Definir el pie de página común a ambos correos
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Enviar correo a los administradores
    msg_admin = Message(
        "Nuevos miembros asignados al proyecto",
        recipients=correo_administradores,
        html=f"""
        <p>Estimado administrador,</p>
        <p>Se han agregado los siguientes miembros al proyecto <strong>{proyecto['nombre']}</strong>:</p>
        <ul>
            {"".join(f"<li>{miembro['nombre']} ({miembro['correo']})</li>" for miembro in miembros_agregados)}
        </ul>
        <p>Por favor revisa la asignación.</p>
        {footer}
        """
    )
    mail.send(msg_admin)

    # Enviar correo a los líderes designados
    for lider in correo_lideres:
        msg_lider = Message(
            "Has sido asignado a un nuevo proyecto",
            recipients=[lider['correo']],
            html=f"""
            <p>Hola <strong>{lider['nombre']}</strong>,</p>
            <p>Te informamos que se han agregado nuevos miembros al proyecto <strong>{proyecto['nombre']}</strong>:</p>
            <ul>
                {"".join(f"<li>{miembro['nombre']} ({miembro['correo']})</li>" for miembro in miembros_agregados)}
            </ul>
            <p>Por favor revisa los cambios en la plataforma.</p>
            {footer}
            """
        )
        mail.send(msg_lider)


def notificar_cambios_miembros(proyecto, miembros_agregados, miembros_eliminados, mail):
    # Definir el pie de página común a ambos correos
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Enviar correos a los miembros eliminados
    for miembro in miembros_eliminados:
        msg_eliminar = Message(
            "Has sido eliminado del proyecto",
            recipients=[miembro['correo']],
            html=f"""
            <p>Hola <strong>{miembro['nombre']}</strong>,</p>
            <p>Te informamos que has sido eliminado del proyecto <strong>{proyecto['nombre']}</strong>.</p>
            <p>Si tienes preguntas, por favor contacta al administrador del proyecto.</p>
            {footer}
            """
        )
        mail.send(msg_eliminar)

    # Enviar correos a los miembros agregados
    for miembro in miembros_agregados:
        msg_agregar = Message(
            "Has sido agregado a un nuevo proyecto",
            recipients=[miembro['correo']],
            html=f"""
            <p>Hola <strong>{miembro['nombre']}</strong>,</p>
            <p>Nos complace informarte que has sido agregado al proyecto <strong>{proyecto['nombre']}</strong>.</p>
            <p>Ya puedes revisar los detalles en la plataforma.</p>
            {footer}
            """
        )
        mail.send(msg_agregar)

def notificar_eliminacion_miembros_admin(proyecto, miembros_eliminados, correos_admin, mail):
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """
    
    for admin_email in correos_admin:
        msg = Message(
            "Miembros eliminados del proyecto",
            recipients=[admin_email],
            html=f"""
            <p>Estimado administrador,</p>
            <p>Se han eliminado los siguientes miembros del proyecto <strong>{proyecto['nombre']}</strong>:</p>
            <ul>
                {"".join(f"<li>{miembro['nombre']} ({miembro['correo']})</li>" for miembro in miembros_eliminados)}
            </ul>
            <p>Por favor revisa los cambios en la plataforma.</p>
            {footer}
            """
        )
        mail.send(msg)


def notificar_eliminacion_miembros_lider(proyecto, miembros_eliminados, lideres, mail):
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """
    
    for lider in lideres:
        msg = Message(
            "Miembros eliminados del proyecto",
            recipients=[lider['correo']],
            html=f"""
            <p>Hola <strong>{lider['nombre']}</strong>,</p>
            <p>Te informamos que se han eliminado los siguientes miembros del proyecto <strong>{proyecto['nombre']}</strong>:</p>
            <ul>
                {"".join(f"<li>{miembro['nombre']} ({miembro['correo']})</li>" for miembro in miembros_eliminados)}
            </ul>
            <p>Por favor revisa los cambios en la plataforma.</p>
            {footer}
            """
        )
        mail.send(msg)

def notificar_nueva_tarea(proyecto, tarea, miembro, correos_admin, lider, mail):
    footer = """
    <p><strong>Nota:</strong> Este correo es generado automáticamente para notificaciones, por favor no responda a este mensaje.</p>
    <p>Atentamente,<br>Centro Digital de Desarrollo - Universidad de Cundinamarca</p>
    """

    # Correo al miembro asignado
    msg_miembro = Message(
        "Nueva tarea asignada a ti",
        recipients=[miembro['correo']],
        html=f"""
        <p>Hola <strong>{miembro['nombre']}</strong>,</p>
        <p>Se te ha asignado una nueva tarea en el proyecto <strong>{proyecto['nombre']}</strong>:</p>
        <p><strong>Nombre:</strong> {tarea['nombre']}<br>
        <strong>Descripción:</strong> {tarea['descripcion']}<br>
        <strong>Fecha de vencimiento:</strong> {tarea['fechavencimiento']}</p>
        <p>Por favor revisa la plataforma para más detalles.</p>
        {footer}
        """
    )
    mail.send(msg_miembro)

    # Correo a los administradores
    for admin_email in correos_admin:
        msg_admin = Message(
            "Nueva tarea creada en el proyecto",
            recipients=[admin_email],
            html=f"""
            <p>Estimado administrador,</p>
            <p>Se ha creado una nueva tarea en el proyecto <strong>{proyecto['nombre']}</strong>:</p>
            <p><strong>Nombre:</strong> {tarea['nombre']}<br>
            <strong>Descripción:</strong> {tarea['descripcion']}<br>
            <strong>Fecha de vencimiento:</strong> {tarea['fechavencimiento']}</p>
            <p>Por favor revisa la plataforma para más detalles.</p>
            {footer}
            """
        )
        mail.send(msg_admin)

    # Correo al líder
    msg_lider = Message(
        "Nueva tarea creada en tu proyecto",
        recipients=[lider['correo']],
        html=f"""
        <p>Hola <strong>{lider['nombre']}</strong>,</p>
        <p>Se ha creado una nueva tarea en el proyecto <strong>{proyecto['nombre']}</strong>:</p>
        <p><strong>Nombre:</strong> {tarea['nombre']}<br>
        <strong>Descripción:</strong> {tarea['descripcion']}<br>
        <strong>Fecha de vencimiento:</strong> {tarea['fechavencimiento']}</p>
        <p>Por favor revisa la plataforma para más detalles.</p>
        {footer}
        """
    )
    mail.send(msg_lider)
