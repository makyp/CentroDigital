import pytest
from bson import ObjectId
from flask import session

def test_admin_usuarios_sin_autenticacion(client):
    """Prueba acceso a admin_usuarios sin autenticación"""
    response = client.get('/admin_usuarios', follow_redirects=True)
    assert response.status_code == 200
    # Usando encode/decode para manejar caracteres especiales
    assert 'No tienes permisos para acceder a esta página.'.encode('utf-8') in response.data
    assert 'Iniciar Sesión'.encode('utf-8') in response.data

def test_admin_usuarios_con_autenticacion_no_admin(client):
    """Prueba acceso a admin_usuarios con usuario no admin"""
    with client.session_transaction() as sess:
        sess['correo'] = 'usuario@test.com'
        sess['role'] = 'miembro'
    
    response = client.get('/admin_usuarios', follow_redirects=True)
    assert response.status_code == 200
    assert 'No tienes permisos para acceder a esta página.'.encode('utf-8') in response.data

def test_admin_usuarios_con_admin(client):
    """Prueba acceso exitoso a admin_usuarios con rol admin"""
    with client.session_transaction() as sess:
        sess['correo'] = 'admin@test.com'
        sess['role'] = 'admin'
    
    response = client.get('/admin_usuarios')
    assert response.status_code == 200
    # Verificar contenido específico que está presente en la plantilla
    assert b'Administrar Usuarios' in response.data

def test_admin_empresas_sin_autenticacion(client):
    """Prueba acceso a admin_empresas sin autenticación"""
    response = client.get('/admin_empresas', follow_redirects=True)
    assert response.status_code == 200
    assert 'No tienes permisos para acceder a esta página.'.encode('utf-8') in response.data
    assert 'Iniciar Sesión'.encode('utf-8') in response.data

def test_admin_empresas_con_autenticacion_no_admin(client):
    """Prueba acceso a admin_empresas con usuario no admin"""
    with client.session_transaction() as sess:
        sess['correo'] = 'usuario@test.com'
        sess['role'] = 'miembro'
    
    response = client.get('/admin_empresas', follow_redirects=True)
    assert response.status_code == 200
    assert 'No tienes permisos para acceder a esta página.'.encode('utf-8') in response.data

def test_admin_empresas_con_admin(client):
    """Prueba acceso exitoso a admin_empresas con rol admin"""
    with client.session_transaction() as sess:
        sess['correo'] = 'admin@test.com'
        sess['role'] = 'admin'
    
    response = client.get('/admin_empresas')
    assert response.status_code == 200
    # Verificar contenido específico que está presente en la plantilla
    assert b'Administrar Empresas' in response.data

def test_eliminar_empresa_sin_autenticacion(client):
    """Prueba eliminar empresa sin autenticación"""
    response = client.post('/eliminar_empresa/123456789012345678901234')
    assert response.status_code == 403
    data = response.get_json()
    assert data['success'] is False
    assert 'No tienes permisos' in data['message']

def test_eliminar_empresa_no_admin(client):
    """Prueba eliminar empresa con usuario no admin"""
    with client.session_transaction() as sess:
        sess['correo'] = 'usuario@test.com'
        sess['role'] = 'miembro'
    
    response = client.post('/eliminar_empresa/123456789012345678901234')
    assert response.status_code == 403
    data = response.get_json()
    assert data['success'] is False
    assert 'No tienes permisos' in data['message']

# Fixture para simular la base de datos
@pytest.fixture
def mock_db(monkeypatch):
    """Fixture para simular la base de datos"""
    class MockCollection:
        def __init__(self):
            # Crear un ID fijo para la empresa de prueba
            self.empresa_id = ObjectId('123456789012345678901234')
            self.data = {}
            # Inicializar con una empresa de prueba
            self.data[str(self.empresa_id)] = {
                '_id': self.empresa_id,
                'correo': 'empresa@test.com',
                'role': 'empresa'
            }

        def find_one(self, query):
            # Manejar búsqueda por ID, aceptando tanto ObjectId como string
            id_str = str(query.get('_id', ''))
            result = self.data.get(id_str)
            print("find_one - query:", query, "result:", result)  # Depuración
            return result

        def delete_one(self, query):
            # Manejar eliminación por ID
            id_str = str(query.get('_id', ''))
            print("delete_one - query:", query)  # Depuración
            if id_str in self.data:
                del self.data[id_str]
                print("delete_one - Deleted:", id_str)  # Depuración
                class DeleteResult:
                    def __init__(self):
                        self.deleted_count = 1
                return DeleteResult()
            class DeleteResult:
                def __init__(self):
                    self.deleted_count = 0
            return DeleteResult()

        def find(self, query=None):
            # Manejar consultas de búsqueda
            if query is None:
                return list(self.data.values())
            if 'role' in query:
                if query['role'] == 'empresa':
                    return [doc for doc in self.data.values() if doc['role'] == 'empresa']
                elif query['role'].get('$ne') == 'empresa':
                    return [doc for doc in self.data.values() if doc['role'] != 'empresa']
            return []

    # Crear y configurar el mock
    mock_collection = MockCollection()
    monkeypatch.setattr('app.usuarios_collection', mock_collection)
    return mock_collection

# Prueba de eliminación
def test_eliminar_empresa_exitoso(client, mock_db):
    """Prueba eliminación exitosa de empresa"""
    # Configurar sesión como admin
    with client.session_transaction() as sess:
        sess['correo'] = 'admin@test.com'
        sess['role'] = 'admin'
    
    empresa_id = str(mock_db.empresa_id)
    assert mock_db.find_one({'_id': ObjectId(empresa_id)}) is not None
    
    # Realizar la solicitud de eliminación
    response = client.post(f'/eliminar_empresa/{empresa_id}')
    print("Response Status Code:", response.status_code)  # Depuración
    print("Response Data:", response.get_json())  # Depuración
    
    # Verificar estado de la respuesta y contenido
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None, "La respuesta no contiene datos JSON"
    assert data['success'] is True, "La eliminación no fue exitosa"
    assert 'Empresa eliminada exitosamente' in data['message'], "Mensaje de éxito no coincide"
    
    # Confirmar que la empresa ha sido eliminada
    assert mock_db.find_one({'_id': ObjectId(empresa_id)}) is None

def test_eliminar_empresa_no_existe(client, mock_db):
    """Prueba eliminar una empresa que no existe"""
    with client.session_transaction() as sess:
        sess['correo'] = 'admin@test.com'
        sess['role'] = 'admin'
    
    # Usar un ID que no existe
    id_no_existente = str(ObjectId('123456789012345678901235'))
    response = client.post(f'/eliminar_empresa/{id_no_existente}')
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert 'Empresa no encontrada' in data['message']