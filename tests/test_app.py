import io
import pytest

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index_page(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Droplet Image Analyzer' in resp.data


def test_analyze_missing_file(client):
    # Missing file should return 400 and JSON body containing an error key
    data = {
        'paper_width': '10',
        'paper_height': '7'
    }
    resp = client.post('/analyze', data=data)
    assert resp.status_code == 400
    data_json = resp.get_json()
    assert isinstance(data_json, dict)
    assert 'error' in data_json


def test_analyze_invalid_dimensions(client):
    # Provide a file but invalid dimensions
    data = {
        'paper_width': 'not-a-number',
        'paper_height': '7'
    }
    # create a tiny 1x1 JPEG image in memory
    dummy_img = io.BytesIO()
    dummy_img.write(b'\xff\xd8\xff')  # invalid but present
    dummy_img.seek(0)
    resp = client.post('/analyze', data={'file': (dummy_img, 'test.jpg'), **data}, content_type='multipart/form-data')
    assert resp.status_code == 400
    # ensure we return JSON error
    assert 'error' in resp.get_json() or resp.get_data()
