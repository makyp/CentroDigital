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

# Prueba para `editar_usuario` exitoso con permisos de admin
def test_editar_usuario_exitoso(client, mock_db, admin_session):
    user_id = '123456789012345678901234'
    response = client.post(f'/usuario/{user_id}/editar', json={'role': 'admin'})

    # Verificar que el rol fue actualizado exitosamente
    assert response.status_code == 200
    assert response.json == {"mensaje": "Usuario actualizado exitosamente."}
    assert mock_db.usuarios[0]['role'] == 'admin'


# Prueba para `editar_usuario` cuando el usuario no existe
def test_editar_usuario_no_existe(client, mock_db, admin_session):
    user_id = 'nonexistentid123456789012'
    response = client.post(f'/usuario/{user_id}/editar', json={'role': 'admin'})

    # Verificar que retorna un 404 al no encontrar el usuario
    assert response.status_code == 404
    assert response.data == b'Usuario no encontrado'


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


# Prueba para `eliminar_usuario` exitoso con permisos de admin
def test_eliminar_usuario_exitoso(client, mock_db, admin_session):
    # Acceder a las colecciones de mock
    mock_usuarios_collection, mock_proyectos_collection = mock_db
    
    user_id = '123456789012345678901234'
    response = client.post(f'/usuario/{user_id}/eliminar')

    # Verificar que el usuario fue eliminado y los proyectos actualizados
    assert response.status_code == 302  # Redirección a admin_usuarios
    
    # Verificar que el usuario ha sido eliminado de la colección
    assert len(mock_usuarios_collection.usuarios) == 0  # Usuario eliminado
    
    # Verificar que el usuario fue eliminado de los miembros del proyecto
    assert not any(m['_id'] == ObjectId(user_id) for p in mock_proyectos_collection.proyectos for m in p['miembros'])
    
    # Verificar que todas las tareas del proyecto tienen el miembro asignado como None
    assert all(t['miembroasignado'] is None for p in mock_proyectos_collection.proyectos for t in p['tareas'])


# Prueba para `eliminar_usuario` cuando el usuario no existe
def test_eliminar_usuario_no_existe(client, mock_db, admin_session):
    # Acceder a las colecciones de mock
    mock_usuarios_collection, mock_proyectos_collection = mock_db
    
    user_id = '123456789012345678901235'
    response = client.post(f'/usuario/{user_id}/eliminar')

    # Verificar que retorna un mensaje de usuario no encontrado y redirección
    assert response.status_code == 302  # Redirección a admin_usuarios
    with client.session_transaction() as sess:
        assert 'No se encontró el usuario.' in sess['_flashes']


# Prueba para `eliminar_usuario` sin permisos de admin
def test_eliminar_usuario_sin_permiso(client, mock_db, user_session):
    user_id = '123456789012345678901234'
    response = client.post(f'/usuario/{user_id}/eliminar')

    # Verificar que retorna un 403 por falta de permisos y redirección a login
    assert response.status_code == 302  # Redirección a login
    with client.session_transaction() as sess:
        assert 'No tienes permisos para realizar esta acción.' in sess['_flashes']