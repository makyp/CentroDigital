import pytest
from unittest.mock import Mock, patch
from werkzeug.security import generate_password_hash
from bson import ObjectId
from flask import session

# Asumiendo que tu aplicación se llama 'app'
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    test_user = {
        '_id': ObjectId('123456789012345678901234'),
        'correo': 'test@test.com',
        'password': generate_password_hash('password123'),
        'role': 'miembro',  # Cambiado de 'usuario' a 'miembro'
        'nombre': 'Test User',
        'lider': 'No',
        'registroCompletado': True
    }
    # Usuario empresa de prueba
    test_empresa = {
        '_id': ObjectId('123456789012345678901235'),
        'correo': 'empresa@test.com',
        'password': generate_password_hash('password123'),
        'role': 'empresa',
        'nombre': 'Test Empresa',
        'lider': 'No'
    }

    return {'test_user': test_user, 'test_empresa': test_empresa}

def test_login_get(client):
    """Prueba que la ruta GET /login devuelve la página de login"""
    response = client.get('/login')
    assert response.status_code == 200
    # Verifica algo que realmente esté en la página
    assert b'Iniciar Sesi\xc3\xb3n - CDDT' in response.data

@patch('app.usuarios_collection')
@patch('app.proyectos_collection')
def test_login_post_success(mock_proyectos_collection, mock_usuarios_collection, client, mock_db):
    """Prueba un login exitoso de usuario normal"""
    mock_usuarios_collection.find_one.return_value = mock_db['test_user']

    mock_proyectos_collection.find.return_value = []  # Sin proyectos
    
    response = client.post('/login', data={
        'correo': 'test@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess['correo'] == 'test@test.com'
        assert sess['role'] == 'miembro'
        assert sess['nombre'] == 'Test User'
        assert sess['lider'] == 'No'
        assert sess['_id'] == str(mock_db['test_user']['_id'])

@patch('app.usuarios_collection')
def test_login_post_empresa(mock_collection, client, mock_db):
    """Prueba un login exitoso de usuario empresa"""
    # Configurar el mock de la base de datos
    mock_collection.find_one.return_value = mock_db['test_empresa']
    
    response = client.post('/login', data={
        'correo': 'empresa@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    # Verificar que se redirige al perfil
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess['correo'] == 'empresa@test.com'
        assert sess['role'] == 'empresa'
        assert sess['empresa_id'] == str(mock_db['test_empresa']['_id'])

@patch('app.usuarios_collection')
def test_login_invalid_password(mock_collection, client, mock_db):
    """Prueba login con contraseña incorrecta"""
    # Configurar el mock de la base de datos
    mock_collection.find_one.return_value = mock_db['test_user']
    
    response = client.post('/login', data={
        'correo': 'test@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    
    assert b'Correo o contrase\xc3\xb1a incorrectos.' in response.data

@patch('app.usuarios_collection')
def test_login_user_not_found(mock_collection, client):
    """Prueba login con usuario que no existe"""
    # Configurar el mock para retornar None (usuario no encontrado)
    mock_collection.find_one.return_value = None
    
    response = client.post('/login', data={
        'correo': 'noexiste@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert b'Correo o contrase\xc3\xb1a incorrectos.' in response.data

@patch('app.usuarios_collection')
def test_login_registro_incompleto(mock_collection, client, mock_db):
    """Prueba login con registro incompleto"""
    # Modificar usuario de prueba para tener registro incompleto
    test_user = mock_db['test_user'].copy()
    test_user['registroCompletado'] = False
    mock_collection.find_one.return_value = test_user
    
    response = client.post('/login', data={
        'correo': 'test@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert b'Debes completar tu registro antes de iniciar sesi\xc3\xb3n.' in response.data

def test_logout(client):
    """Prueba que la ruta /logout limpia la sesión y redirige al login"""
    # Configurar la sesión inicial
    with client.session_transaction() as sess:
        sess['correo'] = 'test@test.com'
        sess['role'] = 'miembro'
        sess['nombre'] = 'Test User'
        sess['lider'] = 'No'
        sess['_id'] = '123456789012345678901234'

    # Hacer una única llamada al logout
    response = client.get('/logout', follow_redirects=True)

    # Verificar el código de respuesta y el contenido
    assert response.status_code == 200
    assert b'Iniciar Sesi\xc3\xb3n - CDDT' in response.data

    # Verificar que la sesión esté completamente limpia
    with client.session_transaction() as sess:
        assert len(sess) == 0  # Verifica que la sesión esté completamente vacía

def test_logout_without_session(client):
    """Prueba que logout funciona incluso sin una sesión activa"""
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'Iniciar Sesi\xc3\xb3n - CDDT' in response.data

def test_logout_partial_session(client):
    """Prueba que logout limpia la sesión incluso si está incompleta"""
    with client.session_transaction() as sess:
        sess['correo'] = 'test@test.com'
    
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        assert 'correo' not in sess
        assert 'role' not in sess