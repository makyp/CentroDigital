import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from src.app import app

@pytest.fixture
def mock_db(monkeypatch):
    
    class MockUsuariosCollection:
        def __init__(self):
            self.usuarios = [
                {
                    '_id': ObjectId('123456789012345678901234'),
                    'nombre': 'Juan Pérez',
                    'correo': 'juan@test.com',
                    'role': 'miembro'
                }
            ]
        
        def find_one(self, query):
            return next((user for user in self.usuarios if str(user['_id']) == str(query.get('_id'))), None)

        def update_one(self, query, update):
            id_str = str(query.get('_id'))
            for user in self.usuarios:
                if str(user['_id']) == id_str:
                    user.update(update['$set'])
                    return True
            return False

        def delete_one(self, query):
            id_str = str(query.get('_id'))
            for i, user in enumerate(self.usuarios):
                if str(user['_id']) == id_str:
                    del self.usuarios[i]
                    return True
            return False

    class MockProyectosCollection:
        def __init__(self):
            self.proyectos = [
                {
                    '_id': ObjectId('567890123456789012345678'),
                    'nombre': 'Proyecto Ejemplo',
                    'miembros': [{'_id': ObjectId('123456789012345678901234')}],
                    'tareas': [{'miembroasignado': ObjectId('123456789012345678901234')}]
                }
            ]
        
        def find(self, query):
            results = []
            for proyecto in self.proyectos:
                if all(proyecto.get(k) == v for k, v in query.items()):
                    results.append(proyecto)
            return results
        
        def update_one(self, query, update):
            id_str = str(query.get('_id'))
            for proyecto in self.proyectos:
                if str(proyecto['_id']) == id_str:
                    proyecto.update(update['$set'])
                    return True
            return False
        
        def update_many(self, query, update):
            for proyecto in self.proyectos:
                for miembro in proyecto.get('miembros', []):
                    if miembro['_id'] == query.get('miembros._id'):
                        miembro.update(update.get('$pull', {}))
                for lider in proyecto.get('lideres', []):
                    if lider['_id'] == query.get('lideres._id'):
                        lider.update(update.get('$pull', {}))
                for tarea in proyecto.get('tareas', []):
                    if tarea['miembroasignado'] == query.get('tareas.miembroasignado'):
                        tarea['miembroasignado'] = None  # Desasignar tarea

    # Crear mocks separados para usuarios y proyectos
    mock_usuarios_collection = MockUsuariosCollection()
    mock_proyectos_collection = MockProyectosCollection()

    # Asignar los mocks a las colecciones correspondientes en la aplicación
    monkeypatch.setattr('src.app.usuarios_collection', mock_usuarios_collection)
    monkeypatch.setattr('src.app.proyectos_collection', mock_proyectos_collection)

    return mock_usuarios_collection, mock_proyectos_collection

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def admin_session(client):
    with client.session_transaction() as sess:
        sess['correo'] = 'admin@test.com'
        sess['role'] = 'admin'
        sess['nombre'] = 'Admin'


@pytest.fixture
def user_session(client):
    with client.session_transaction() as sess:
        sess['correo'] = 'user@test.com'
        sess['role'] = 'miembro'

@pytest.fixture
def mock_mail(monkeypatch):
    mail = MagicMock()
    monkeypatch.setattr('src.app.mail', mail)
    return mail


# Prueba para `editar_usuario` sin permisos de admin
def test_editar_usuario_sin_permiso(client, mock_db, user_session):
    user_id = '123456789012345678901234'
    response = client.post(f'/usuario/{user_id}/editar', json={'role': 'admin'})

    # Verificar que retorna un 403 por falta de permisos
    assert response.status_code == 403
    assert response.data == b'No tienes permisos'


# Prueba para `editar_usuario` con datos faltantes
def test_editar_usuario_falta_datos(client, mock_db, admin_session):
    user_id = '123456789012345678901234'
    response = client.post(f'/usuario/{user_id}/editar', json={})

    # Verificar que retorna un 400 por datos faltantes
    assert response.status_code == 400
    assert response.data == b'Faltan datos'

