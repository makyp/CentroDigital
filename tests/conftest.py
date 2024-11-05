
import pytest
from src.app import app as flask_app

@pytest.fixture
def app():
    # Configuración de prueba para la app
    flask_app.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/tu_database_test"
    })
    yield flask_app
