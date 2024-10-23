import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env en local
if os.path.exists('.env'):
    load_dotenv()

# Obtener la URI de MongoDB desde las variables de entorno
MONGO_URI = os.getenv('MONGO_URI')

# Archivo de certificados SSL
certificado = certifi.where()

def Conexion():
    try:
        if not MONGO_URI:
            raise ValueError("La variable de entorno MONGO_URI no está definida.")

        client = MongoClient(MONGO_URI, tlsCAFile=certificado)
        print('Conexión Exitosa')
        return client["bd_AdminProyectos"]  # Nombre de la base de datos
    except Exception as e:
        print(f'Error de conexión con la base de datos: {e}')
        return None

# Inicializar la conexión
db = Conexion()
