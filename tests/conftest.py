import pytest
from app.app import app

@pytest.fixture
def app():
    app_config = {'TESTING': True}
    app.config.update(**app_config)
    ctx = app.app_context()
    ctx.push()

    yield app

    ctx.pop()
