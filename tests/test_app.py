import pytest
import json

def test_hello_endpoint(client):
    response = client.get('/hello')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert data['message'] == 'Hello, World!'
