from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from flask import url_for
import random
import string




def enviar_correo_registro(email, password, token):
    enlace = url_for('completar_registro', token=token, _external=True)
    msg = Message("Completa tu registro", recipients=[email])
    msg.body = f"Hola, tu contraseña temporal es {password}.\nPor favor, completa tu registro aquí: {enlace}"
    return msg

def generar_contraseña():
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for i in range(8))