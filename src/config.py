from pymongo import MongoClient
import certifi
# MONGO='mongodb+srv://makyp:Pacho040321@cluster0.yjkbst6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
MONGO='mongodb+srv://Aleky:MpBn7j6kTRdLXgDR@centrodigitaldedesarrol.uksf6.mongodb.net/?retryWrites=true&w=majority&appName=CentroDigitaldeDesarrollo'

certificado = certifi.where()

def Conexion():
    try:
        client = MongoClient(MONGO, tlsCAFile=certificado)
        print('Conexión Exitosa')
        return client["bd_AdminProyectos"]
    except ConnectionError:
        print('Error de conexión con la base de datos')
        return None

Conexion();#Inicializarla